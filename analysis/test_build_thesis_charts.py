import json
import numpy as np
import pandas as pd

from build_thesis_charts import (
    THESIS_TEXTWIDTH_IN,
    compute_bar_clip_bounds,
    compute_trellis_ylim,
    latex_escape_text,
    plot_mlton_shared,
    plot_parallel_bench_mlton_shared,
    plot_thesis_mpl_summary,
    plot_thesis_trellis,
    plot_thesis_trial_scatter,
    process_thesis_config,
)


def test_latex_escape_text():
    assert r"\texttt{-chunkify one}" in latex_escape_text("Con-vs-con, with `-chunkify one`")
    assert "baseline" in latex_escape_text("Tuple-vs-tuple, with basline fixup")


def test_compute_bar_clip_bounds_outlier_and_eff_span():
    # Mirrors Fig. 5.9c: 22 benchmarks within [-1.8%, +9.0%] and one outlier at +565.2%
    vals = np.array([-1.8, -0.5, 0.2, 1.1, 2.4, 4.5, 5.4, 9.0, 565.2])
    xlim_lo, xlim_hi = compute_bar_clip_bounds(vals, vals, vals)
    assert xlim_hi <= 16.0
    # Left padding must be proportional to clipped span, NOT raw 567% span
    assert xlim_lo >= -4.0


def test_compute_trellis_ylim_clips_runaway_ci():
    rows = []
    for i in range(10):
        for p in [1, 4, 16, 64, 160]:
            rows.append({
                "bench": f"b{i}",
                "procs": p,
                "relative_pct": -5.0 + i,
                "err_minus_pct": 3.0,
                "err_plus_pct": 3.0,
            })
    # Add one outlier benchmark with +209% upper CI and -60% lower CI at 160c
    rows.append({
        "bench": "linearrec",
        "procs": 160,
        "relative_pct": 59.0,
        "err_minus_pct": 119.0,
        "err_plus_pct": 150.0,
    })
    df = pd.DataFrame(rows)
    ylo, yhi = compute_trellis_ylim(df, use_new_analysis_style=True)
    assert yhi < 40.0
    assert ylo > -40.0


def test_mlton_and_parallel_shared_charts(tmp_path):
    mlton_df = pd.DataFrame({
        "bench": ["b1", "b1", "b2", "b2", "b3", "b3", "b4", "b4", "b5", "b5"],
        "compilerAbbrev": ["MLton0", "MLton1"] * 5,
        "runTime": [10.0, 9.5, 10.0, 10.2, 10.0, 9.8, 10.0, 10.1, 10.0, 9.9],
        "compileTime": [5.0, 5.1, 5.0, 5.2, 5.0, 5.0, 5.0, 5.1, 5.0, 15.0],
        "binarySize": [100, 102, 100, 101, 100, 100, 100, 103, 100, 650],
        "binaryChecksum": ["h0", "h1"] * 5,
    })
    plot_mlton_shared(mlton_df, "con", out_dir=str(tmp_path))
    assert (tmp_path / "con_mlton_shared.pdf").exists()
    assert (tmp_path / "con_mlton_shared.pdf").stat().st_size > 0

    par_df = pd.DataFrame({
        "bench": ["p1", "p1", "p2", "p2"],
        "procs": [1, 1, 1, 1],
        "config": ["mlton-baseline", "mlton-opt", "mlton-baseline", "mlton-opt"],
        "test_results_secs": [[1.0, 1.1], [0.9, 0.95], [2.0, 2.1], [2.2, 2.3]],
        "binary_bytes": [1000, 1020, 2000, 1980],
        "binary_md5": ["m0", "m1", "m2", "m3"],
    })
    plot_parallel_bench_mlton_shared(par_df, "tuple", out_dir=str(tmp_path))
    assert (tmp_path / "tuple_parallel_bench_mlton_shared.pdf").exists()


def test_mpl_trellis_summary_and_scatter(tmp_path):
    rows = []
    for b in ["bfs", "delaunay", "quickhull"]:
        for p in [1, 2, 4, 8, 16, 32]:
            rows.append({
                "bench": b,
                "procs": p,
                "config": "mpl-baseline",
                "warmup_result_secs": [1.1, 1.0],
                "test_results_secs": [1.0, 1.02, 0.99],
                "binary_bytes": 10000,
                "binary_md5": f"{b}_base",
            })
            rows.append({
                "bench": b,
                "procs": p,
                "config": "mpl-aos",
                "warmup_result_secs": [0.9, 0.85],
                "test_results_secs": [0.8, 0.82, 0.79],
                "binary_bytes": 9950,
                "binary_md5": f"{b}_aos",
            })
    df = pd.DataFrame(rows)
    plot_thesis_trellis(df, "aos", out_dir=str(tmp_path))
    plot_thesis_mpl_summary(df, "aos", out_dir=str(tmp_path))
    plot_thesis_trial_scatter(df, "quickhull", "quickhull_scatter", out_dir=str(tmp_path))

    assert (tmp_path / "aos_parallel_bench_run_mpl_vs_mpl_trellis.pdf").exists()
    assert (tmp_path / "aos_parallel_bench_mpl_summary.pdf").exists()
    assert (tmp_path / "quickhull_scatter.pdf").exists()


def test_process_thesis_config_isolates_subdirectory(tmp_path):
    charts_dir = tmp_path / "charts"
    charts_dir.mkdir()
    sentinel = charts_dir / "all_charts.tex"
    sentinel.write_text("UNCHANGED", encoding="utf-8")

    config = {
        "output_directory": str(charts_dir),
        "mlton_benchmarks_mlton_vs_mlton": {
            "compiler": "mlton",
            "suite": "mlton",
            "tuple": "fix_hashes4:big-mpl:99fe634ab:20260719_202336.jsonl",
        },
    }
    process_thesis_config(config)

    assert sentinel.read_text(encoding="utf-8") == "UNCHANGED"
    assert (charts_dir / "thesis" / "tuple_mlton_shared.pdf").exists()
    assert THESIS_TEXTWIDTH_IN == 6.50
