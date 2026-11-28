#!/usr/bin/env python3
"""Analyze and plot results from o1_instability_exp.py."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np


REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "analysis" / "data"
OUT_DIR = REPO_ROOT / "analysis" / "charts" / "thesis"

# Match thesis figure styling from build_thesis_charts.py
THESIS_TEXTWIDTH_IN = 6.50
THESIS_RC = {
    "text.usetex": True,
    "font.family": "serif",
    "font.serif": ["Computer Modern Roman"],
    "font.size": 8.5,
    "axes.labelsize": 8.5,
    "axes.titlesize": 9.0,
    "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.8,
    "legend.fontsize": 7.5,
    "axes.linewidth": 0.6,
    "grid.linewidth": 0.45,
    "lines.linewidth": 1.4,
}

CONFIG_ORDER = ["O1", "O1_align", "O2", "O3_native"]
CONFIG_LABELS = {
    "O1": r"\texttt{O1}",
    "O1_align": r"\texttt{O1\_align}",
    "O2": r"\texttt{O2}",
    "O3_native": r"\texttt{O3}",
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


def latex_bench_label(bench: str) -> str:
    s = str(bench).replace("_", r"\_").replace("%", r"\%")
    return fr"\texttt{{{s}}}"


def ordered_benchmarks(records: list[dict]) -> list[str]:
    """Order benchmarks descending by -O1 max/min cycle spread (matching tables)."""
    benchmarks = list(dict.fromkeys(r["benchmark"] for r in records))

    def o1_cycle_spread(b: str) -> float:
        cyc = [r["median_cycles"] for r in records if r["benchmark"] == b and r["config"] == "O1"]
        return (max(cyc) / min(cyc) - 1.0) * 100.0 if cyc else 0.0

    return sorted(benchmarks, key=o1_cycle_spread, reverse=True)


def load_sweep(path: Path) -> list[dict]:
    records = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def print_summary(records: list[dict], perf_data: list[dict] | None) -> None:
    benchmarks = ordered_benchmarks(records)

    print("\n## Experiment 1: Code-Layout Perturbation Sensitivity (Max/Min Cycle Spread %)")
    print("| Benchmark | Suite | -O1 | -O1 + align | -O2 | -O3 -march=native |")
    print("| :--- | :--- | ---: | ---: | ---: | ---: |")
    for b in benchmarks:
        brecs = [r for r in records if r["benchmark"] == b]
        suite = brecs[0]["suite"]
        row = [b, suite]
        for cfg in CONFIG_ORDER:
            crecs = [r for r in brecs if r["config"] == cfg]
            cyc = [r["median_cycles"] for r in crecs]
            spread = (max(cyc) / min(cyc) - 1.0) * 100.0
            row.append(f"{spread:.2f}%")
        print("| " + " | ".join(row) + " |")

    print("\n## Experiment 1: Instruction Count Max/Min Spread %")
    print("| Benchmark | Suite | -O1 | -O1 + align | -O2 | -O3 -march=native |")
    print("| :--- | :--- | ---: | ---: | ---: | ---: |")
    for b in benchmarks:
        brecs = [r for r in records if r["benchmark"] == b]
        suite = brecs[0]["suite"]
        row = [b, suite]
        for cfg in CONFIG_ORDER:
            crecs = [r for r in brecs if r["config"] == cfg]
            insts = [r["median_instructions"] for r in crecs]
            spread = (max(insts) / min(insts) - 1.0) * 100.0
            row.append(f"{spread:.3f}%")
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
        print("\n## Experiment 2: Ice Lake TMA Root-Cause Comparison (Fast vs. Slow -O1 Offset)")
        for entry in perf_data:
            b = entry["benchmark"]
            pf = entry["profiles"]["O1_fast"]
            ps = entry["profiles"]["O1_slow"]
            cf, cs = pf["counters"], ps["counters"]
            df, ds = pf["derived"], ps["derived"]
            cyc_diff = (cs["cycles"] / cf["cycles"] - 1.0) * 100.0
            inst_diff = (cs["instructions"] / cf["instructions"] - 1.0) * 100.0
            print(f"\n### `{b}` (`-O1` fast N={entry['o1_fast_offset']} vs. slow N={entry['o1_slow_offset']}: +{cyc_diff:.2f}% cycles, {inst_diff:+.3f}% instructions)")
            print("| Variant | Offset | Cycles (B) | Insts (B) | IPC | FE Bound % | BE Bound % | DSB uops % | MITE uops % | DSB->MITE Pen (M) | ICache Stall (M) |")
            print("| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
            for label in ["O1_fast", "O1_slow", "O1_align_N0", "O2_N0", "O3_native_N0"]:
                if label not in entry["profiles"]:
                    continue
                p = entry["profiles"][label]
                c, d = p["counters"], p["derived"]
                print(
                    f"| `{label}` | {p['offset']} | {c['cycles']/1e9:.3f} | {c['instructions']/1e9:.3f} "
                    f"| {d['ipc']:.2f} | {d['fe_bound_pct']:.1f}% | {d['be_bound_pct']:.1f}% "
                    f"| {d['dsb_share_pct']:.1f}% | {d['mite_share_pct']:.1f}% "
                    f"| {c.get('dsb2mite_switches.penalty_cycles', 0.0)/1e6:.2f} "
                    f"| {c.get('icache_64b.iftag_stall', 0.0)/1e6:.2f} |"
                )


def plot_sweep_grid(records: list[dict], out_prefix: Path) -> None:
    benchmarks = ordered_benchmarks(records)
    ncols = 4
    nrows = (len(benchmarks) + ncols - 1) // ncols
    fig_h = 1.48 * nrows + 0.55

    with plt.rc_context(THESIS_RC):
        fig, axes = plt.subplots(
            nrows, ncols,
            figsize=(THESIS_TEXTWIDTH_IN, fig_h),
            sharex=True,
            layout="constrained",
        )
        axes_flat = np.array(axes).reshape(-1)

        for i, b in enumerate(benchmarks):
            ax = axes_flat[i]
            brecs = [r for r in records if r["benchmark"] == b]
            all_ys = []
            for cfg in CONFIG_ORDER:
                crecs = sorted([r for r in brecs if r["config"] == cfg], key=lambda r: r["offset"])
                xs = [r["offset"] for r in crecs]
                cyc = [r["median_cycles"] for r in crecs]
                med = statistics.median(cyc)
                ys = [(c / med - 1.0) * 100.0 for c in cyc]
                all_ys.extend(ys)
                ax.plot(
                    xs, ys,
                    label=CONFIG_LABELS[cfg],
                    color=CONFIG_COLORS[cfg],
                    marker=CONFIG_MARKERS[cfg],
                    markersize=2.6,
                    linewidth=1.25 if cfg == "O1" else 0.95,
                    alpha=0.92 if cfg == "O1" else 0.85,
                    zorder=5 if cfg == "O1" else 3,
                )
            ax.axhline(0.0, color="0.4", linestyle="--", linewidth=0.65, alpha=0.8, zorder=2)
            ax.set_title(latex_bench_label(b), fontsize=8.0, pad=2.5)
            ax.set_xticks([0, 16, 32, 48, 60])
            yspan = (max(all_ys) - min(all_ys)) if all_ys else 1.0
            decimals = 0 if yspan >= 4.0 else 1
            ax.yaxis.set_major_formatter(ticker.PercentFormatter(decimals=decimals))
            ax.yaxis.set_major_locator(ticker.MaxNLocator(nbins=4, integer=(decimals == 0)))
            ax.tick_params(axis="x", labelsize=6.8, length=2.5, pad=1.5)
            ax.tick_params(axis="y", labelsize=6.8, length=2.5, pad=1.5)
            ax.grid(True, linestyle=":", alpha=0.5, zorder=0)

        for j in range(len(benchmarks), len(axes_flat)):
            axes_flat[j].set_visible(False)

        handles, labels = axes_flat[0].get_legend_handles_labels()
        fig.legend(
            handles, labels,
            loc="outside upper center",
            ncol=len(CONFIG_ORDER),
            frameon=True,
            fontsize=7.5,
        )
        fig.supylabel(r"Cycles vs.\ median (\%)", fontsize=8.5)
        fig.supxlabel(r"Entry \texttt{NOP} padding $N$ (bytes)", fontsize=8.5)

        for ext in ("pdf", "png"):
            out_path = out_prefix.with_suffix(f".{ext}")
            save_kwargs = {"bbox_inches": "tight"}
            if ext == "pdf":
                save_kwargs["metadata"] = {"CreationDate": None}
            else:
                save_kwargs["dpi"] = 200
            fig.savefig(out_path, **save_kwargs)
            print(f"Wrote {out_path}")
        plt.close(fig)


def plot_spread_bar(records: list[dict], out_prefix: Path) -> None:
    benchmarks = ordered_benchmarks(records)
    x = np.arange(len(benchmarks))
    width = 0.2

    with plt.rc_context(THESIS_RC):
        fig, ax = plt.subplots(figsize=(THESIS_TEXTWIDTH_IN, 2.75), layout="constrained")
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
                zorder=3,
            )
            if cfg == "O1":
                for bar, val in zip(bars, spreads):
                    if val >= 2.0:
                        ax.text(
                            bar.get_x() + bar.get_width() / 2.0,
                            val + 0.6,
                            fr"{val:.1f}\%",
                            ha="center",
                            va="bottom",
                            fontsize=6.8,
                            color=CONFIG_COLORS["O1"],
                        )

        ax.set_xticks(x)
        ax.set_xticklabels([latex_bench_label(b) for b in benchmarks], rotation=20, ha="right", fontsize=7.5)
        ax.yaxis.set_major_formatter(ticker.PercentFormatter(decimals=0))
        ax.set_ylabel(r"Max/min cycle spread (\%)", fontsize=8.5)
        ax.grid(True, axis="y", linestyle=":", alpha=0.5, zorder=0)
        ax.legend(frameon=True, fontsize=7.5, loc="upper right")
        for ext in ("pdf", "png"):
            out_path = out_prefix.with_suffix(f".{ext}")
            save_kwargs = {"bbox_inches": "tight"}
            if ext == "pdf":
                save_kwargs["metadata"] = {"CreationDate": None}
            else:
                save_kwargs["dpi"] = 200
            fig.savefig(out_path, **save_kwargs)
            print(f"Wrote {out_path}")
        plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize and plot -O1 instability results.")
    parser.add_argument("--sweep", type=Path, default=DATA_DIR / "o1_instability_sweep.jsonl")
    parser.add_argument("--perf", type=Path, default=DATA_DIR / "o1_instability_perf.json")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()

    records = load_sweep(args.sweep)
    perf_data = json.loads(args.perf.read_text()) if args.perf.exists() else None
    print_summary(records, perf_data)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    plot_sweep_grid(records, args.out_dir / "o1_instability_sweep")
    plot_spread_bar(records, args.out_dir / "o1_instability_spread_bar")


if __name__ == "__main__":
    main()
