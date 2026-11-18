"""Generate thesis-specific benchmark charts for solution.tex.

Leaves the standalone all_charts.pdf pipeline (charts/*.pdf) completely untouched
by writing publication-sized, outlier-clipped figures to `<output_directory>/thesis/`.
"""

import argparse
import json
import os
import re
import sys

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd

from build_charts_lib import (
    CHECKSUM_FIELD_PARALLEL,
    COMPILER_NAME_FIELD_PARALLEL,
    METADATA_KEYS,
    USE_NEW_ANALYSIS_STYLE,
    calculate_error_bars,
    compute_bar_series,
    compute_parallel_bench_benchmark,
    compute_parallel_bench_geomean,
    infer_configs,
    load_df,
    resolve_series_path,
)

# Exact LaTeX textwidth on US Letter with 1in margins: 6.50 inches
THESIS_TEXTWIDTH_IN = 6.50
THESIS_HALFWIDTH_IN = 3.12

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


def latex_escape_text(text: str) -> str:
    """Format plain config labels cleanly for LaTeX usetex."""
    if not text:
        return ""
    s = str(text)
    # Fix typo present in config.json display strings without altering config.json
    s = s.replace("basline", "baseline")
    # Convert markdown backtick spans `...` to \texttt{...}
    def _repl_code(m):
        inner = m.group(1).replace("_", r"\_").replace("%", r"\%")
        return fr"\texttt{{{inner}}}"

    parts = re.split(r"(`[^`]+`)", s)
    out = []
    for p in parts:
        if p.startswith("`") and p.endswith("`") and len(p) >= 2:
            out.append(_repl_code(re.match(r"`([^`]+)`", p)))
        else:
            p_esc = p.replace("_", r"\_").replace("%", r"\%")
            out.append(p_esc)
    return "".join(out)


def latex_bench_label(bench: str) -> str:
    s = str(bench).replace("_", r"\_").replace("%", r"\%")
    return fr"\texttt{{{s}}}"


def _nice_bound(val: float, direction: str) -> float:
    """Round axis bound outward to a clean tick-friendly value."""
    if val == 0:
        return 0.0
    abs_v = abs(val)
    if abs_v <= 6:
        step = 1.0
    elif abs_v <= 20:
        step = 2.0
    elif abs_v <= 60:
        step = 5.0
    else:
        step = 10.0
    if direction == "up":
        return float(np.ceil(val / step) * step)
    return float(np.floor(val / step) * step)


def compute_bar_clip_bounds(vals, los, his, min_ratio_to_second=3.0, min_span_reduction=0.35):
    """Determine [xlim_lo, xlim_hi] for horizontal bar charts, clipping extreme outliers."""
    vals = np.asarray(vals, dtype=float)
    los = np.asarray(los, dtype=float)
    his = np.asarray(his, dtype=float)
    valid = np.isfinite(vals)
    if not np.any(valid):
        return -5.0, 5.0

    vals = vals[valid]
    los = los[valid]
    his = his[valid]

    raw_lo = min(0.0, float(np.min(los)))
    raw_hi = max(0.0, float(np.max(his)))
    raw_span = max(1e-6, raw_hi - raw_lo)

    clip_lo = None
    clip_hi = None

    if len(his) >= 5:
        sorted_his = np.sort(his)
        max_hi = sorted_his[-1]
        second_hi = max(0.0, float(sorted_his[-2]))
        if max_hi > 15.0 and max_hi >= min_ratio_to_second * max(second_hi, 5.0):
            cand_hi = _nice_bound(max(second_hi * 1.38, 12.0), "up")
            if (raw_hi - cand_hi) >= min_span_reduction * raw_span:
                clip_hi = cand_hi

        sorted_los = np.sort(los)
        min_lo = sorted_los[0]
        second_lo = min(0.0, float(sorted_los[1]))
        if min_lo < -15.0 and abs(min_lo) >= min_ratio_to_second * max(abs(second_lo), 5.0):
            cand_lo = _nice_bound(min(second_lo * 1.38, -12.0), "down")
            if (cand_lo - raw_lo) >= min_span_reduction * raw_span:
                clip_lo = cand_lo

    eff_lo = clip_lo if clip_lo is not None else raw_lo
    eff_hi = clip_hi if clip_hi is not None else raw_hi
    eff_span = max(1e-6, eff_hi - eff_lo)

    final_lo = clip_lo if clip_lo is not None else (raw_lo - 0.07 * eff_span if raw_lo < 0 else -0.04 * eff_span)
    final_hi = clip_hi if clip_hi is not None else (raw_hi + 0.08 * eff_span if raw_hi > 0 else 0.04 * eff_span)
    if final_hi - final_lo < 0.5:
        final_lo, final_hi = -0.5, 0.5
    return final_lo, final_hi


def compute_trellis_ylim(results_df: pd.DataFrame, use_new_analysis_style=USE_NEW_ANALYSIS_STYLE):
    """Compute shared (ymin, ymax) for trellis plots, clipping runaway single-benchmark CIs/outliers."""
    if results_df.empty:
        return -10.0, 10.0

    vals = results_df["relative_pct"].to_numpy(dtype=float)
    if use_new_analysis_style and "err_minus_pct" in results_df.columns:
        los = vals - results_df["err_minus_pct"].to_numpy(dtype=float)
        his = vals + results_df["err_plus_pct"].to_numpy(dtype=float)
    elif "std_pct" in results_df.columns:
        los = vals - results_df["std_pct"].to_numpy(dtype=float)
        his = vals + results_df["std_pct"].to_numpy(dtype=float)
    else:
        los = vals.copy()
        his = vals.copy()

    raw_lo = min(-2.0, float(np.nanmin(los)))
    raw_hi = max(2.0, float(np.nanmax(his)))
    raw_span = max(1e-6, raw_hi - raw_lo)

    bench_groups = results_df.groupby("bench")
    bench_max_val = bench_groups["relative_pct"].max().sort_values()
    bench_min_val = bench_groups["relative_pct"].min().sort_values()

    tmp = results_df.copy()
    tmp["_lo"] = los
    tmp["_hi"] = his
    bench_max_hi = tmp.groupby("bench")["_hi"].max().sort_values()
    bench_min_lo = tmp.groupby("bench")["_lo"].min().sort_values()
    n_b = len(bench_max_hi)

    cand_hi = raw_hi
    cand_lo = raw_lo

    if n_b >= 6:
        # Exclude at most the single worst runaway CI benchmark (or top 2 if >=8 benches and 2nd is also extreme)
        drop_hi = 2 if (n_b >= 8 and bench_max_hi.iloc[-2] > 2.2 * max(float(bench_max_hi.iloc[-3]), 15.0)) else 1
        ref_val_hi = float(bench_max_val.iloc[-2]) if float(bench_max_val.iloc[-1]) > 2.5 * max(float(bench_max_val.iloc[-2]), 12.0) else float(bench_max_val.iloc[-1])
        ref_ci_hi = float(bench_max_hi.iloc[-(drop_hi + 1)])
        target_hi = _nice_bound(max(ref_val_hi * 1.15, ref_ci_hi * 1.12, 15.0), "up")
        if (raw_hi - target_hi) >= 0.24 * raw_span:
            cand_hi = target_hi

        post_hi_span = max(1e-6, cand_hi - raw_lo)
        drop_lo = 1
        ref_val_lo = float(bench_min_val.iloc[1]) if abs(float(bench_min_val.iloc[0])) > 2.5 * max(abs(float(bench_min_val.iloc[1])), 12.0) else float(bench_min_val.iloc[0])
        ref_ci_lo = float(bench_min_lo.iloc[drop_lo])
        target_lo = _nice_bound(min(ref_val_lo * 1.15, ref_ci_lo * 1.12, -15.0), "down")
        if (target_lo - raw_lo) >= 0.24 * post_hi_span:
            cand_lo = target_lo

    span = cand_hi - cand_lo
    pad_lo = cand_lo - (0.06 * span if cand_lo == raw_lo else 0.03 * span)
    pad_hi = cand_hi + (0.06 * span if cand_hi == raw_hi else 0.03 * span)
    return pad_lo, pad_hi


def find_best_badge_corner(vals_arr, los_arr, his_arr, xlim_lo, xlim_hi, min_clear_frac=0.52):
    """Pick the corner of a horizontal bar plot with the least data overlap, expanding xlim slightly if needed."""
    n = len(vals_arr)
    if n == 0:
        return "upper right", xlim_lo, xlim_hi
    k = max(1, min(4, int(np.ceil(n * 0.22))))
    # Remember: yaxis is inverted (index 0 is at the top, index n-1 is at the bottom)
    top_slice = slice(0, k)
    bot_slice = slice(n - k, n)

    span = max(1e-6, xlim_hi - xlim_lo)
    clear_ur = (xlim_hi - max(0.0, float(np.nanmax(his_arr[top_slice])))) / span
    clear_lr = (xlim_hi - max(0.0, float(np.nanmax(his_arr[bot_slice])))) / span
    clear_ul = (min(0.0, float(np.nanmin(los_arr[top_slice]))) - xlim_lo) / span
    clear_ll = (min(0.0, float(np.nanmin(los_arr[bot_slice]))) - xlim_lo) / span

    candidates = [
        (clear_lr + 0.03, clear_lr, "lower right"),
        (clear_ur + 0.02, clear_ur, "upper right"),
        (clear_ll, clear_ll, "lower left"),
        (clear_ul, clear_ul, "upper left"),
    ]
    candidates.sort(key=lambda x: x[0], reverse=True)
    _, best_raw_clear, corner = candidates[0]
    if best_raw_clear < min_clear_frac:
        extra = ((min_clear_frac - best_raw_clear) / max(0.15, 1.0 - min_clear_frac)) * span
        if "right" in corner:
            xlim_hi = xlim_hi + extra
        else:
            xlim_lo = xlim_lo - extra
    return corner, xlim_lo, xlim_hi


def place_geomean_badge(ax, geomean_pct, corner="lower right", fontsize=7.2):
    if pd.isna(geomean_pct):
        return
    textstr = fr"Geomean: {geomean_pct:+.1f}\%"
    pos_map = {
        "upper right": (0.96, 0.96, "top", "right"),
        "lower right": (0.96, 0.04, "bottom", "right"),
        "upper left": (0.04, 0.96, "top", "left"),
        "lower left": (0.04, 0.04, "bottom", "left"),
    }
    x, y, va, ha = pos_map.get(corner, pos_map["lower right"])
    props = dict(boxstyle="round,pad=0.28", facecolor="white", alpha=0.92, edgecolor="0.4", linewidth=0.5)
    ax.text(x, y, textstr, transform=ax.transAxes, fontsize=fontsize, va=va, ha=ha, bbox=props, zorder=15)


def draw_clipped_hbar_panel(
    ax,
    y_positions,
    vals,
    err_minus=None,
    err_plus=None,
    bar_height=0.68,
    color="tab:blue",
    label=None,
    xlim=None,
    annotate_fontsize=6.8,
):
    """Draw horizontal bars with automatic clipping markers and value annotations."""
    vals = np.asarray(vals, dtype=float)
    n = len(vals)
    em = np.zeros(n) if err_minus is None else np.asarray(err_minus, dtype=float)
    ep = np.zeros(n) if err_plus is None else np.asarray(err_plus, dtype=float)
    los = vals - em
    his = vals + ep

    if xlim is None:
        xlim_lo, xlim_hi = compute_bar_clip_bounds(vals, los, his)
    else:
        xlim_lo, xlim_hi = xlim
    span = max(1e-6, xlim_hi - xlim_lo)

    # Clamp bar endpoints slightly inside spine if clipped so arrow & break are crisp
    margin = 0.025 * span
    draw_vals = np.clip(vals, xlim_lo + margin, xlim_hi - margin)

    ax.barh(
        y_positions,
        draw_vals,
        height=bar_height,
        color=color,
        edgecolor="black",
        linewidth=0.4,
        alpha=0.88,
        label=label,
        zorder=3,
    )

    has_err = (err_minus is not None) and (np.any(em > 0) or np.any(ep > 0))
    for idx in range(n):
        y = y_positions[idx]
        v = vals[idx]
        if not np.isfinite(v):
            continue
        lo = los[idx]
        hi = his[idx]

        if v > xlim_hi - margin:
            # Bar itself clipped on positive side
            ax.plot(
                xlim_hi - 0.015 * span,
                y,
                marker=">",
                color="black",
                markersize=3.8,
                zorder=12,
                clip_on=False,
            )
            lbl = fr"\textbf{{{v:+.1f}\%}}"
            ax.text(
                xlim_hi - 0.05 * span,
                y,
                lbl,
                va="center",
                ha="right",
                fontsize=annotate_fontsize,
                bbox=dict(boxstyle="round,pad=0.14", facecolor="white", edgecolor=color, linewidth=0.5, alpha=0.95),
                zorder=14,
            )
        elif v < xlim_lo + margin:
            # Bar itself clipped on negative side
            ax.plot(
                xlim_lo + 0.015 * span,
                y,
                marker="<",
                color="black",
                markersize=3.8,
                zorder=12,
                clip_on=False,
            )
            lbl = fr"\textbf{{{v:+.1f}\%}}"
            ax.text(
                xlim_lo + 0.05 * span,
                y,
                lbl,
                va="center",
                ha="left",
                fontsize=annotate_fontsize,
                bbox=dict(boxstyle="round,pad=0.14", facecolor="white", edgecolor=color, linewidth=0.5, alpha=0.95),
                zorder=14,
            )
        elif has_err and (em[idx] > 0 or ep[idx] > 0):
            # Bar fits; check error bar bounds
            lo_clamped = max(lo, xlim_lo + 0.015 * span)
            hi_clamped = min(hi, xlim_hi - 0.015 * span)
            ax.plot([lo_clamped, hi_clamped], [y, y], color="black", linewidth=0.75, zorder=5)
            cap_h = bar_height * 0.28
            if lo >= xlim_lo + 0.015 * span:
                ax.plot([lo, lo], [y - cap_h, y + cap_h], color="black", linewidth=0.75, zorder=5)
            else:
                ax.plot(xlim_lo + 0.015 * span, y, marker="<", color="black", markersize=3.0, zorder=6)
                ax.text(
                    xlim_lo + 0.04 * span,
                    y,
                    fr"{lo:+.0f}\%",
                    va="center",
                    ha="left",
                    fontsize=annotate_fontsize - 0.5,
                    bbox=dict(boxstyle="round,pad=0.1", facecolor="white", edgecolor="none", alpha=0.88),
                    zorder=13,
                )
            if hi <= xlim_hi - 0.015 * span:
                ax.plot([hi, hi], [y - cap_h, y + cap_h], color="black", linewidth=0.75, zorder=5)
            else:
                ax.plot(xlim_hi - 0.015 * span, y, marker=">", color="black", markersize=3.0, zorder=6)
                ax.text(
                    xlim_hi - 0.04 * span,
                    y,
                    fr"{hi:+.0f}\%",
                    va="center",
                    ha="right",
                    fontsize=annotate_fontsize - 0.5,
                    bbox=dict(boxstyle="round,pad=0.1", facecolor="white", edgecolor="none", alpha=0.88),
                    zorder=13,
                )

    ax.set_xlim(xlim_lo, xlim_hi)
    return xlim_lo, xlim_hi


def annotate_clipped_line_panel(ax, series_data_list, ylim_lo, ylim_hi, fontsize=6.3):
    """Add border arrows and a single clean summary callout for clipped points/CIs on a line panel.

    series_data_list: list of dicts with keys:
      'procs', 'vals', 'los', 'his', 'color', 'name'
    """
    span = max(1e-6, ylim_hi - ylim_lo)
    notes = []
    any_in_top_left = False
    any_in_bot_left = False

    all_procs = sorted({p for sd in series_data_list for p in sd["procs"]})
    low_proc_cutoff = all_procs[min(3, len(all_procs) - 1)] if all_procs else 8

    # Aggregate clipped-value notes cleanly across series on this panel
    max_over_val = None  # (val, proc, hi)
    max_over_ci = None
    min_under_val = None  # (val, proc, lo)
    min_under_ci = None

    for sd in series_data_list:
        procs = np.asarray(sd["procs"], dtype=float)
        vals = np.asarray(sd["vals"], dtype=float)
        los = np.asarray(sd["los"], dtype=float)
        his = np.asarray(sd["his"], dtype=float)
        color = sd["color"]

        for p, v, lo, hi in zip(procs, vals, los, his):
            if p <= low_proc_cutoff:
                if min(v, hi) > ylim_lo + 0.62 * span:
                    any_in_top_left = True
                if max(v, lo) < ylim_lo + 0.38 * span:
                    any_in_bot_left = True

            if v > ylim_hi:
                ax.plot(p, ylim_hi - 0.03 * span, marker="^", color=color, markersize=4.2, zorder=12)
                if max_over_val is None or v > max_over_val[0]:
                    max_over_val = (float(v), int(p), float(hi))
            elif hi > ylim_hi:
                ax.plot([p, p], [v, ylim_hi - 0.025 * span], color=color, linewidth=0.9, alpha=0.85, zorder=4)
                ax.plot(p, ylim_hi - 0.025 * span, marker="^", color=color, markersize=3.0, zorder=11)
                if max_over_ci is None or hi > max_over_ci:
                    max_over_ci = float(hi)

            if v < ylim_lo:
                ax.plot(p, ylim_lo + 0.03 * span, marker="v", color=color, markersize=4.2, zorder=12)
                if min_under_val is None or v < min_under_val[0]:
                    min_under_val = (float(v), int(p), float(lo))
            elif lo < ylim_lo:
                ax.plot([p, p], [ylim_lo + 0.025 * span, v], color=color, linewidth=0.9, alpha=0.85, zorder=4)
                ax.plot(p, ylim_lo + 0.025 * span, marker="v", color=color, markersize=3.0, zorder=11)
                if min_under_ci is None or lo < min_under_ci:
                    min_under_ci = float(lo)

    if max_over_val is not None:
        v_max, p_max, hi_max = max_over_val
        hi_all = max(hi_max, max_over_ci or hi_max)
        if hi_all > v_max + 1.0:
            notes.append(fr"{p_max}c: ${v_max:+.0f}\%$" + "\n" + fr"(CI ${hi_all:+.0f}\%$)")
        else:
            notes.append(fr"{p_max}c: ${v_max:+.0f}\%$")
    elif max_over_ci is not None:
        notes.append(fr"CI up to ${max_over_ci:+.0f}\%$")

    if min_under_val is not None:
        v_min, p_min, lo_min = min_under_val
        lo_all = min(lo_min, min_under_ci or lo_min)
        if lo_all < v_min - 1.0:
            notes.append(fr"{p_min}c: ${v_min:+.0f}\%$" + "\n" + fr"(CI ${lo_all:+.0f}\%$)")
        else:
            notes.append(fr"{p_min}c: ${v_min:+.0f}\%$")
    elif min_under_ci is not None:
        notes.append(fr"CI to ${min_under_ci:+.0f}\%$")

    if notes:
        text = "\n".join(notes[:2])
        if not any_in_top_left:
            x_pos, y_pos, va, ha = 0.04, 0.94, "top", "left"
        elif not any_in_bot_left:
            x_pos, y_pos, va, ha = 0.04, 0.06, "bottom", "left"
        else:
            x_pos, y_pos, va, ha = 0.04, 0.94, "top", "left"
        ax.text(
            x_pos,
            y_pos,
            text,
            transform=ax.transAxes,
            fontsize=fontsize,
            va=va,
            ha=ha,
            bbox=dict(boxstyle="round,pad=0.16", facecolor="white", edgecolor="0.65", linewidth=0.4, alpha=0.92),
            zorder=15,
        )


def _save_pdf(fig, out_dir: str, out_filename: str):
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{out_filename}.pdf")
    print(f"Saving thesis chart to {path}")
    fig.savefig(path, format="pdf", metadata={"CreationDate": None})
    plt.close(fig)


def plot_mlton_shared(df, type_name: str, out_dir: str, abbrevs=("MLton0", "MLton1"), use_new_analysis_style=USE_NEW_ANALYSIS_STYLE):
    """Plot 1x3 shared-y horizontal bar chart (Run time | Compile time | Binary size) for MLton suite."""
    filtered = df[df.groupby("bench")["binaryChecksum"].transform("nunique") > 1]
    if filtered.empty:
        return

    metrics = [
        ("runTime", r"\textsf{\textbf{(a)} Run time}"),
        ("compileTime", r"\textsf{\textbf{(b)} Compile time}"),
        ("binarySize", r"\textsf{\textbf{(c)} Binary size}"),
    ]

    panel_data = []
    all_benches = set()
    for col, header in metrics:
        piv = filtered.pivot(index="bench", columns="compilerAbbrev", values=col).dropna(subset=[abbrevs[0], abbrevs[1]])
        if piv.empty:
            continue
        if use_new_analysis_style:
            abs_ratio = piv.apply(lambda r: np.mean(r[abbrevs[1]]) / np.mean(r[abbrevs[0]]), axis=1)
        else:
            abs_ratio = piv[abbrevs[1]] / piv[abbrevs[0]]
        rel_pct = (abs_ratio - 1.0) * 100.0
        geomean_pct = (np.exp(np.mean(np.log(abs_ratio.dropna()))) - 1.0) * 100.0
        all_benches.update(rel_pct.index)
        panel_data.append((header, rel_pct, geomean_pct))

    if not panel_data or not all_benches:
        return

    benches = sorted(all_benches)
    n_b = len(benches)
    fig_h = max(2.05, 0.78 + 0.165 * n_b)

    with plt.rc_context(THESIS_RC):
        fig, axes = plt.subplots(1, len(panel_data), figsize=(THESIS_TEXTWIDTH_IN, fig_h), sharey=True, layout="constrained")
        axes = np.atleast_1d(axes)
        y_pos = np.arange(n_b)

        for idx, (header, rel_pct, geomean_pct) in enumerate(panel_data):
            ax = axes[idx]
            vals = np.array([rel_pct.get(b, np.nan) for b in benches], dtype=float)
            xlim_lo, xlim_hi = draw_clipped_hbar_panel(ax, y_pos, vals, color="tab:blue")
            ax.axvline(0, color="0.35", linestyle="--", linewidth=0.7, zorder=2)
            ax.grid(True, axis="x", linestyle=":", alpha=0.55, zorder=0)
            ax.xaxis.set_major_formatter(ticker.PercentFormatter(decimals=0 if (xlim_hi - xlim_lo) >= 12 else 1))
            ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=4))
            ax.set_title(header, fontsize=9.0, pad=5)
            ax.set_xlabel(r"Change (\%)", fontsize=8.0)

            corner, xlim_lo, xlim_hi = find_best_badge_corner(vals, vals, vals, xlim_lo, xlim_hi, min_clear_frac=0.65)
            ax.set_xlim(xlim_lo, xlim_hi)
            ax.xaxis.set_major_formatter(ticker.PercentFormatter(decimals=0 if (xlim_hi - xlim_lo) >= 12 else 1))
            place_geomean_badge(ax, geomean_pct, corner=corner, fontsize=6.8)

        axes[0].set_yticks(y_pos)
        axes[0].set_yticklabels([latex_bench_label(b) for b in benches], fontsize=7.8)
        axes[0].invert_yaxis()
        axes[0].set_ylim(n_b - 0.4, -0.6)

        _save_pdf(fig, out_dir, f"{type_name}_mlton_shared")


def _extract_parallel_metric_series(df, values: str, abbrevs=None, use_new_analysis_style=USE_NEW_ANALYSIS_STYLE):
    base_key, test_key = infer_configs(df, abbrevs)
    work = df.copy()
    if values in ("binary_bytes", "binarySize") and "procs" in work.columns:
        work = work[work["procs"] == 1].copy()

    filtered = work[["bench", COMPILER_NAME_FIELD_PARALLEL, values, CHECKSUM_FIELD_PARALLEL]]
    filtered = filtered[filtered[COMPILER_NAME_FIELD_PARALLEL].isin([base_key, test_key])]
    filtered = filtered[filtered.groupby("bench")[CHECKSUM_FIELD_PARALLEL].transform("nunique") > 1]
    if filtered.empty:
        return None
    filtered = filtered.drop_duplicates(subset=["bench", COMPILER_NAME_FIELD_PARALLEL], keep="last")
    piv = filtered.pivot(index="bench", columns=COMPILER_NAME_FIELD_PARALLEL, values=values).dropna(subset=[base_key, test_key])
    if piv.empty:
        return None

    if use_new_analysis_style:
        mean_ratios = piv.apply(lambda r: np.mean(r[test_key]) / np.mean(r[base_key]), axis=1)
        em, ep = calculate_error_bars(piv[test_key], piv[base_key], random_state=42)
        em_pct = np.asarray(em, dtype=float) * 100.0
        ep_pct = np.asarray(ep, dtype=float) * 100.0
    else:
        all_ratios = piv.apply(lambda r: np.array(r[test_key]) / np.array(r[base_key]), axis=1)
        mean_ratios = all_ratios.apply(np.mean)
        std_pct = all_ratios.apply(lambda a: np.std(np.atleast_1d(a), ddof=1) if len(np.atleast_1d(a)) > 1 else 0.0).to_numpy() * 100.0
        em_pct = std_pct
        ep_pct = std_pct

    rel_pct = (mean_ratios - 1.0) * 100.0
    geomean_pct = (np.exp(np.mean(np.log(mean_ratios.dropna()))) - 1.0) * 100.0
    return pd.DataFrame({
        "bench": piv.index,
        "relative_pct": rel_pct.to_numpy(dtype=float),
        "err_minus_pct": em_pct,
        "err_plus_pct": ep_pct,
    }).set_index("bench"), geomean_pct


def plot_parallel_bench_mlton_shared(df, type_name: str, out_dir: str, use_new_analysis_style=USE_NEW_ANALYSIS_STYLE):
    """Plot 1x2 shared-y horizontal bar chart (Run time | Binary size) for parallel-ml-bench on MLton."""
    run_res = _extract_parallel_metric_series(df, "test_results_secs", use_new_analysis_style=use_new_analysis_style)
    size_res = _extract_parallel_metric_series(df, "binary_bytes", use_new_analysis_style=use_new_analysis_style)
    if run_res is None and size_res is None:
        return

    panels = []
    all_benches = set()
    if run_res is not None:
        panels.append((r"\textsf{\textbf{(a)} Run time}", run_res[0], run_res[1], True))
        all_benches.update(run_res[0].index)
    if size_res is not None:
        lbl = r"\textsf{\textbf{(b)} Binary size}" if len(panels) == 1 else r"\textsf{\textbf{(a)} Binary size}"
        panels.append((lbl, size_res[0], size_res[1], False))
        all_benches.update(size_res[0].index)

    benches = sorted(all_benches)
    n_b = len(benches)
    fig_h = max(2.35, 0.78 + 0.16 * n_b)

    with plt.rc_context(THESIS_RC):
        fig, axes = plt.subplots(1, len(panels), figsize=(THESIS_TEXTWIDTH_IN, fig_h), sharey=True, layout="constrained")
        axes = np.atleast_1d(axes)
        y_pos = np.arange(n_b)

        for idx, (header, res_df, geomean_pct, show_err) in enumerate(panels):
            ax = axes[idx]
            vals = np.array([res_df.loc[b, "relative_pct"] if b in res_df.index else np.nan for b in benches], dtype=float)
            em = np.array([res_df.loc[b, "err_minus_pct"] if (show_err and b in res_df.index) else 0.0 for b in benches], dtype=float)
            ep = np.array([res_df.loc[b, "err_plus_pct"] if (show_err and b in res_df.index) else 0.0 for b in benches], dtype=float)
            los = vals - em
            his = vals + ep

            xlim_lo, xlim_hi = draw_clipped_hbar_panel(
                ax,
                y_pos,
                vals,
                err_minus=em if show_err else None,
                err_plus=ep if show_err else None,
                color="tab:blue",
            )
            ax.axvline(0, color="0.35", linestyle="--", linewidth=0.7, zorder=2)
            ax.grid(True, axis="x", linestyle=":", alpha=0.55, zorder=0)
            ax.xaxis.set_major_formatter(ticker.PercentFormatter(decimals=0 if (xlim_hi - xlim_lo) >= 12 else 1))
            ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=5))
            ax.set_title(header, fontsize=9.0, pad=5)
            ax.set_xlabel(r"Change (\%)", fontsize=8.0)

            corner, xlim_lo, xlim_hi = find_best_badge_corner(vals, los, his, xlim_lo, xlim_hi, min_clear_frac=0.42)
            ax.set_xlim(xlim_lo, xlim_hi)
            ax.xaxis.set_major_formatter(ticker.PercentFormatter(decimals=0 if (xlim_hi - xlim_lo) >= 12 else 1))
            place_geomean_badge(ax, geomean_pct, corner=corner, fontsize=7.0)

        axes[0].set_yticks(y_pos)
        axes[0].set_yticklabels([latex_bench_label(b) for b in benches], fontsize=7.8)
        axes[0].invert_yaxis()
        axes[0].set_ylim(n_b - 0.4, -0.6)

        _save_pdf(fig, out_dir, f"{type_name}_parallel_bench_mlton_shared")


def plot_thesis_trellis(df, type_name: str, out_dir: str, values="test_results_secs", abbrevs=None, use_new_analysis_style=USE_NEW_ANALYSIS_STYLE):
    """Plot full-width, outlier-clipped, decluttered small-multiples trellis for MPL."""
    filtered = df[df.groupby("bench")[CHECKSUM_FIELD_PARALLEL].transform("nunique") > 1]
    if filtered.empty:
        return

    base_key, test_key = infer_configs(filtered, abbrevs)
    filtered = filtered[filtered[COMPILER_NAME_FIELD_PARALLEL].isin([base_key, test_key])]
    filtered = filtered.drop_duplicates(subset=["bench", "procs", COMPILER_NAME_FIELD_PARALLEL], keep="last")
    piv = filtered.pivot(index=["bench", "procs"], columns=COMPILER_NAME_FIELD_PARALLEL, values=values).dropna(subset=[base_key, test_key])
    if piv.empty:
        return

    if use_new_analysis_style:
        mean_ratios = piv.apply(lambda r: np.mean(r[test_key]) / np.mean(r[base_key]), axis=1)
        em, ep = calculate_error_bars(piv[test_key], piv[base_key], random_state=42)
        em_pct = np.asarray(em, dtype=float) * 100.0
        ep_pct = np.asarray(ep, dtype=float) * 100.0
    else:
        all_ratios = piv.apply(lambda r: np.array(r[test_key]) / np.array(r[base_key]), axis=1)
        mean_ratios = all_ratios.apply(np.mean)
        std_pct = all_ratios.apply(lambda a: np.std(np.atleast_1d(a), ddof=1) if len(np.atleast_1d(a)) > 1 else 0.0).to_numpy() * 100.0
        em_pct = std_pct
        ep_pct = std_pct

    rel_pct = (mean_ratios.to_numpy(dtype=float) - 1.0) * 100.0
    results_df = pd.DataFrame({
        "bench": [idx[0] for idx in piv.index],
        "procs": [int(idx[1]) for idx in piv.index],
        "relative_pct": rel_pct,
        "err_minus_pct": em_pct,
        "err_plus_pct": ep_pct,
    })

    df_ratios = pd.DataFrame({
        "procs": [int(idx[1]) for idx in piv.index],
        "mean_ratio": mean_ratios.to_numpy(dtype=float),
    })
    geomean_per_proc = df_ratios.groupby("procs")["mean_ratio"].apply(lambda s: np.exp(np.mean(np.log(s.dropna()))))
    geomean_pct = (geomean_per_proc - 1.0) * 100.0

    benches = sorted(results_df["bench"].unique())
    n_benches = len(benches)
    has_geomean = n_benches > 1
    total_panels = n_benches + (1 if has_geomean else 0)

    if total_panels <= 12:
        ncols = 4
        row_h = 1.32
        title_fs = 8.0
        tick_fs = 6.8
    elif total_panels <= 25:
        ncols = 5
        row_h = 1.12
        title_fs = 7.5
        tick_fs = 6.2
    else:
        ncols = 5
        row_h = 1.04
        title_fs = 7.2
        tick_fs = 6.0

    nrows = int(np.ceil(total_panels / ncols))
    fig_h = min(7.65, max(2.6, nrows * row_h + 0.42))

    ylim_lo, ylim_hi = compute_trellis_ylim(results_df, use_new_analysis_style=use_new_analysis_style)

    unique_procs = sorted(results_df["procs"].unique())
    is_log = len(unique_procs) > 2 and all(p > 0 for p in unique_procs) and max(unique_procs) / min(unique_procs) >= 8

    # Determine bottom-most occupied panel index in each column so every column gets x-tick labels once
    bottom_panel_in_col = {}
    for p_idx in range(total_panels):
        col = p_idx % ncols
        bottom_panel_in_col[col] = p_idx
    bottom_indices = set(bottom_panel_in_col.values())

    with plt.rc_context(THESIS_RC):
        fig, axes = plt.subplots(nrows, ncols, figsize=(THESIS_TEXTWIDTH_IN, fig_h), sharex=False, sharey=True, layout="constrained")
        axes_flat = np.atleast_1d(axes).flatten()

        markers = ["o", "s", "^", "v", "D", "p", "h", "*", "X", "<", ">"]
        colors = plt.rcParams["axes.prop_cycle"].by_key().get("color", ["tab:blue"])

        def _style_panel(ax, panel_idx, title_tex, is_bold=False):
            ax.axhline(0, color="0.4", linestyle="--", linewidth=0.65, alpha=0.8, zorder=2)
            if is_log:
                ax.set_xscale("log", base=2)
            ax.set_xticks(unique_procs)
            ax.get_xaxis().set_major_formatter(ticker.ScalarFormatter())
            ax.set_ylim(ylim_lo, ylim_hi)
            ax.yaxis.set_major_formatter(ticker.PercentFormatter(decimals=0))
            ax.yaxis.set_major_locator(ticker.MaxNLocator(nbins=4))
            show_x = panel_idx in bottom_indices
            ax.tick_params(axis="x", labelbottom=show_x, rotation=45, labelsize=tick_fs, length=2.5, pad=1.5)
            ax.tick_params(axis="y", labelsize=tick_fs + 0.3, length=2.5, pad=1.5)
            if is_bold:
                ax.set_title(fr"\textbf{{{title_tex}}}", fontsize=title_fs, pad=2.5)
            else:
                ax.set_title(title_tex, fontsize=title_fs, pad=2.5)
            ax.grid(True, linestyle=":", alpha=0.5, zorder=0)

        if has_geomean:
            ax0 = axes_flat[0]
            ax0.plot(
                geomean_per_proc.index,
                geomean_pct.to_numpy(dtype=float),
                color="black",
                marker="D",
                linewidth=1.5,
                markersize=3.4,
                zorder=8,
            )
            _style_panel(ax0, 0, "Geomean", is_bold=True)

        offset = 1 if has_geomean else 0
        for i, bench in enumerate(benches):
            p_idx = i + offset
            ax = axes_flat[p_idx]
            b_df = results_df[results_df["bench"] == bench].sort_values("procs")
            procs = b_df["procs"].to_numpy(dtype=int)
            vals = b_df["relative_pct"].to_numpy(dtype=float)
            em_v = b_df["err_minus_pct"].to_numpy(dtype=float)
            ep_v = b_df["err_plus_pct"].to_numpy(dtype=float)
            los = vals - em_v
            his = vals + ep_v

            color = colors[i % len(colors)]
            marker = markers[i % len(markers)]

            # Plot line across all points (clipped cleanly to panel box)
            ax.plot(procs, vals, color=color, linewidth=1.2, alpha=0.9, zorder=5)

            # Plot in-bounds markers and clamped error bars
            in_mask = (vals >= ylim_lo) & (vals <= ylim_hi)
            if np.any(in_mask):
                p_in = procs[in_mask]
                v_in = vals[in_mask]
                lo_in = los[in_mask]
                hi_in = his[in_mask]
                em_clamped = np.where(lo_in >= ylim_lo, v_in - lo_in, 0.0)
                ep_clamped = np.where(hi_in <= ylim_hi, hi_in - v_in, 0.0)
                ax.errorbar(
                    p_in,
                    v_in,
                    yerr=[em_clamped, ep_clamped],
                    fmt=marker,
                    color=color,
                    capsize=2.0,
                    capthick=0.7,
                    elinewidth=0.75,
                    markersize=3.2,
                    alpha=0.9,
                    zorder=6,
                )

            _style_panel(ax, p_idx, latex_bench_label(bench))
            annotate_clipped_line_panel(
                ax,
                [{"procs": procs, "vals": vals, "los": los, "his": his, "color": color, "name": bench}],
                ylim_lo,
                ylim_hi,
                fontsize=5.8 if ncols >= 5 else 6.3,
            )

        for j in range(total_panels, len(axes_flat)):
            fig.delaxes(axes_flat[j])

        fig.supylabel(r"Runtime change (\%)", fontsize=8.5)
        fig.supxlabel("Core count", fontsize=8.5)

        _save_pdf(fig, out_dir, f"{type_name}_parallel_bench_run_mpl_vs_mpl_trellis")


def plot_thesis_mpl_summary(df, type_name: str, out_dir: str, use_new_analysis_style=USE_NEW_ANALYSIS_STYLE):
    """Plot unpacked companion summary for MPL: (a) Geomean run time and (b) Binary size."""
    geomean_pct = compute_parallel_bench_geomean(df, values="test_results_secs", use_new_analysis_style=use_new_analysis_style)
    size_res = _extract_parallel_metric_series(df, "binary_bytes", use_new_analysis_style=use_new_analysis_style)
    if (geomean_pct is None or geomean_pct.empty) and size_res is None:
        return

    size_df, size_geomean = size_res if size_res is not None else (pd.DataFrame(), np.nan)
    benches = sorted(size_df.index) if not size_df.empty else []
    n_b = len(benches)

    with plt.rc_context(THESIS_RC):
        if n_b <= 14:
            # Side-by-side 1x2 layout for compact benchmark sets (AoS, SoA: n=11)
            fig_h = max(2.35, 0.78 + 0.145 * n_b)
            fig, (ax_geo, ax_sz) = plt.subplots(1, 2, figsize=(THESIS_TEXTWIDTH_IN, fig_h), layout="constrained")

            # (a) Geomean line chart
            unique_procs = sorted(geomean_pct.index)
            ax_geo.plot(
                geomean_pct.index,
                geomean_pct.to_numpy(dtype=float),
                color="black",
                marker="D",
                linewidth=1.8,
                markersize=4.5,
                zorder=6,
            )
            ax_geo.axhline(0, color="0.4", linestyle="--", linewidth=0.7, zorder=2)
            if len(unique_procs) > 2 and all(p > 0 for p in unique_procs) and max(unique_procs) / min(unique_procs) >= 8:
                ax_geo.set_xscale("log", base=2)
            ax_geo.set_xticks(unique_procs)
            ax_geo.get_xaxis().set_major_formatter(ticker.ScalarFormatter())
            ax_geo.tick_params(axis="x", labelsize=7.2)
            ax_geo.yaxis.set_major_formatter(ticker.PercentFormatter())
            ax_geo.set_xlabel("Core count", fontsize=8.2)
            ax_geo.set_ylabel(r"Runtime change (\%)", fontsize=8.2)
            ax_geo.set_title(r"\textsf{\textbf{(a)} Geomean run time}", fontsize=9.0, pad=5)
            ax_geo.grid(True, linestyle=":", alpha=0.55)

            # (b) Horizontal binary size bars
            y_pos = np.arange(n_b)
            vals = np.array([size_df.loc[b, "relative_pct"] for b in benches], dtype=float)
            xlim_lo, xlim_hi = draw_clipped_hbar_panel(ax_sz, y_pos, vals, color="tab:blue")
            ax_sz.axvline(0, color="0.35", linestyle="--", linewidth=0.7, zorder=2)
            ax_sz.grid(True, axis="x", linestyle=":", alpha=0.55, zorder=0)
            ax_sz.set_yticks(y_pos)
            ax_sz.set_yticklabels([latex_bench_label(b) for b in benches], fontsize=7.4)
            ax_sz.invert_yaxis()
            ax_sz.set_ylim(n_b - 0.4, -0.6)
            ax_sz.xaxis.set_major_formatter(ticker.PercentFormatter(decimals=1 if (xlim_hi - xlim_lo) < 5 else 0))
            ax_sz.xaxis.set_major_locator(ticker.MaxNLocator(nbins=4))
            ax_sz.set_xlabel(r"Size change (\%)", fontsize=8.2)
            ax_sz.set_title(r"\textsf{\textbf{(b)} Binary size}", fontsize=9.0, pad=5)
            corner, xlim_lo, xlim_hi = find_best_badge_corner(vals, vals, vals, xlim_lo, xlim_hi, min_clear_frac=0.42)
            ax_sz.set_xlim(xlim_lo, xlim_hi)
            place_geomean_badge(ax_sz, size_geomean, corner=corner, fontsize=6.8)
        else:
            # Stacked 2x1 layout for larger suites (Tuple n=21, ConApp n=34) so every benchmark label has room
            fig, (ax_geo, ax_sz) = plt.subplots(
                2, 1, figsize=(THESIS_TEXTWIDTH_IN, 4.35), gridspec_kw={"height_ratios": [1.0, 1.25]}, layout="constrained"
            )
            unique_procs = sorted(geomean_pct.index)
            ax_geo.plot(
                geomean_pct.index,
                geomean_pct.to_numpy(dtype=float),
                color="black",
                marker="D",
                linewidth=1.8,
                markersize=4.5,
                zorder=6,
            )
            ax_geo.axhline(0, color="0.4", linestyle="--", linewidth=0.7, zorder=2)
            if len(unique_procs) > 2 and all(p > 0 for p in unique_procs) and max(unique_procs) / min(unique_procs) >= 8:
                ax_geo.set_xscale("log", base=2)
            ax_geo.set_xticks(unique_procs)
            ax_geo.get_xaxis().set_major_formatter(ticker.ScalarFormatter())
            ax_geo.yaxis.set_major_formatter(ticker.PercentFormatter())
            ax_geo.set_xlabel("Core count", fontsize=8.2)
            ax_geo.set_ylabel(r"Runtime change (\%)", fontsize=8.2)
            ax_geo.set_title(r"\textsf{\textbf{(a)} Geomean run time}", fontsize=9.0, pad=4)
            ax_geo.grid(True, linestyle=":", alpha=0.55)

            x_pos = np.arange(n_b)
            vals = np.array([size_df.loc[b, "relative_pct"] for b in benches], dtype=float)
            ax_sz.bar(x_pos, vals, width=0.68, color="tab:blue", edgecolor="black", linewidth=0.35, alpha=0.88, zorder=3)
            ax_sz.axhline(0, color="0.35", linestyle="--", linewidth=0.7, zorder=2)
            ax_sz.grid(True, axis="y", linestyle=":", alpha=0.55, zorder=0)
            ax_sz.set_xticks(x_pos)
            ax_sz.set_xticklabels([latex_bench_label(b) for b in benches], rotation=90, fontsize=7.0 if n_b > 25 else 7.4)
            ax_sz.set_xlim(-0.7, n_b - 0.3)
            ax_sz.yaxis.set_major_formatter(ticker.PercentFormatter(decimals=0 if (np.ptp(vals) >= 10) else 1))
            ax_sz.set_ylabel(r"Size change (\%)", fontsize=8.2)
            ax_sz.set_title(r"\textsf{\textbf{(b)} Binary size}", fontsize=9.0, pad=4)
            # Place geomean badge on upper left or upper right away from tallest bars
            left_max = float(np.max(vals[: max(1, n_b // 4)]))
            right_max = float(np.max(vals[-max(1, n_b // 4) :]))
            badge_corner = "upper left" if left_max < right_max else "upper right"
            place_geomean_badge(ax_sz, size_geomean, corner=badge_corner, fontsize=7.0)

        _save_pdf(fig, out_dir, f"{type_name}_parallel_bench_mpl_summary")


def _extract_drilldown_data(df, bench_name: str, abbrevs=None):
    filtered = df.copy()
    if bench_name is not None:
        if bench_name in filtered["bench"].values:
            filtered = filtered[filtered["bench"] == bench_name]
        elif bench_name == "delunay" and "delaunay" in filtered["bench"].values:
            filtered = filtered[filtered["bench"] == "delaunay"]
        else:
            matches = [
                b for b in filtered["bench"].dropna().unique()
                if b.lower() == bench_name.lower() or b.replace("-", "_") == bench_name.replace("-", "_")
            ]
            filtered = filtered[filtered["bench"] == (matches[0] if matches else bench_name)]
    if filtered.empty:
        return None
    filtered = filtered[filtered.groupby("bench")[CHECKSUM_FIELD_PARALLEL].transform("nunique") > 1]
    if filtered.empty:
        return None
    base_key, test_key = infer_configs(filtered, abbrevs)
    filtered = filtered[filtered[COMPILER_NAME_FIELD_PARALLEL].isin([base_key, test_key])]
    if "procs" in filtered.columns:
        filtered = filtered.drop_duplicates(subset=["bench", "procs", COMPILER_NAME_FIELD_PARALLEL], keep="last")
        procs = sorted(int(p) for p in filtered["procs"].unique())
    else:
        filtered = filtered.drop_duplicates(subset=["bench", COMPILER_NAME_FIELD_PARALLEL], keep="last")
        procs = [1]
    bench_display = filtered["bench"].iloc[0]
    return filtered, procs, base_key, test_key, bench_display


def _plot_scatter_on_ax(ax, proc_df, base_key: str, test_key: str, marker_size=18):
    base_row = proc_df[proc_df[COMPILER_NAME_FIELD_PARALLEL] == base_key]
    test_row = proc_df[proc_df[COMPILER_NAME_FIELD_PARALLEL] == test_key]

    base_lbl = latex_escape_text(base_key)
    test_lbl = latex_escape_text(test_key)

    if not base_row.empty:
        warmup = base_row.iloc[0].get("warmup_result_secs", [])
        if warmup is not None and len(warmup) > 0:
            ax.scatter(range(len(warmup)), warmup, color="tab:blue", marker="x", label=f"{base_lbl} (warmup)", alpha=0.85, s=marker_size, linewidths=0.9)
        test_res = base_row.iloc[0].get("test_results_secs", base_row.iloc[0].get("test_result_secs", []))
        if test_res is not None and len(test_res) > 0:
            ax.scatter(range(len(test_res)), test_res, color="tab:blue", marker="o", label=f"{base_lbl} (test)", alpha=0.85, s=marker_size * 0.85)

    if not test_row.empty:
        warmup = test_row.iloc[0].get("warmup_result_secs", [])
        if warmup is not None and len(warmup) > 0:
            ax.scatter(range(len(warmup)), warmup, color="tab:orange", marker="x", label=f"{test_lbl} (warmup)", alpha=0.85, s=marker_size, linewidths=0.9)
        test_res = test_row.iloc[0].get("test_results_secs", test_row.iloc[0].get("test_result_secs", []))
        if test_res is not None and len(test_res) > 0:
            ax.scatter(range(len(test_res)), test_res, color="tab:orange", marker="o", label=f"{test_lbl} (test)", alpha=0.85, s=marker_size * 0.85)


def plot_thesis_trial_scatter(df, bench_name: str, out_filename: str, out_dir: str, show_legend=True):
    """Plot full-width trial scatter: 1 panel for MLton, or 2x5 wrapped grid for 10-core MPL."""
    extracted = _extract_drilldown_data(df, bench_name)
    if extracted is None:
        return
    filtered, procs, base_key, test_key, _ = extracted
    n_procs = len(procs)

    with plt.rc_context(THESIS_RC):
        if n_procs == 1:
            fig, ax = plt.subplots(1, 1, figsize=(THESIS_TEXTWIDTH_IN, 2.15), layout="constrained")
            _plot_scatter_on_ax(ax, filtered, base_key, test_key, marker_size=20)
            ax.set_xlabel("Trial", fontsize=8.2)
            ax.set_ylabel("Time (s)", fontsize=8.2)
            ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
            ax.grid(True, linestyle=":", alpha=0.55)
            handles, labels = ax.get_legend_handles_labels()
            if handles and show_legend:
                fig.legend(handles, labels, loc="outside upper center", ncol=min(4, len(labels)), fontsize=7.3, frameon=True)
        else:
            ncols = min(5, n_procs)
            nrows = int(np.ceil(n_procs / ncols))
            fig_h = (1.35 * nrows + 0.48) if show_legend else (1.35 * nrows + 0.18)
            fig, axes = plt.subplots(nrows, ncols, figsize=(THESIS_TEXTWIDTH_IN, fig_h), sharey=False, layout="constrained")
            axes_flat = np.atleast_1d(axes).flatten()

            for idx, proc in enumerate(procs):
                ax = axes_flat[idx]
                proc_df = filtered[filtered["procs"] == proc]
                _plot_scatter_on_ax(ax, proc_df, base_key, test_key, marker_size=11)
                core_word = "core" if proc == 1 else "cores"
                ax.set_title(f"{proc} {core_word}", fontsize=7.8, pad=2.5)
                ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=3, integer=True))
                ax.yaxis.set_major_locator(ticker.MaxNLocator(nbins=4))
                ax.tick_params(axis="both", labelsize=6.6, length=2.5, pad=1.5)
                ax.grid(True, linestyle=":", alpha=0.5)
                if idx // ncols == nrows - 1 or idx + ncols >= n_procs:
                    ax.set_xlabel("Trial", fontsize=7.5)
                if idx % ncols == 0:
                    ax.set_ylabel("Time (s)", fontsize=7.5)

            for j in range(n_procs, len(axes_flat)):
                fig.delaxes(axes_flat[j])

            handles, labels = axes_flat[0].get_legend_handles_labels()
            if handles and show_legend:
                fig.legend(handles, labels, loc="outside upper center", ncol=min(4, len(labels)), fontsize=7.3, frameon=True)

        _save_pdf(fig, out_dir, out_filename)


def plot_example_scatter_pair(config: dict, out_dir: str):
    """Plot Figure 5.1 (delunay + dedup) as a clean 1x2 figure at exact textwidth."""
    scatter_cfg = config.get("trial_scatter_plots", {})
    k1 = "delunay_mlton_parallel_ml_bench_scatter"
    k2 = "dedup_mlton_parallel_ml_bench_scatter"
    if k1 not in scatter_cfg or k2 not in scatter_cfg:
        return

    s1 = scatter_cfg[k1]
    s2 = scatter_cfg[k2]
    e1 = _extract_drilldown_data(load_df(s1["source"]), s1["benchmark"])
    e2 = _extract_drilldown_data(load_df(s2["source"]), s2["benchmark"])
    if e1 is None or e2 is None:
        return

    with plt.rc_context(THESIS_RC):
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(THESIS_TEXTWIDTH_IN, 2.35), layout="constrained")
        for ax, ext, header in [
            (ax1, e1, r"\textsf{\textbf{(a)} }\texttt{delaunay}"),
            (ax2, e2, r"\textsf{\textbf{(b)} }\texttt{dedup}"),
        ]:
            filt, _, base_k, test_k, _ = ext
            _plot_scatter_on_ax(ax, filt, base_k, test_k, marker_size=16)
            y_lo, y_hi = ax.get_ylim()
            ax.set_ylim(y_lo, y_hi + 0.24 * (y_hi - y_lo))
            ax.set_title(header, fontsize=9.0, pad=4)
            ax.set_xlabel("Trial", fontsize=8.0)
            ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
            ax.grid(True, linestyle=":", alpha=0.55)
            handles, labels = ax.get_legend_handles_labels()
            if handles:
                ax.legend(handles, labels, loc="upper center", ncol=2, fontsize=6.2, framealpha=0.92, handletextpad=0.3, columnspacing=0.6)

        ax1.set_ylabel("Time (s)", fontsize=8.2)
        _save_pdf(fig, out_dir, "example_scatter_trials_shared")


def _compute_compare_series_items(series_specs, series_type: str, config: dict, values="test_results_secs", use_new_analysis_style=USE_NEW_ANALYSIS_STYLE):
    computed = []
    for item in series_specs:
        if not isinstance(item, dict):
            continue
        series_name = item.get("series_name", "")
        if "df" in item:
            df = item["df"]
        elif "series_path" in item:
            df = load_df(resolve_series_path(config, item["series_path"]))
        elif "source" in item or "data" in item or "file" in item:
            df = load_df(item.get("source") or item.get("data") or item.get("file"))
        else:
            continue

        abbrevs = item.get("abbrevs")
        val_col = item.get("values", values)
        item_stype = item.get("source_series_type") or item.get("series_type") or series_type
        if item_stype in ("geomean", "geomeans"):
            s = compute_parallel_bench_geomean(df, values=val_col, abbrevs=abbrevs, use_new_analysis_style=use_new_analysis_style)
            if s is not None and not s.empty:
                computed.append((series_name, s))
        else:
            # Use deterministic random_state via compute_parallel_bench_benchmark
            b_df = compute_parallel_bench_benchmark(df, bench_name=item_stype, values=val_col, abbrevs=abbrevs, use_new_analysis_style=use_new_analysis_style)
            if b_df is not None and not b_df.empty:
                computed.append((series_name, b_df))
    return computed


def _draw_compare_series_ax(ax, computed_series, use_new_analysis_style=USE_NEW_ANALYSIS_STYLE):
    markers = ["o", "s", "^", "v", "D", "p", "h", "*", "X", "<", ">"]
    colors = plt.rcParams["axes.prop_cycle"].by_key().get("color", ["tab:blue", "tab:orange", "tab:green"])

    all_procs_set = set()
    raw_lo = -1.0
    raw_hi = 1.0
    max_point_hi = 1.0
    min_point_lo = -1.0
    series_records = []

    for i, (name, s) in enumerate(computed_series):
        color = colors[i % len(colors)]
        marker = markers[i % len(markers)]
        lbl = latex_escape_text(name)
        if isinstance(s, pd.Series):
            procs = np.asarray(s.index, dtype=int)
            vals = s.to_numpy(dtype=float)
            los = vals.copy()
            his = vals.copy()
            has_err = False
        else:
            s_sorted = s.sort_values("procs")
            procs = s_sorted["procs"].to_numpy(dtype=int)
            vals = s_sorted["relative_pct"].to_numpy(dtype=float)
            if use_new_analysis_style and "err_minus_pct" in s_sorted.columns:
                em = s_sorted["err_minus_pct"].to_numpy(dtype=float)
                ep = s_sorted["err_plus_pct"].to_numpy(dtype=float)
                los = vals - em
                his = vals + ep
                has_err = True
            elif "std_pct" in s_sorted.columns:
                st = s_sorted["std_pct"].to_numpy(dtype=float)
                los = vals - st
                his = vals + st
                has_err = True
            else:
                los = vals.copy()
                his = vals.copy()
                has_err = False

        all_procs_set.update(procs.tolist())
        raw_lo = min(raw_lo, float(np.nanmin(los)))
        raw_hi = max(raw_hi, float(np.nanmax(his)))
        min_point_lo = min(min_point_lo, float(np.nanmin(vals)))
        max_point_hi = max(max_point_hi, float(np.nanmax(vals)))
        series_records.append({
            "procs": procs,
            "vals": vals,
            "los": los,
            "his": his,
            "has_err": has_err,
            "color": color,
            "marker": marker,
            "label": lbl,
            "name": name,
        })

    # Clip runaway upper/lower CI whiskers if they exceed 2x the point range and > 70%
    raw_span = max(1e-6, raw_hi - raw_lo)
    ylim_hi = raw_hi + 0.07 * raw_span
    ylim_lo = raw_lo - 0.07 * raw_span
    if raw_hi > 75.0 and raw_hi > 1.75 * max(max_point_hi, 25.0):
        cand_hi = _nice_bound(max(max_point_hi * 1.18, 65.0), "up")
        if (raw_hi - cand_hi) >= 0.25 * raw_span:
            ylim_hi = cand_hi
    if raw_lo < -75.0 and abs(raw_lo) > 1.75 * max(abs(min_point_lo), 25.0):
        cand_lo = _nice_bound(min(min_point_lo * 1.18, -65.0), "down")
        if (cand_lo - raw_lo) >= 0.25 * raw_span:
            ylim_lo = cand_lo

    for sr in series_records:
        procs = sr["procs"]
        vals = sr["vals"]
        los = sr["los"]
        his = sr["his"]
        if sr["has_err"]:
            ax.plot(procs, vals, color=sr["color"], linewidth=1.4, alpha=0.9, zorder=5)
            in_m = (vals >= ylim_lo) & (vals <= ylim_hi)
            if np.any(in_m):
                v_in = vals[in_m]
                lo_in = los[in_m]
                hi_in = his[in_m]
                em_c = np.where(lo_in >= ylim_lo, v_in - lo_in, 0.0)
                ep_c = np.where(hi_in <= ylim_hi, hi_in - v_in, 0.0)
                ax.errorbar(
                    procs[in_m],
                    v_in,
                    yerr=[em_c, ep_c],
                    label=sr["label"],
                    fmt=sr["marker"],
                    color=sr["color"],
                    capsize=2.3,
                    capthick=0.8,
                    elinewidth=0.85,
                    markersize=4.0,
                    alpha=0.9,
                    zorder=6,
                )
            else:
                ax.plot([], [], marker=sr["marker"], color=sr["color"], label=sr["label"])
        else:
            ax.plot(procs, vals, label=sr["label"], color=sr["color"], marker=sr["marker"], linewidth=1.7, markersize=4.5, alpha=0.92, zorder=6)

    ax.axhline(0, color="0.4", linestyle="--", linewidth=0.7, zorder=2)
    all_procs = sorted(all_procs_set)
    if len(all_procs) > 2 and all(p > 0 for p in all_procs) and max(all_procs) / min(all_procs) >= 8:
        ax.set_xscale("log", base=2)
    ax.set_xticks(all_procs)
    ax.get_xaxis().set_major_formatter(ticker.ScalarFormatter())
    ax.set_ylim(ylim_lo, ylim_hi)
    ax.yaxis.set_major_formatter(ticker.PercentFormatter(decimals=1 if (ylim_hi - ylim_lo) < 6 else 0))
    ax.set_xlabel("Core count", fontsize=8.0)
    ax.grid(True, linestyle=":", alpha=0.55)

    annotate_clipped_line_panel(ax, series_records, ylim_lo, ylim_hi, fontsize=6.4)


def plot_thesis_compare_series_single(series_specs, series_type: str, config: dict, out_filename: str, out_dir: str, use_new_analysis_style=USE_NEW_ANALYSIS_STYLE):
    computed = _compute_compare_series_items(series_specs, series_type, config, use_new_analysis_style=use_new_analysis_style)
    if not computed:
        return
    with plt.rc_context(THESIS_RC):
        fig, ax = plt.subplots(1, 1, figsize=(THESIS_TEXTWIDTH_IN, 2.30), layout="constrained")
        _draw_compare_series_ax(ax, computed, use_new_analysis_style=use_new_analysis_style)
        ax.set_ylabel(r"Runtime change (\%)", fontsize=8.2)
        ax.legend(loc="best", fontsize=7.5, framealpha=0.92)
        _save_pdf(fig, out_dir, out_filename)


def plot_thesis_compare_series_group(panel_specs, config: dict, out_filename: str, out_dir: str, use_new_analysis_style=USE_NEW_ANALYSIS_STYLE):
    """Plot 1x2 or 1x3 compare_series panels with a single shared top legend and shared left y-label."""
    compare_dict = config.get("compare_series") or config.get("compare_geomeans") or {}
    loaded_panels = []
    for key, panel_title in panel_specs:
        if key not in compare_dict:
            return
        spec = compare_dict[key]
        stype = spec.get("source_series_type") or spec.get("series_type") or "geomeans"
        slist = spec.get("source_series") or spec.get("series") or []
        comp = _compute_compare_series_items(slist, stype, config, use_new_analysis_style=use_new_analysis_style)
        if not comp:
            return
        loaded_panels.append((panel_title, comp))

    n_p = len(loaded_panels)
    with plt.rc_context(THESIS_RC):
        fig, axes = plt.subplots(1, n_p, figsize=(THESIS_TEXTWIDTH_IN, 2.45 if n_p == 2 else 2.38), layout="constrained")
        axes = np.atleast_1d(axes)
        for idx, (p_title, comp) in enumerate(loaded_panels):
            ax = axes[idx]
            _draw_compare_series_ax(ax, comp, use_new_analysis_style=use_new_analysis_style)
            ax.set_title(p_title, fontsize=9.0, pad=4)
            ax.tick_params(axis="x", labelsize=6.8 if n_p >= 3 else 7.3, rotation=35 if n_p >= 3 else 0)
            ax.tick_params(axis="y", labelsize=7.2)

        axes[0].set_ylabel(r"Runtime change (\%)", fontsize=8.2)
        handles, labels = axes[0].get_legend_handles_labels()
        if handles:
            ncol = min(len(labels), 3 if sum(len(l) for l in labels) < 95 else 2)
            fig.legend(handles, labels, loc="outside upper center", ncol=ncol, fontsize=7.3, frameon=True)

        _save_pdf(fig, out_dir, out_filename)


def plot_thesis_compare_bars(series_specs, config: dict, values: str, out_filename: str, out_dir: str, suite=None, use_new_analysis_style=USE_NEW_ANALYSIS_STYLE):
    """Plot horizontal grouped bar chart at exact textwidth with top legend and outlier clipping."""
    computed_series = []
    for item in series_specs:
        if not isinstance(item, dict):
            continue
        s_name, res_df, geomean_pct = compute_bar_series(
            item, config=config, values=values, suite=suite, use_new_analysis_style=use_new_analysis_style
        )
        if res_df is not None and not res_df.empty:
            computed_series.append((s_name, res_df, geomean_pct))

    if not computed_series:
        return

    all_benches = sorted({b for _, df_r, _ in computed_series for b in df_r["bench"]})
    n_b = len(all_benches)
    n_m = len(computed_series)
    if n_b == 0:
        return

    fig_h = max(2.65, 0.98 + 0.168 * n_b)
    group_height = 0.78
    bar_h = group_height / n_m
    colors = plt.cm.tab10.colors

    # Collect all bounds first to compute shared panel xlim
    all_vals, all_los, all_his = [], [], []
    for _, res_df, _ in computed_series:
        v = res_df["relative_pct"].to_numpy(dtype=float)
        em = res_df["err_minus_pct"].to_numpy(dtype=float) if "err_minus_pct" in res_df.columns else np.zeros(len(v))
        ep = res_df["err_plus_pct"].to_numpy(dtype=float) if "err_plus_pct" in res_df.columns else np.zeros(len(v))
        all_vals.extend(v)
        all_los.extend(v - em)
        all_his.extend(v + ep)

    xlim = compute_bar_clip_bounds(all_vals, all_los, all_his)

    with plt.rc_context(THESIS_RC):
        fig, ax = plt.subplots(1, 1, figsize=(THESIS_TEXTWIDTH_IN, fig_h), layout="constrained")
        base_y = np.arange(n_b, dtype=float)

        for i, (name, res_df, geomean_pct) in enumerate(computed_series):
            df_map = res_df.set_index("bench")
            y_coords = base_y + (i - (n_m - 1) / 2.0) * bar_h
            vals = np.array([df_map.loc[b, "relative_pct"] if b in df_map.index else np.nan for b in all_benches], dtype=float)
            has_err = use_new_analysis_style and "err_minus_pct" in df_map.columns and (
                (df_map["err_minus_pct"] > 0).any() or (df_map["err_plus_pct"] > 0).any()
            )
            em = np.array([df_map.loc[b, "err_minus_pct"] if (has_err and b in df_map.index) else 0.0 for b in all_benches], dtype=float)
            ep = np.array([df_map.loc[b, "err_plus_pct"] if (has_err and b in df_map.index) else 0.0 for b in all_benches], dtype=float)

            lbl = latex_escape_text(name)
            if pd.notna(geomean_pct):
                lbl = fr"{lbl} (geomean: {geomean_pct:+.1f}\%)"

            draw_clipped_hbar_panel(
                ax,
                y_coords,
                vals,
                err_minus=em if has_err else None,
                err_plus=ep if has_err else None,
                bar_height=bar_h * 0.94,
                color=colors[i % len(colors)],
                label=lbl,
                xlim=xlim,
                annotate_fontsize=6.4,
            )

        ax.axvline(0, color="0.35", linestyle="--", linewidth=0.7, zorder=2)
        ax.grid(True, axis="x", linestyle=":", alpha=0.55, zorder=0)
        ax.set_yticks(base_y)
        ax.set_yticklabels([latex_bench_label(b) for b in all_benches], fontsize=7.8)
        ax.invert_yaxis()
        ax.set_ylim(n_b - 0.4, -0.6)
        ax.xaxis.set_major_formatter(ticker.PercentFormatter(decimals=0 if (xlim[1] - xlim[0]) >= 12 else 1))
        ax.set_xlabel(r"Runtime change (\%)", fontsize=8.2)

        handles, labels = ax.get_legend_handles_labels()
        if handles:
            ncol = 1 if any(len(l) > 42 for l in labels) else min(2, len(labels))
            fig.legend(handles, labels, loc="outside upper center", ncol=ncol, fontsize=7.4, frameon=True)

        _save_pdf(fig, out_dir, out_filename)


def process_thesis_config(config: dict, thesis_out_dir: str = None, use_new_analysis_style=USE_NEW_ANALYSIS_STYLE):
    """Build all thesis-formatted charts into `<output_directory>/thesis/`."""
    base_out = config["output_directory"]
    out_dir = thesis_out_dir or os.path.join(base_out, "thesis")
    os.makedirs(out_dir, exist_ok=True)

    # 1. Benchmark suite sections
    for section_key, section_val in config.items():
        if section_key in ("output_directory", "trial_scatter_plots", "compare_geomeans", "compare_series", "compare_bar_charts", "compare_bars"):
            continue
        if not isinstance(section_val, dict):
            continue

        suite = section_val.get("suite", "mlton")
        compiler = section_val.get("compiler", "mlton")

        for type_name, data_file in section_val.items():
            if type_name in METADATA_KEYS:
                continue
            df = load_df(data_file)
            if suite == "mlton":
                plot_mlton_shared(df, type_name, out_dir=out_dir, use_new_analysis_style=use_new_analysis_style)
            elif suite == "parallel_bench" and compiler == "mlton":
                plot_parallel_bench_mlton_shared(df, type_name, out_dir=out_dir, use_new_analysis_style=use_new_analysis_style)
            elif suite == "parallel_bench" and compiler == "mpl":
                plot_thesis_trellis(df, type_name, out_dir=out_dir, use_new_analysis_style=use_new_analysis_style)
                plot_thesis_mpl_summary(df, type_name, out_dir=out_dir, use_new_analysis_style=use_new_analysis_style)

    # 2. Trial scatter plots
    scatter_cfg = config.get("trial_scatter_plots")
    if isinstance(scatter_cfg, dict):
        for plot_key, plot_spec in scatter_cfg.items():
            if not isinstance(plot_spec, dict):
                continue
            source_file = plot_spec.get("source") or plot_spec.get("data")
            bench_name = plot_spec.get("benchmark") or plot_spec.get("bench")
            if not source_file:
                continue
            df = load_df(source_file)
            # In Fig 5.20, quickhull (top) carries the shared legend; linearrec (bottom) omits duplicate legend
            plot_thesis_trial_scatter(df, bench_name=bench_name, out_filename=plot_key, out_dir=out_dir, show_legend=True)
            if plot_key == "linearrec_default_aos_mpl_parallel_ml_bench_scatter":
                plot_thesis_trial_scatter(
                    df,
                    bench_name=bench_name,
                    out_filename=f"{plot_key}_nolegend",
                    out_dir=out_dir,
                    show_legend=False,
                )
        plot_example_scatter_pair(config, out_dir=out_dir)

    # 3. Compare series (both standalone and multi-panel thesis groups)
    compare_dict = config.get("compare_series") or config.get("compare_geomeans")
    if isinstance(compare_dict, dict):
        for name, spec in compare_dict.items():
            if isinstance(spec, dict):
                stype = spec.get("source_series_type") or spec.get("series_type") or spec.get("type", "geomeans")
                slist = spec.get("source_series") or spec.get("series") or []
            elif isinstance(spec, list):
                stype = "geomeans"
                slist = spec
            else:
                continue
            plot_thesis_compare_series_single(
                slist, stype, config, out_filename=name, out_dir=out_dir, use_new_analysis_style=use_new_analysis_style
            )

        group_defs = [
            (
                "tuple_standouts_only",
                [
                    ("tuple_exp_bfs", r"\textsf{\textbf{(a)} }\texttt{bfs}"),
                    ("tuple_exp_delaunay", r"\textsf{\textbf{(b)} }\texttt{delaunay}"),
                ],
            ),
            (
                "con_chunkify_one_outliers",
                [
                    ("con_exp_suffix_array", r"\textsf{\textbf{(a)} }\texttt{suffix-array}"),
                    ("con_exp_linearrec", r"\textsf{\textbf{(b)} }\texttt{linearrec}"),
                ],
            ),
            (
                "aos_fixed_iters_focus",
                [
                    ("aos_fixed_iters_geomean", r"\textsf{\textbf{(a)} Geometric mean}"),
                    ("aos_fixed_iters_quickhull", r"\textsf{\textbf{(b)} }\texttt{quickhull}"),
                    ("aos_fixed_iters_linearrec", r"\textsf{\textbf{(c)} }\texttt{linearrec}"),
                ],
            ),
            (
                "aos_sync_gc_focus",
                [
                    ("aos_sync_gc_geomean", r"\textsf{\textbf{(a)} Geometric mean}"),
                    ("aos_sync_gc_quickhull", r"\textsf{\textbf{(b)} }\texttt{quickhull}"),
                    ("aos_sync_gc_linearrec", r"\textsf{\textbf{(c)} }\texttt{linearrec}"),
                ],
            ),
            (
                "aos_chunkify_one_focus",
                [
                    ("aos_chunkify_one_geomean", r"\textsf{\textbf{(a)} Geometric mean}"),
                    ("aos_chunkify_one_quickhull", r"\textsf{\textbf{(b)} }\texttt{quickhull}"),
                    ("aos_chunkify_one_linearrec", r"\textsf{\textbf{(c)} }\texttt{linearrec}"),
                ],
            ),
        ]
        for group_name, panel_specs in group_defs:
            plot_thesis_compare_series_group(
                panel_specs, config, out_filename=group_name, out_dir=out_dir, use_new_analysis_style=use_new_analysis_style
            )

    # 4. Compare bar charts
    compare_bars = config.get("compare_bar_charts") or config.get("compare_bars")
    if isinstance(compare_bars, dict):
        for name, spec in compare_bars.items():
            if isinstance(spec, dict):
                suite = spec.get("suite")
                slist = spec.get("source_series") or spec.get("series") or []
                val_col = spec.get("values") or ("runTime" if suite == "mlton" else "test_results_secs")
            elif isinstance(spec, list):
                suite = None
                slist = spec
                val_col = "test_results_secs"
            else:
                continue
            plot_thesis_compare_bars(
                slist, config=config, values=val_col, out_filename=name, out_dir=out_dir, suite=suite, use_new_analysis_style=use_new_analysis_style
            )


def main():
    parser = argparse.ArgumentParser(description="Build thesis-formatted charts into <output_directory>/thesis/.")
    parser.add_argument("--config", required=True, help="Path to the JSON configuration file.")
    parser.add_argument("--out-dir", default=None, help="Optional override directory for thesis charts.")
    parser.add_argument(
        "--use-new-analysis-style",
        dest="use_new_analysis_style",
        action="store_true",
        default=USE_NEW_ANALYSIS_STYLE,
    )
    parser.add_argument(
        "--use-old-analysis-style",
        dest="use_new_analysis_style",
        action="store_false",
    )
    args = parser.parse_args()

    if not os.path.exists(args.config):
        print(f"Error: Config file not found: {args.config}", file=sys.stderr)
        sys.exit(1)

    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)

    process_thesis_config(config, thesis_out_dir=args.out_dir, use_new_analysis_style=args.use_new_analysis_style)


if __name__ == "__main__":
    main()
