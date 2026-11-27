#!/usr/bin/env python3
"""Analyze and plot results from o1_codegen_permute_exp.py."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "analysis" / "data"
OUT_DIR = REPO_ROOT / "analysis" / "charts" / "thesis"

CONFIG_ORDER = ["O1", "O1_align", "O2", "O3_native"]
CONFIG_LABELS = {
    "O1": "-O1 (default)",
    "O1_align": "-O1 + -falign-*=16",
    "O2": "-O2",
    "O3_native": "-O3 -march=native",
}
CONFIG_COLORS = {
    "O1": "#d62728",        # red
    "O1_align": "#ff7f0e",  # orange
    "O2": "#1f77b4",        # blue
    "O3_native": "#2ca02c", # green
}
CONFIG_MARKERS = {
    "O1": "o",
    "O1_align": "s",
    "O2": "^",
    "O3_native": "D",
}


def load_sweep(path: Path) -> list[dict]:
    records = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def print_summary(records: list[dict], perf_data: list[dict] | None) -> None:
    benchmarks = list(dict.fromkeys(r["benchmark"] for r in records))

    print("\n## Experiment 1: MLton C-Codegen Permutation Sensitivity (Max/Min Cycle Spread %)")
    print("| Benchmark | Suite | -O1 | -O1 + align | -O2 | -O3 -march=native | -O1 Inst. Spread |")
    print("| :--- | :--- | ---: | ---: | ---: | ---: | ---: |")
    for b in benchmarks:
        brecs = [r for r in records if r["benchmark"] == b]
        suite = brecs[0]["suite"]
        row = [b, suite]
        o1_inst_spread = 0.0
        for cfg in CONFIG_ORDER:
            crecs = [r for r in brecs if r["config"] == cfg]
            cyc = [r["median_cycles"] for r in crecs]
            spread = (max(cyc) / min(cyc) - 1.0) * 100.0
            row.append(f"{spread:.2f}%")
            if cfg == "O1":
                insts = [r["median_instructions"] for r in crecs]
                o1_inst_spread = (max(insts) / min(insts) - 1.0) * 100.0
        row.append(f"{o1_inst_spread:.3f}%")
        print("| " + " | ".join(row) + " |")

    print("\n## Experiment 1: Wall-Time Max/Min Spread %")
    print("| Benchmark | -O1 | -O1 + align | -O2 | -O3 -march=native |")
    print("| :--- | ---: | ---: | ---: | ---: |")
    for b in benchmarks:
        brecs = [r for r in records if r["benchmark"] == b]
        row = [b]
        for cfg in CONFIG_ORDER:
            crecs = [r for r in brecs if r["config"] == cfg]
            vals = [r.get("internal_avg_s", r["median_wall_s"]) for r in crecs]
            spread = (max(vals) / min(vals) - 1.0) * 100.0
            row.append(f"{spread:.2f}%")
        print("| " + " | ".join(row) + " |")

    if perf_data:
        print("\n## Experiment 2: Ice Lake TMA Root-Cause Comparison (Fast vs. Slow -O1 Seed)")
        for entry in perf_data:
            b = entry["benchmark"]
            pf = entry["profiles"]["O1_fast"]
            ps = entry["profiles"]["O1_slow"]
            cf, cs = pf["counters"], ps["counters"]
            cyc_diff = (cs["cycles"] / cf["cycles"] - 1.0) * 100.0
            inst_diff = (cs["instructions"] / cf["instructions"] - 1.0) * 100.0
            print(f"\n### `{b}` (`-O1` fast seed={entry['o1_fast_seed']} vs. slow seed={entry['o1_slow_seed']}: +{cyc_diff:.2f}% cycles, {inst_diff:+.3f}% instructions)")
            print("| Variant | Seed | Cycles (B) | Insts (B) | IPC | FE Bound % | BE Bound % | DSB uops % | MITE uops % | DSB->MITE Pen (M) | ICache Stall (M) |")
            print("| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
            for label in ["O1_fast", "O1_slow", "O1_align_S0", "O2_S0", "O3_native_S0"]:
                if label not in entry["profiles"]:
                    continue
                p = entry["profiles"][label]
                c, d = p["counters"], p["derived"]
                print(
                    f"| `{label}` | {p['seed']} | {c['cycles']/1e9:.3f} | {c['instructions']/1e9:.3f} "
                    f"| {d['ipc']:.2f} | {d['fe_bound_pct']:.1f}% | {d['be_bound_pct']:.1f}% "
                    f"| {d['dsb_share_pct']:.1f}% | {d['mite_share_pct']:.1f}% "
                    f"| {c.get('dsb2mite_switches.penalty_cycles', 0.0)/1e6:.2f} "
                    f"| {c.get('icache_64b.iftag_stall', 0.0)/1e6:.2f} |"
                )


def plot_sweep_grid(records: list[dict], out_prefix: Path) -> None:
    benchmarks = list(dict.fromkeys(r["benchmark"] for r in records))
    ncols = 4
    nrows = (len(benchmarks) + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(13.5, 3.1 * nrows), sharex=True)
    axes_flat = np.array(axes).reshape(-1)

    for i, b in enumerate(benchmarks):
        ax = axes_flat[i]
        brecs = [r for r in records if r["benchmark"] == b]
        for cfg in CONFIG_ORDER:
            crecs = sorted([r for r in brecs if r["config"] == cfg], key=lambda r: r["seed"])
            xs = [r["seed"] for r in crecs]
            cyc = [r["median_cycles"] for r in crecs]
            med = statistics.median(cyc)
            ys = [(c / med - 1.0) * 100.0 for c in cyc]
            ax.plot(
                xs, ys,
                label=CONFIG_LABELS[cfg],
                color=CONFIG_COLORS[cfg],
                marker=CONFIG_MARKERS[cfg],
                markersize=3.5,
                linewidth=1.5 if cfg == "O1" else 1.1,
                alpha=0.95 if cfg == "O1" else 0.85,
                zorder=5 if cfg == "O1" else 3,
            )
        ax.axhline(0.0, color="#666666", linestyle="--", linewidth=0.7, alpha=0.6)
        ax.set_title(b, fontsize=10.5, fontweight="bold")
        ax.set_xticks([0, 3, 6, 9, 12, 15])
        ax.grid(True, linestyle=":", alpha=0.4)
        if i % ncols == 0:
            ax.set_ylabel("Cycles vs. median (%)")
        if i >= (nrows - 1) * ncols:
            ax.set_xlabel("Permutation seed (0 = default)")

    for j in range(len(benchmarks), len(axes_flat)):
        axes_flat[j].set_visible(False)

    handles, labels = axes_flat[0].get_legend_handles_labels()
    fig.legend(
        handles, labels,
        loc="upper center",
        ncol=len(CONFIG_ORDER),
        frameon=True,
        fontsize=9.5,
        bbox_to_anchor=(0.5, 1.01),
    )
    fig.suptitle(
        "MLton C-Codegen Entry-Order Permutation Sensitivity Across GCC Optimization Levels",
        fontsize=12,
        fontweight="bold",
        y=1.06,
    )
    fig.tight_layout()
    for ext in ("pdf", "png"):
        out_path = out_prefix.with_suffix(f".{ext}")
        fig.savefig(out_path, bbox_inches="tight", dpi=200)
        print(f"Wrote {out_path}")
    plt.close(fig)


def plot_spread_bar(records: list[dict], out_prefix: Path) -> None:
    benchmarks = list(dict.fromkeys(r["benchmark"] for r in records))
    x = np.arange(len(benchmarks))
    width = 0.2

    fig, ax = plt.subplots(figsize=(11.5, 4.2))
    for k, cfg in enumerate(CONFIG_ORDER):
        spreads = []
        for b in benchmarks:
            crecs = [r for r in records if r["benchmark"] == b and r["config"] == cfg]
            cyc = [r["median_cycles"] for r in crecs]
            spreads.append((max(cyc) / min(cyc) - 1.0) * 100.0)
        offset = (k - (len(CONFIG_ORDER) - 1) / 2.0) * width
        bars = ax.bar(
            x + offset, spreads, width,
            label=CONFIG_LABELS[cfg],
            color=CONFIG_COLORS[cfg],
            edgecolor="black",
            linewidth=0.4,
            alpha=0.9,
        )
        if cfg == "O1":
            for bar, val in zip(bars, spreads):
                if val >= 2.0:
                    ax.text(
                        bar.get_x() + bar.get_width() / 2.0,
                        val + 0.4,
                        f"{val:.1f}%",
                        ha="center",
                        va="bottom",
                        fontsize=7.5,
                        color=CONFIG_COLORS["O1"],
                        fontweight="bold",
                    )

    ax.set_xticks(x)
    ax.set_xticklabels(benchmarks, rotation=20, ha="right", fontsize=9.5)
    ax.set_ylabel("Max / Min Cycle Spread (%) across seeds 0..15")
    ax.set_title(
        "Max-to-Min Cycle Spread Under MLton C-Codegen Entry-Order Permutations (Flattening Disabled)",
        fontsize=11,
        fontweight="bold",
    )
    ax.grid(True, axis="y", linestyle=":", alpha=0.5)
    ax.legend(frameon=True, fontsize=9)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        out_path = out_prefix.with_suffix(f".{ext}")
        fig.savefig(out_path, bbox_inches="tight", dpi=200)
        print(f"Wrote {out_path}")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize and plot MLton c-codegen permutation results.")
    parser.add_argument("--sweep", type=Path, default=DATA_DIR / "o1_codegen_permute_sweep.jsonl")
    parser.add_argument("--perf", type=Path, default=DATA_DIR / "o1_codegen_permute_perf.json")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()

    records = load_sweep(args.sweep)
    perf_data = json.loads(args.perf.read_text()) if args.perf.exists() else None
    print_summary(records, perf_data)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    plot_sweep_grid(records, args.out_dir / "o1_codegen_permute_sweep")
    plot_spread_bar(records, args.out_dir / "o1_codegen_permute_spread_bar")


if __name__ == "__main__":
    main()
