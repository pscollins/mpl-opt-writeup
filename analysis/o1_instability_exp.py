#!/usr/bin/env python3
"""Controlled code-layout perturbation experiment to measure GCC -O1 instability.

Sweeps `-fpatchable-function-entry=N,0` across N in {0, 4, 8, ..., 60} (one full
64-byte cache line / two 32-byte Intel DSB lines) with all custom flattening passes
disabled (`-disable-pass '(preFlatten.*)|(shallowFlatten.*)'`), comparing:
  - O1          : -O1 (MLton default)
  - O1_align    : -O1 -falign-loops=16 -falign-jumps=16 -falign-labels=16 -falign-functions=16
  - O2          : -O2
  - O3_native   : -O3 -march=native

Experiment 1: Collects pinned-core wall time, cycles, instructions, and branch-misses
              across all (benchmark, config, offset) combinations.
Experiment 2: Runs Ice Lake Top-Down Microarchitecture Analysis (TMA) + DSB/MITE
              perf counters on the fastest vs. slowest -O1 offsets for the top
              benchmarks exhibiting the largest -O1 instability.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import sys
import time
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "analysis" / "data"
MLTON_BIN = Path.home() / "code" / "mlton" / "build" / "bin" / "mlton"
MLTON_TESTS_DIR = Path.home() / "code" / "mlton" / "benchmark" / "tests"
MPL_BENCH_DIR = Path.home() / "code" / "parallel-ml-bench" / "mpl"

OFFSETS = list(range(0, 64, 4))  # 0, 4, 8, ..., 60 (16 offsets)

CONFIGS: dict[str, list[str]] = {
    "O1": ["-cc-opt", "-O1"],
    "O1_align": [
        "-cc-opt", "-O1",
        "-cc-opt", "-falign-loops=16",
        "-cc-opt", "-falign-jumps=16",
        "-cc-opt", "-falign-labels=16",
        "-cc-opt", "-falign-functions=16",
    ],
    "O2": ["-cc-opt", "-O2"],
    "O3_native": ["-cc-opt", "-O3", "-cc-opt", "-march=native"],
}

# Benchmark specs calibrated to ~0.5-2.0s per invocation
BENCHMARKS: list[dict[str, Any]] = [
    # MLton benchmark suite (single-core)
    {"name": "wc-input1",       "suite": "mlton", "doit": 256, "trials": 3},
    {"name": "fft",             "suite": "mlton", "doit": 1,   "trials": 2},
    {"name": "matrix-multiply", "suite": "mlton", "doit": 3,   "trials": 3},
    {"name": "imp-for",         "suite": "mlton", "doit": 64,  "trials": 3},
    {"name": "checksum",        "suite": "mlton", "doit": 192, "trials": 3},
    # parallel-ml-bench (1-core MLton)
    {
        "name": "primes",
        "suite": "parallel_bench",
        "bench_dir": "primes",
        "args": ["-N", "40000000", "-repeat", "3", "-warmup", "1"],
        "trials": 1,
    },
    {
        "name": "dense-matmul",
        "suite": "parallel_bench",
        "bench_dir": "dense-matmul",
        "args": ["-N", "512", "-repeat", "3", "-warmup", "1"],
        "trials": 5,  # median of 5 invocations filters occasional physical-page/L2-set blips on 512x512 matrices
    },
    {
        "name": "msort",
        "suite": "parallel_bench",
        "bench_dir": "msort",
        "args": ["-N", "2500000", "-repeat", "3", "-warmup", "1"],
        "trials": 1,
    },
]

LIGHT_PERF_EVENTS = "cycles,instructions,branch-misses"
TMA_PERF_EVENTS = (
    "cycles,instructions,branch-misses,"
    "slots,topdown-fe-bound,topdown-be-bound,topdown-bad-spec,topdown-retiring,"
    "idq.dsb_uops,idq.mite_uops,dsb2mite_switches.penalty_cycles,icache_64b.iftag_stall"
)

AVG_RE = re.compile(r"average\s+([0-9.]+)\s*s", re.IGNORECASE)


def prepare_mlton_source(bench: dict[str, Any], src_dir: Path) -> Path:
    """Create a scaled batch .sml file from the benchmark's .sml source."""
    name = bench["name"]
    doit = bench["doit"]
    out_sml = src_dir / f"{name}.scaled.sml"
    if not out_sml.exists():
        orig = MLTON_TESTS_DIR / f"{name}.sml"
        content = orig.read_text()
        out_sml.write_text(f"{content}\nval _ = Main.doit {doit}\n")
    return out_sml


def compile_binary(
    bench: dict[str, Any],
    config_name: str,
    offset: int,
    bin_dir: Path,
    src_dir: Path,
) -> tuple[str, str, int, Path, str | None]:
    """Compile one (bench, config, offset) binary with flattening passes disabled."""
    bname = bench["name"]
    out_path = bin_dir / f"{bname}__{config_name}__N{offset:02d}"
    if out_path.exists():
        return (bname, config_name, offset, out_path, None)

    base_flags = [
        str(MLTON_BIN),
        "-codegen", "c",
        "-build-magic", "0",
        "-disable-pass", "(preFlatten.*)|(shallowFlatten.*)",
    ]

    if bench["suite"] == "mlton":
        src_path = prepare_mlton_source(bench, src_dir)
        cmd = (
            base_flags
            + CONFIGS[config_name]
            + ["-cc-opt", f"-fpatchable-function-entry={offset},0"]
            + ["-output", str(out_path), str(src_path)]
        )
        cwd = MLTON_TESTS_DIR
    else:
        bdir = bench["bench_dir"]
        mlb = MPL_BENCH_DIR / "bench" / bdir / f"{bdir}.mlb"
        cmd = (
            base_flags
            + [
                "-mlb-path-var", "COMPAT mlton",
                "-default-type", "int64",
                "-default-type", "word64",
                "-cc-opt", "-Wno-error=incompatible-pointer-types",
            ]
            + CONFIGS[config_name]
            + ["-cc-opt", f"-fpatchable-function-entry={offset},0"]
            + ["-output", str(out_path), str(mlb)]
        )
        cwd = MPL_BENCH_DIR

    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if res.returncode != 0:
        err = (res.stderr or res.stdout)[-400:]
        return (bname, config_name, offset, out_path, err)
    return (bname, config_name, offset, out_path, None)


def parse_perf_csv(stderr_text: str) -> dict[str, float]:
    """Parse `perf stat -x,` output into event -> numeric value."""
    metrics: dict[str, float] = {}
    for line in stderr_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("WARNING"):
            continue
        parts = line.split(",")
        if len(parts) < 3:
            continue
        val_str, _, event = parts[0].strip(), parts[1].strip(), parts[2].strip()
        if not val_str or val_str in ("<not supported>", "<not counted>"):
            continue
        # Strip any PMU suffix like cpu_core/cycles/ -> cycles
        clean_event = event
        if "/" in clean_event:
            m = re.search(r"/([^/]+)/", clean_event)
            if m:
                clean_event = m.group(1)
        try:
            metrics[clean_event] = float(val_str)
        except ValueError:
            pass
    return metrics


def run_once_with_perf(
    binary: Path,
    bench: dict[str, Any],
    events: str,
    cpu: int,
    repeat: int = 1,
) -> dict[str, Any]:
    """Run a binary pinned to `cpu` under `perf stat` and return timing + counters."""
    cwd = MLTON_TESTS_DIR if bench["suite"] == "mlton" else MPL_BENCH_DIR
    run_args = [str(binary)] + bench.get("args", [])
    perf_cmd = ["taskset", "-c", str(cpu), "perf", "stat", "-x,", "-e", events]
    if repeat > 1:
        perf_cmd += ["-r", str(repeat)]
    perf_cmd += ["--"] + run_args

    t0 = time.perf_counter()
    res = subprocess.run(perf_cmd, cwd=cwd, capture_output=True, text=True)
    wall_s = (time.perf_counter() - t0) / repeat
    if res.returncode != 0:
        raise RuntimeError(f"Run failed for {binary}: {res.stderr[-300:]}")

    counters = parse_perf_csv(res.stderr)
    out: dict[str, Any] = {
        "wall_s": wall_s,
        "counters": counters,
    }
    if bench["suite"] == "parallel_bench":
        m = AVG_RE.search(res.stdout)
        if m:
            out["internal_avg_s"] = float(m.group(1))
    return out


def get_chunk_addrs(binary: Path) -> dict[str, str]:
    """Return addresses of Chunk_* symbols for diagnostics."""
    res = subprocess.run(["nm", str(binary)], capture_output=True, text=True)
    addrs: dict[str, str] = {}
    if res.returncode == 0:
        for line in res.stdout.splitlines():
            parts = line.split()
            if len(parts) == 3 and parts[2].startswith("Chunk_"):
                addrs[parts[2]] = "0x" + parts[0]
    return addrs


def main() -> None:
    parser = argparse.ArgumentParser(description="Run GCC -O1 code-layout instability experiment.")
    parser.add_argument("--cpu", type=int, default=0, help="CPU core to pin runs to (default: 0)")
    parser.add_argument("--compile-jobs", type=int, default=32, help="Parallel compile workers (default: 32)")
    parser.add_argument("--bin-dir", type=Path, default=Path("/tmp/o1_instability_bins"))
    parser.add_argument("--keep-bins", action="store_true", help="Keep compiled binaries after completion")
    parser.add_argument("--sweep-out", type=Path, default=DATA_DIR / "o1_instability_sweep.jsonl")
    parser.add_argument("--perf-out", type=Path, default=DATA_DIR / "o1_instability_perf.json")
    parser.add_argument("--top-k-perf", type=int, default=3, help="Number of top -O1 unstable benchmarks for Exp 2 TMA perf")
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    bin_dir: Path = args.bin_dir
    src_dir = bin_dir / "_src"
    bin_dir.mkdir(parents=True, exist_ok=True)
    src_dir.mkdir(parents=True, exist_ok=True)

    # Pre-create scaled MLton sources once to avoid concurrent writes
    for bench in BENCHMARKS:
        if bench["suite"] == "mlton":
            prepare_mlton_source(bench, src_dir)

    # Phase 1: Parallel compilation
    jobs = [
        (bench, cfg, off)
        for bench in BENCHMARKS
        for cfg in CONFIGS
        for off in OFFSETS
    ]
    print(f"[Phase 1] Compiling {len(jobs)} binaries with {args.compile_jobs} workers...")
    t_comp = time.perf_counter()
    binaries: dict[tuple[str, str, int], Path] = {}
    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=args.compile_jobs) as ex:
        futs = [
            ex.submit(compile_binary, bench, cfg, off, bin_dir, src_dir)
            for bench, cfg, off in jobs
        ]
        done = 0
        for fut in as_completed(futs):
            bname, cfg, off, path, err = fut.result()
            done += 1
            if err:
                failures.append(f"{bname}/{cfg}/N={off}: {err}")
            else:
                binaries[(bname, cfg, off)] = path
            if done % 64 == 0 or done == len(jobs):
                print(f"  compiled {done}/{len(jobs)} ({time.perf_counter() - t_comp:.1f}s)")

    if failures:
        print("Compilation failures:", file=sys.stderr)
        for f in failures[:10]:
            print(" ", f, file=sys.stderr)
        sys.exit(1)

    # Phase 2: Experiment 1 — Sequential pinned-core sweep
    print(f"\n[Phase 2] Running Experiment 1 sweep on CPU {args.cpu} -> {args.sweep_out}")
    sweep_records: list[dict[str, Any]] = []
    t_run = time.perf_counter()
    total_runs = len(jobs)
    idx = 0
    with args.sweep_out.open("w") as out_f:
        for bench in BENCHMARKS:
            bname = bench["name"]
            trials = bench["trials"]
            for cfg in CONFIGS:
                for off in OFFSETS:
                    idx += 1
                    binary = binaries[(bname, cfg, off)]
                    trial_results = [
                        run_once_with_perf(binary, bench, LIGHT_PERF_EVENTS, args.cpu, repeat=1)
                        for _ in range(trials)
                    ]
                    cycles_list = [r["counters"]["cycles"] for r in trial_results]
                    insts_list = [r["counters"]["instructions"] for r in trial_results]
                    bmiss_list = [r["counters"].get("branch-misses", 0.0) for r in trial_results]
                    wall_list = [r["wall_s"] for r in trial_results]
                    internal_list = [r["internal_avg_s"] for r in trial_results if "internal_avg_s" in r]

                    rec: dict[str, Any] = {
                        "benchmark": bname,
                        "suite": bench["suite"],
                        "config": cfg,
                        "offset": off,
                        "trials": trials,
                        "median_wall_s": statistics.median(wall_list),
                        "median_cycles": statistics.median(cycles_list),
                        "median_instructions": statistics.median(insts_list),
                        "median_branch_misses": statistics.median(bmiss_list),
                        "wall_trials": wall_list,
                        "cycles_trials": cycles_list,
                    }
                    if internal_list:
                        rec["internal_avg_s"] = statistics.median(internal_list)

                    sweep_records.append(rec)
                    out_f.write(json.dumps(rec) + "\n")
                    out_f.flush()

                # Progress summary per (bench, cfg)
                cfg_recs = [r for r in sweep_records if r["benchmark"] == bname and r["config"] == cfg]
                cyc = [r["median_cycles"] for r in cfg_recs]
                spread_pct = (max(cyc) / min(cyc) - 1.0) * 100.0
                elapsed = time.perf_counter() - t_run
                print(
                    f"  [{idx:3d}/{total_runs}] {bname:16s} {cfg:10s} "
                    f"cycle spread={spread_pct:5.2f}%  (elapsed {elapsed:.0f}s)"
                )

    # Phase 3: Experiment 2 — Ice Lake TMA + DSB/MITE perf deep-dive
    print(f"\n[Phase 3] Running Experiment 2 Ice Lake TMA perf deep-dive -> {args.perf_out}")
    # Rank benchmarks by -O1 cycle spread
    o1_spreads: list[tuple[float, dict[str, Any], int, int]] = []
    for bench in BENCHMARKS:
        bname = bench["name"]
        o1_recs = [r for r in sweep_records if r["benchmark"] == bname and r["config"] == "O1"]
        fast_rec = min(o1_recs, key=lambda r: r["median_cycles"])
        slow_rec = max(o1_recs, key=lambda r: r["median_cycles"])
        spread = slow_rec["median_cycles"] / fast_rec["median_cycles"]
        o1_spreads.append((spread, bench, fast_rec["offset"], slow_rec["offset"]))

    o1_spreads.sort(key=lambda x: x[0], reverse=True)
    perf_results: list[dict[str, Any]] = []
    for spread, bench, n_fast, n_slow in o1_spreads[: args.top_k_perf]:
        bname = bench["name"]
        print(f"  TMA profiling {bname}: O1 fast N={n_fast} vs slow N={n_slow} (sweep spread={(spread-1)*100:.2f}%)")
        entry: dict[str, Any] = {
            "benchmark": bname,
            "suite": bench["suite"],
            "o1_fast_offset": n_fast,
            "o1_slow_offset": n_slow,
            "sweep_cycle_ratio": spread,
            "profiles": {},
        }
        cases = [
            ("O1_fast", "O1", n_fast),
            ("O1_slow", "O1", n_slow),
            ("O1_align_N0", "O1_align", 0),
            ("O2_N0", "O2", 0),
            ("O3_native_N0", "O3_native", 0),
        ]
        for label, cfg, off in cases:
            binary = binaries[(bname, cfg, off)]
            res = run_once_with_perf(binary, bench, TMA_PERF_EVENTS, args.cpu, repeat=3)
            c = res["counters"]
            slots = c.get("slots", 0.0) or 1.0
            dsb = c.get("idq.dsb_uops", 0.0)
            mite = c.get("idq.mite_uops", 0.0)
            tot_uops = (dsb + mite) or 1.0
            entry["profiles"][label] = {
                "config": cfg,
                "offset": off,
                "wall_s": res["wall_s"],
                "counters": c,
                "derived": {
                    "ipc": c.get("instructions", 0.0) / (c.get("cycles", 1.0) or 1.0),
                    "fe_bound_pct": 100.0 * c.get("topdown-fe-bound", 0.0) / slots,
                    "be_bound_pct": 100.0 * c.get("topdown-be-bound", 0.0) / slots,
                    "bad_spec_pct": 100.0 * c.get("topdown-bad-spec", 0.0) / slots,
                    "retiring_pct": 100.0 * c.get("topdown-retiring", 0.0) / slots,
                    "dsb_share_pct": 100.0 * dsb / tot_uops,
                    "mite_share_pct": 100.0 * mite / tot_uops,
                },
                "chunk_addrs": get_chunk_addrs(binary),
            }
        perf_results.append(entry)

    args.perf_out.write_text(json.dumps(perf_results, indent=2) + "\n")
    print(f"Saved Experiment 2 TMA results to {args.perf_out}")

    if not args.keep_bins:
        shutil.rmtree(bin_dir, ignore_errors=True)
        print(f"Cleaned up temporary binaries in {bin_dir}")

    print(f"\nDone in {(time.perf_counter() - t_comp):.1f}s total.")


if __name__ == "__main__":
    main()
