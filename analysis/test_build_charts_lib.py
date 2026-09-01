import json
import pandas as pd
import pytest
from build_charts_lib import (
    USE_NEW_ANALYSIS_STYLE,
    calculate_error_bars,
    process_config,
    generate_all_charts_tex,
    plot_mlton,
    plot_parallel_bench,
    plot_parallel_bench_cores,
    plot_parallel_bench_geomean,
    compute_parallel_bench_geomean,
    plot_compare_geomeans,
    resolve_series_path,
    plot_parallel_bench_size,
    plot_parallel_bench_trellis,
    infer_configs,
)


def test_process_config(tmp_path):
    output_dir = tmp_path / "charts"
    test_config_path = tmp_path / "test_config.json"

    config_data = {
        "output_directory": str(output_dir),
        "mlton_benchmarks_mlton_vs_mlton": {
            "tuple": "fix_hashes4:big-mpl:99fe634ab:20260719_202336.jsonl"
        }
    }

    with open(test_config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f)

    with open(test_config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    process_config(config)

    expected_files = [
        "tuple_mlton_run_mlton_vs_mlton.pdf",
        "tuple_mlton_run_mlton_vs_mlton.csv",
        "tuple_mlton_compile_mlton_vs_mlton.pdf",
        "tuple_mlton_compile_mlton_vs_mlton.csv",
        "tuple_mlton_size_mlton_vs_mlton.pdf",
        "tuple_mlton_size_mlton_vs_mlton.csv",
        "chart_info.md",
        "all_charts.tex",
    ]

    for fname in expected_files:
        output_file = output_dir / fname
        assert output_file.exists(), f"Expected chart file {fname} was not created."
        assert output_file.stat().st_size > 0, f"Chart file {fname} is empty."

    chart_info_content = (output_dir / "chart_info.md").read_text(encoding="utf-8")
    assert "Data generated at " in chart_info_content
    assert "using the following config:" in chart_info_content

    all_charts_tex_content = (output_dir / "all_charts.tex").read_text(encoding="utf-8")
    assert "fix_hashes4:big-mpl:99fe634ab:20260719_202336.jsonl" in all_charts_tex_content
    assert "tuple_mlton_run_mlton_vs_mlton.pdf" in all_charts_tex_content



def test_process_config_parallel_bench(tmp_path):
    output_dir = tmp_path / "charts_parallel"
    test_config_path = tmp_path / "test_config_parallel.json"

    config_data = {
        "output_directory": str(output_dir),
        "parallel_bench_benchmarks_mlton_vs_mlton": {
            "compiler": "mlton",
            "suite": "parallel_bench",
            "tuple": "cc_tuple_flatten_fixed_hash:260813-220330:flattening-tests:e957206262ad2a8b93398cdf777dd91275a74fbd:260813-220330.processed.jsonl",
            "con": "cc_conapp_flatten_fixed_hash:260814-000801:flattening-tests:dfcc9e1798eddbe9a3d884b806fa2a946f27000d:260814-000801.processed.jsonl"
        }
    }

    with open(test_config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f)

    with open(test_config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    process_config(config)

    expected_files = [
        "tuple_parallel_bench_run_mlton_vs_mlton.pdf",
        "tuple_parallel_bench_run_mlton_vs_mlton.csv",
        "tuple_parallel_bench_size_mlton_vs_mlton.pdf",
        "tuple_parallel_bench_size_mlton_vs_mlton.csv",
        "con_parallel_bench_run_mlton_vs_mlton.pdf",
        "con_parallel_bench_run_mlton_vs_mlton.csv",
        "con_parallel_bench_size_mlton_vs_mlton.pdf",
        "con_parallel_bench_size_mlton_vs_mlton.csv",
        "chart_info.md",
        "all_charts.tex",
    ]

    for fname in expected_files:
        output_file = output_dir / fname
        assert output_file.exists(), f"Expected chart file {fname} was not created."
        assert output_file.stat().st_size > 0, f"Chart file {fname} is empty."


def test_process_config_full(tmp_path):
    output_dir = tmp_path / "charts_full"
    test_config_path = tmp_path / "test_config_full.json"

    config_data = {
        "output_directory": str(output_dir),
        "mlton_benchmarks_mlton_vs_mlton": {
            "compiler": "mlton",
            "suite": "mlton",
            "tuple": "test_conapp_flatten_cc_icelake:flattening-tests:05e9492b9:20260725_223512.jsonl",
            "con": "test_tuple_flatten_cc_icelake:flattening-tests:41f63ec71:20260725_203206.jsonl"
        },
        "parallel_bench_benchmarks_mlton_vs_mlton": {
            "compiler": "mlton",
            "suite": "parallel_bench",
            "tuple": "cc_tuple_flatten_fixed_hash:260813-220330:flattening-tests:e957206262ad2a8b93398cdf777dd91275a74fbd:260813-220330.processed.jsonl",
            "con": "cc_conapp_flatten_fixed_hash:260814-000801:flattening-tests:dfcc9e1798eddbe9a3d884b806fa2a946f27000d:260814-000801.processed.jsonl"
        }
    }

    with open(test_config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f)

    with open(test_config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    process_config(config)

    expected_files = [
        "tuple_mlton_run_mlton_vs_mlton.pdf",
        "tuple_mlton_run_mlton_vs_mlton.csv",
        "tuple_mlton_compile_mlton_vs_mlton.pdf",
        "tuple_mlton_compile_mlton_vs_mlton.csv",
        "tuple_mlton_size_mlton_vs_mlton.pdf",
        "tuple_mlton_size_mlton_vs_mlton.csv",
        "con_mlton_run_mlton_vs_mlton.pdf",
        "con_mlton_run_mlton_vs_mlton.csv",
        "con_mlton_compile_mlton_vs_mlton.pdf",
        "con_mlton_compile_mlton_vs_mlton.csv",
        "con_mlton_size_mlton_vs_mlton.pdf",
        "con_mlton_size_mlton_vs_mlton.csv",
        "tuple_parallel_bench_run_mlton_vs_mlton.pdf",
        "tuple_parallel_bench_run_mlton_vs_mlton.csv",
        "tuple_parallel_bench_size_mlton_vs_mlton.pdf",
        "tuple_parallel_bench_size_mlton_vs_mlton.csv",
        "con_parallel_bench_run_mlton_vs_mlton.pdf",
        "con_parallel_bench_run_mlton_vs_mlton.csv",
        "con_parallel_bench_size_mlton_vs_mlton.pdf",
        "con_parallel_bench_size_mlton_vs_mlton.csv",
        "chart_info.md",
        "all_charts.tex",
    ]

    for fname in expected_files:
        output_file = output_dir / fname
        assert output_file.exists(), f"Expected chart file {fname} was not created."
        assert output_file.stat().st_size > 0, f"Chart file {fname} is empty."


def test_process_config_suite_selection(tmp_path):
    output_dir = tmp_path / "charts_suite_select"
    test_config_path = tmp_path / "test_config_suite_select.json"

    # Section key is arbitrarily named, suite determines behavior
    config_data = {
        "output_directory": str(output_dir),
        "arbitrary_section_name": {
            "compiler": "mlton",
            "suite": "parallel_bench",
            "tuple": "cc_tuple_flatten_fixed_hash:260813-220330:flattening-tests:e957206262ad2a8b93398cdf777dd91275a74fbd:260813-220330.processed.jsonl"
        }
    }

    with open(test_config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f)

    with open(test_config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    process_config(config)

    assert (output_dir / "tuple_parallel_bench_run_mlton_vs_mlton.pdf").exists()
    assert (output_dir / "tuple_parallel_bench_run_mlton_vs_mlton.csv").exists()
    assert (output_dir / "tuple_parallel_bench_size_mlton_vs_mlton.pdf").exists()
    assert (output_dir / "tuple_parallel_bench_size_mlton_vs_mlton.csv").exists()
    assert not (output_dir / "tuple_mlton_run_mlton_vs_mlton.pdf").exists()
    assert not (output_dir / "tuple_mlton_run_mlton_vs_mlton.csv").exists()


def test_process_config_with_aos_soa(tmp_path):
    output_dir = tmp_path / "charts_aos_soa"
    test_config_path = tmp_path / "test_config_aos_soa.json"

    config_data = {
        "output_directory": str(output_dir),
        "parallel_bench_benchmarks_mlton_vs_mlton": {
            "compiler": "mlton",
            "suite": "parallel_bench",
            "aos": "cc_aos_flatten:260814-144252:flattening-tests:b4d8ba41a1a341b3a2390460f9f14e4babbc05ea:260814-144252.processed.jsonl",
            "soa": "cc_soa_flatten:260814-161510:flattening-tests:e979d4dcc72fa0405eaed998063f4acda35193e8:260814-161510.processed.jsonl",
        }
    }

    with open(test_config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f)

    with open(test_config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    process_config(config)

    expected_files = [
        "aos_parallel_bench_run_mlton_vs_mlton.pdf",
        "aos_parallel_bench_run_mlton_vs_mlton.csv",
        "aos_parallel_bench_size_mlton_vs_mlton.pdf",
        "aos_parallel_bench_size_mlton_vs_mlton.csv",
        "soa_parallel_bench_run_mlton_vs_mlton.pdf",
        "soa_parallel_bench_run_mlton_vs_mlton.csv",
        "soa_parallel_bench_size_mlton_vs_mlton.pdf",
        "soa_parallel_bench_size_mlton_vs_mlton.csv",
        "chart_info.md",
        "all_charts.tex",
    ]

    for fname in expected_files:
        output_file = output_dir / fname
        assert output_file.exists(), f"Expected chart file {fname} was not created."
        assert output_file.stat().st_size > 0, f"Chart file {fname} is empty."


def test_plot_parallel_bench_invalid_configs(tmp_path):
    # Case 1: Missing 'mlton-baseline'
    df_no_baseline = pd.DataFrame({
        'bench': ['b1'],
        'config': ['mlton-aos'],
        'test_results_secs': [[1.0]],
        'binary_md5': ['md5_1'],
    })
    with pytest.raises((ValueError, AssertionError)):
        plot_parallel_bench(df_no_baseline, out_dir=str(tmp_path))

    # Case 2: Only 'mlton-baseline' (0 test configurations remaining)
    df_only_baseline = pd.DataFrame({
        'bench': ['b1'],
        'config': ['mlton-baseline'],
        'test_results_secs': [[1.0]],
        'binary_md5': ['md5_1'],
    })
    with pytest.raises((ValueError, AssertionError)):
        plot_parallel_bench(df_only_baseline, out_dir=str(tmp_path))

    # Case 3: Multiple test configurations remaining (e.g., 'mlton-aos' and 'mlton-soa')
    df_multiple_test = pd.DataFrame({
        'bench': ['b1', 'b1', 'b1'],
        'config': ['mlton-baseline', 'mlton-aos', 'mlton-soa'],
        'test_results_secs': [[1.0], [1.1], [1.2]],
        'binary_md5': ['md5_1', 'md5_2', 'md5_3'],
    })
    with pytest.raises((ValueError, AssertionError)):
        plot_parallel_bench(df_multiple_test, out_dir=str(tmp_path))


def test_process_config_mpl_parallel_bench(tmp_path):
    output_dir = tmp_path / "charts_mpl"
    test_config_path = tmp_path / "test_config_mpl.json"

    config_data = {
        "output_directory": str(output_dir),
        "parallel_bench_benchmarks_mpl_vs_mpl": {
            "compiler": "mpl",
            "suite": "parallel_bench",
            "tuple": "test_mpl_cores:260815-120506:home:ab3c6b6692273c761927291bb65dbe256fd5ee64:260815-120506.processed.jsonl",
        }
    }

    with open(test_config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f)

    with open(test_config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    process_config(config)

    expected_files = [
        "tuple_parallel_bench_run_mpl_vs_mpl.pdf",
        "tuple_parallel_bench_run_mpl_vs_mpl.csv",
        "tuple_parallel_bench_size_mpl_vs_mpl.pdf",
        "tuple_parallel_bench_size_mpl_vs_mpl.csv",
        "tuple_parallel_bench_run_mpl_vs_mpl_geomean.pdf",
        "tuple_parallel_bench_run_mpl_vs_mpl_geomean.csv",
        "tuple_parallel_bench_run_mpl_vs_mpl_trellis.pdf",
        "tuple_parallel_bench_run_mpl_vs_mpl_trellis.csv",
        "chart_info.md",
        "all_charts.tex",
    ]

    for fname in expected_files:
        output_file = output_dir / fname
        assert output_file.exists(), f"Expected chart file {fname} was not created."
        assert output_file.stat().st_size > 0, f"Chart file {fname} is empty."



def test_infer_configs():
    # Explicit abbrevs passed
    df = pd.DataFrame({'config': ['a', 'b']})
    assert infer_configs(df, abbrevs=('c1', 'c2')) == ('c1', 'c2')

    # Baseline mlton-baseline + 1 test config
    df = pd.DataFrame({'config': ['mlton-baseline', 'mlton-opt']})
    assert infer_configs(df) == ('mlton-baseline', 'mlton-opt')

    # Baseline mpl-baseline + 1 test config
    df = pd.DataFrame({'config': ['mpl-baseline', 'mpl-tuple']})
    assert infer_configs(df) == ('mpl-baseline', 'mpl-tuple')

    # Non-allowable baseline name (e.g. 'custom-baseline') should raise ValueError
    df = pd.DataFrame({'config': ['custom-baseline', 'mpl-opt']})
    with pytest.raises(ValueError):
        infer_configs(df)

    # Invalid: no baseline and multiple configs
    df = pd.DataFrame({'config': ['opt1', 'opt2', 'opt3']})
    with pytest.raises(ValueError):
        infer_configs(df)


def test_constant_export():
    assert isinstance(USE_NEW_ANALYSIS_STYLE, bool)


def test_calculate_error_bars():
    # 1. Single pair of 1D lists
    test_trials = [1.0, 1.1, 1.2, 0.9, 1.0]
    base_trials = [1.0, 1.0, 1.0, 1.0, 1.0]
    em, ep = calculate_error_bars(test_trials, base_trials, random_state=42)
    assert em >= 0.0
    assert ep >= 0.0
    assert isinstance(em, float)
    assert isinstance(ep, float)

    # 2. pd.Series of trial lists
    s_test = pd.Series([[1.0, 1.1, 1.2], [2.0, 2.2, 2.1]], index=['b1', 'b2'])
    s_base = pd.Series([[1.0, 1.0, 1.0], [2.0, 2.0, 2.0]], index=['b1', 'b2'])
    em_series, ep_series = calculate_error_bars(s_test, s_base, random_state=42)
    assert isinstance(em_series, pd.Series)
    assert isinstance(ep_series, pd.Series)
    assert list(em_series.index) == ['b1', 'b2']
    assert len(em_series) == 2

    # 3. Scalar inputs / length <= 1 (should return 0.0, 0.0)
    s_test_sc = pd.Series([100, 200], index=['b1', 'b2'])
    s_base_sc = pd.Series([100, 200], index=['b1', 'b2'])
    em_sc, ep_sc = calculate_error_bars(s_test_sc, s_base_sc)
    assert (em_sc.values == 0.0).all()
    assert (ep_sc.values == 0.0).all()


def test_plot_parallel_bench_cores(tmp_path):
    df = pd.DataFrame({
        'bench': ['bench1', 'bench1', 'bench1', 'bench1'],
        'procs': [1, 2, 1, 2],
        'config': ['mpl-baseline', 'mpl-baseline', 'mpl-opt', 'mpl-opt'],
        'test_results_secs': [[1.0, 1.1], [0.5, 0.55], [0.8, 0.85], [0.4, 0.45]],
        'binary_md5': ['hash_base', 'hash_base', 'hash_opt', 'hash_opt'],
    })

    # Test new analysis style (default)
    out_file_new = "test_cores_chart_new"
    plot_parallel_bench_cores(df, title="Test Cores New", out_filename=out_file_new, out_dir=str(tmp_path), use_new_analysis_style=True)
    created_pdf = tmp_path / f"{out_file_new}.pdf"
    assert created_pdf.exists()
    assert created_pdf.stat().st_size > 0

    created_csv = tmp_path / f"{out_file_new}.csv"
    assert created_csv.exists()
    assert created_csv.stat().st_size > 0
    csv_df = pd.read_csv(created_csv)
    assert list(csv_df.columns) == ['bench', 'procs', 'relative_pct', 'err_minus_pct', 'err_plus_pct']
    assert len(csv_df) == 2

    # Test old analysis style
    out_file_old = "test_cores_chart_old"
    plot_parallel_bench_cores(df, title="Test Cores Old", out_filename=out_file_old, out_dir=str(tmp_path), use_new_analysis_style=False)
    created_pdf_old = tmp_path / f"{out_file_old}.pdf"
    assert created_pdf_old.exists()
    assert created_pdf_old.stat().st_size > 0

    created_csv_old = tmp_path / f"{out_file_old}.csv"
    assert created_csv_old.exists()
    assert created_csv_old.stat().st_size > 0
    csv_df_old = pd.read_csv(created_csv_old)
    assert list(csv_df_old.columns) == ['bench', 'procs', 'relative_pct', 'std_pct']
    assert len(csv_df_old) == 2


def test_plot_parallel_bench_geomean(tmp_path):
    df = pd.DataFrame({
        'bench': ['bench1', 'bench1', 'bench1', 'bench1'],
        'procs': [1, 2, 1, 2],
        'config': ['mpl-baseline', 'mpl-baseline', 'mpl-opt', 'mpl-opt'],
        'test_results_secs': [[1.0, 1.1], [0.5, 0.55], [0.8, 0.85], [0.4, 0.45]],
        'binary_md5': ['hash_base', 'hash_base', 'hash_opt', 'hash_opt'],
    })

    # Test new analysis style (default)
    out_file_new = "test_geomean_chart_new"
    plot_parallel_bench_geomean(df, title="Test Geomean New", out_filename=out_file_new, out_dir=str(tmp_path), use_new_analysis_style=True)
    created_pdf = tmp_path / f"{out_file_new}.pdf"
    assert created_pdf.exists()
    assert created_pdf.stat().st_size > 0

    created_csv = tmp_path / f"{out_file_new}.csv"
    assert created_csv.exists()
    assert created_csv.stat().st_size > 0
    csv_df = pd.read_csv(created_csv)
    assert list(csv_df.columns) == ['procs', 'relative_pct']
    assert len(csv_df) == 2

    # Test old analysis style
    out_file_old = "test_geomean_chart_old"
    plot_parallel_bench_geomean(df, title="Test Geomean Old", out_filename=out_file_old, out_dir=str(tmp_path), use_new_analysis_style=False)
    created_pdf_old = tmp_path / f"{out_file_old}.pdf"
    assert created_pdf_old.exists()
    assert created_pdf_old.stat().st_size > 0

    created_csv_old = tmp_path / f"{out_file_old}.csv"
    assert created_csv_old.exists()
    assert created_csv_old.stat().st_size > 0
    csv_df_old = pd.read_csv(created_csv_old)
    assert list(csv_df_old.columns) == ['procs', 'relative_pct']
    assert len(csv_df_old) == 2


def test_plot_parallel_bench_trellis(tmp_path):
    df = pd.DataFrame({
        'bench': ['bench1', 'bench1', 'bench1', 'bench1', 'bench2', 'bench2', 'bench2', 'bench2'],
        'procs': [1, 2, 1, 2, 1, 2, 1, 2],
        'config': ['mpl-baseline', 'mpl-baseline', 'mpl-opt', 'mpl-opt', 'mpl-baseline', 'mpl-baseline', 'mpl-opt', 'mpl-opt'],
        'test_results_secs': [[1.0, 1.1], [0.5, 0.55], [0.8, 0.85], [0.4, 0.45], [2.0, 2.2], [1.0, 1.1], [1.6, 1.7], [0.8, 0.9]],
        'binary_md5': ['hash_base1', 'hash_base1', 'hash_opt1', 'hash_opt1', 'hash_base2', 'hash_base2', 'hash_opt2', 'hash_opt2'],
    })

    # Test new analysis style (default)
    import matplotlib.pyplot as plt

    captured_axes_labels = []
    orig_savefig = plt.savefig

    def mock_savefig(*args, **kwargs):
        fig = plt.gcf()
        for ax in fig.axes:
            labels = [t.get_text() for t in ax.get_xticklabels() if t.get_visible()]
            captured_axes_labels.append((ax.get_title(), labels))
        orig_savefig(*args, **kwargs)

    plt.savefig = mock_savefig
    out_file_new = "test_trellis_chart_new"
    try:
        plot_parallel_bench_trellis(df, title="Test Trellis New", out_filename=out_file_new, out_dir=str(tmp_path), use_new_analysis_style=True)
    finally:
        plt.savefig = orig_savefig

    assert len(captured_axes_labels) == 3  # Geomean, bench1, bench2
    for title, labels in captured_axes_labels:
        assert len(labels) == 2, f"Axis {title} expected 2 tick labels, got {labels}"

    created_pdf = tmp_path / f"{out_file_new}.pdf"
    assert created_pdf.exists()
    assert created_pdf.stat().st_size > 0

    created_csv = tmp_path / f"{out_file_new}.csv"
    assert created_csv.exists()
    assert created_csv.stat().st_size > 0
    csv_df = pd.read_csv(created_csv)
    assert list(csv_df.columns) == ['bench', 'procs', 'relative_pct', 'err_minus_pct', 'err_plus_pct']
    assert len(csv_df) == 4

    # Test old analysis style
    out_file_old = "test_trellis_chart_old"
    plot_parallel_bench_trellis(df, title="Test Trellis Old", out_filename=out_file_old, out_dir=str(tmp_path), use_new_analysis_style=False)
    created_pdf_old = tmp_path / f"{out_file_old}.pdf"
    assert created_pdf_old.exists()
    assert created_pdf_old.stat().st_size > 0

    created_csv_old = tmp_path / f"{out_file_old}.csv"
    assert created_csv_old.exists()
    assert created_csv_old.stat().st_size > 0
    csv_df_old = pd.read_csv(created_csv_old)
    assert list(csv_df_old.columns) == ['bench', 'procs', 'relative_pct', 'std_pct']
    assert len(csv_df_old) == 4


def test_plot_parallel_bench_size(tmp_path):
    df = pd.DataFrame({
        'bench': ['bench1', 'bench1'],
        'procs': [1, 1],
        'config': ['mpl-baseline', 'mpl-opt'],
        'binary_bytes': [1000, 900],
        'binary_md5': ['hash_base', 'hash_opt'],
    })

    # New style
    out_file_new = "test_size_chart_new"
    plot_parallel_bench_size(df, title="Test Size New", out_filename=out_file_new, out_dir=str(tmp_path), use_new_analysis_style=True)
    created_pdf_new = tmp_path / f"{out_file_new}.pdf"
    assert created_pdf_new.exists()
    assert created_pdf_new.stat().st_size > 0

    created_csv_new = tmp_path / f"{out_file_new}.csv"
    assert created_csv_new.exists()
    assert created_csv_new.stat().st_size > 0
    csv_df_new = pd.read_csv(created_csv_new)
    assert list(csv_df_new.columns) == ['bench', 'relative_pct', 'err_minus_pct', 'err_plus_pct']
    assert csv_df_new.iloc[0]['bench'] == 'bench1'
    assert csv_df_new.iloc[0]['relative_pct'] == pytest.approx(-10.0)

    # Old style
    out_file_old = "test_size_chart_old"
    plot_parallel_bench_size(df, title="Test Size Old", out_filename=out_file_old, out_dir=str(tmp_path), use_new_analysis_style=False)
    created_pdf_old = tmp_path / f"{out_file_old}.pdf"
    assert created_pdf_old.exists()
    assert created_pdf_old.stat().st_size > 0

    created_csv_old = tmp_path / f"{out_file_old}.csv"
    assert created_csv_old.exists()
    assert created_csv_old.stat().st_size > 0
    csv_df_old = pd.read_csv(created_csv_old)
    assert list(csv_df_old.columns) == ['bench', 'relative_pct', 'std_pct']
    assert csv_df_old.iloc[0]['bench'] == 'bench1'
    assert csv_df_old.iloc[0]['relative_pct'] == pytest.approx(-10.0)


def test_plot_parallel_bench_size_multicore(tmp_path):
    df = pd.DataFrame({
        'bench': ['bench1', 'bench1', 'bench1', 'bench1'],
        'procs': [1, 2, 1, 2],
        'config': ['mpl-baseline', 'mpl-baseline', 'mpl-opt', 'mpl-opt'],
        'binary_bytes': [1000, 1000, 900, 900],
        'binary_md5': ['hash_base', 'hash_base', 'hash_opt', 'hash_opt'],
    })

    # New style
    out_file_new = "test_size_chart_multi_new"
    plot_parallel_bench_size(df, title="Test Multi Size New", out_filename=out_file_new, out_dir=str(tmp_path), use_new_analysis_style=True)
    created_pdf_new = tmp_path / f"{out_file_new}.pdf"
    assert created_pdf_new.exists()
    assert created_pdf_new.stat().st_size > 0

    created_csv_new = tmp_path / f"{out_file_new}.csv"
    assert created_csv_new.exists()
    assert created_csv_new.stat().st_size > 0
    csv_df_new = pd.read_csv(created_csv_new)
    assert list(csv_df_new.columns) == ['bench', 'relative_pct', 'err_minus_pct', 'err_plus_pct']
    assert len(csv_df_new) == 1
    assert csv_df_new.iloc[0]['relative_pct'] == pytest.approx(-10.0)

    # Old style
    out_file_old = "test_size_chart_multi_old"
    plot_parallel_bench_size(df, title="Test Multi Size Old", out_filename=out_file_old, out_dir=str(tmp_path), use_new_analysis_style=False)
    created_pdf_old = tmp_path / f"{out_file_old}.pdf"
    assert created_pdf_old.exists()
    assert created_pdf_old.stat().st_size > 0

    created_csv_old = tmp_path / f"{out_file_old}.csv"
    assert created_csv_old.exists()
    assert created_csv_old.stat().st_size > 0
    csv_df_old = pd.read_csv(created_csv_old)
    assert list(csv_df_old.columns) == ['bench', 'relative_pct', 'std_pct']
    assert len(csv_df_old) == 1
    assert csv_df_old.iloc[0]['relative_pct'] == pytest.approx(-10.0)


def test_plot_analysis_style_difference(tmp_path):
    # Construct a case where pair-wise mean of ratios differs from ratio of means
    # base trials: [10.0, 20.0], mean = 15.0
    # test trials: [5.0, 40.0], mean = 22.5
    # Pair-wise ratios: [5/10, 40/20] = [0.5, 2.0], mean ratio = 1.25 (+25%)
    # Ratio of means: 22.5 / 15.0 = 1.5 (+50%)
    df = pd.DataFrame({
        'bench': ['diff_bench', 'diff_bench'],
        'config': ['mlton-baseline', 'mlton-opt'],
        'test_results_secs': [[10.0, 20.0], [5.0, 40.0]],
        'binary_md5': ['h1', 'h2'],
    })

    plot_parallel_bench(df, values='test_results_secs', out_filename='diff_new', out_dir=str(tmp_path), use_new_analysis_style=True)
    plot_parallel_bench(df, values='test_results_secs', out_filename='diff_old', out_dir=str(tmp_path), use_new_analysis_style=False)

    df_new = pd.read_csv(tmp_path / "diff_new.csv")
    df_old = pd.read_csv(tmp_path / "diff_old.csv")

    assert df_new.iloc[0]['relative_pct'] == pytest.approx(50.0)
    assert df_old.iloc[0]['relative_pct'] == pytest.approx(25.0)


def test_process_config_old_and_new_style(tmp_path):
    config_data = {
        "output_directory": str(tmp_path / "charts_old_style"),
        "parallel_bench_benchmarks_mlton_vs_mlton": {
            "compiler": "mlton",
            "suite": "parallel_bench",
            "tuple": "cc_tuple_flatten_fixed_hash:260813-220330:flattening-tests:e957206262ad2a8b93398cdf777dd91275a74fbd:260813-220330.processed.jsonl",
        }
    }
    # Run with old style
    process_config(config_data, use_new_analysis_style=False)
    csv_old = tmp_path / "charts_old_style" / "tuple_parallel_bench_run_mlton_vs_mlton.csv"
    assert csv_old.exists()
    df_old = pd.read_csv(csv_old)
    assert 'std_pct' in df_old.columns

    # Run with new style
    config_data["output_directory"] = str(tmp_path / "charts_new_style")
    process_config(config_data, use_new_analysis_style=True)
    csv_new = tmp_path / "charts_new_style" / "tuple_parallel_bench_run_mlton_vs_mlton.csv"
    assert csv_new.exists()
    df_new = pd.read_csv(csv_new)
    assert 'err_minus_pct' in df_new.columns
    assert 'err_plus_pct' in df_new.columns


def test_plot_mlton_csv_content(tmp_path):
    df = pd.DataFrame({
        'bench': ['bench1', 'bench1'],
        'compilerAbbrev': ['MLton0', 'MLton1'],
        'runTime': [10.0, 8.0],
        'binaryChecksum': ['hash0', 'hash1'],
    })
    # New style
    out_file_new = "test_mlton_chart_new"
    plot_mlton(df, values='runTime', title='Test MLton New', out_filename=out_file_new, abbrevs=('MLton0', 'MLton1'), out_dir=str(tmp_path), use_new_analysis_style=True)
    csv_file_new = tmp_path / f"{out_file_new}.csv"
    assert csv_file_new.exists()
    csv_df_new = pd.read_csv(csv_file_new)
    assert list(csv_df_new.columns) == ['bench', 'MLton0', 'MLton1', 'relative_pct']
    assert len(csv_df_new) == 1
    assert csv_df_new.iloc[0]['bench'] == 'bench1'
    assert csv_df_new.iloc[0]['MLton0'] == pytest.approx(10.0)
    assert csv_df_new.iloc[0]['MLton1'] == pytest.approx(8.0)
    assert csv_df_new.iloc[0]['relative_pct'] == pytest.approx(-20.0)

    # Old style
    out_file_old = "test_mlton_chart_old"
    plot_mlton(df, values='runTime', title='Test MLton Old', out_filename=out_file_old, abbrevs=('MLton0', 'MLton1'), out_dir=str(tmp_path), use_new_analysis_style=False)
    csv_file_old = tmp_path / f"{out_file_old}.csv"
    assert csv_file_old.exists()
    csv_df_old = pd.read_csv(csv_file_old)
    assert list(csv_df_old.columns) == ['bench', 'MLton0', 'MLton1', 'relative_pct']
    assert len(csv_df_old) == 1
    assert csv_df_old.iloc[0]['bench'] == 'bench1'
    assert csv_df_old.iloc[0]['MLton0'] == pytest.approx(10.0)
    assert csv_df_old.iloc[0]['MLton1'] == pytest.approx(8.0)
    assert csv_df_old.iloc[0]['relative_pct'] == pytest.approx(-20.0)


def test_plot_parallel_bench_csv_content(tmp_path):
    df = pd.DataFrame({
        'bench': ['bench1', 'bench1'],
        'config': ['mlton-baseline', 'mlton-opt'],
        'test_results_secs': [[2.0, 4.0], [1.0, 2.0]],
        'binary_md5': ['hash0', 'hash1'],
    })

    # New style
    out_file_new = "test_pb_chart_new"
    plot_parallel_bench(df, values='test_results_secs', title='Test PB New', out_filename=out_file_new, out_dir=str(tmp_path), use_new_analysis_style=True)
    pdf_file_new = tmp_path / f"{out_file_new}.pdf"
    csv_file_new = tmp_path / f"{out_file_new}.csv"
    assert pdf_file_new.exists()
    assert csv_file_new.exists()
    csv_df_new = pd.read_csv(csv_file_new)
    assert list(csv_df_new.columns) == ['bench', 'relative_pct', 'err_minus_pct', 'err_plus_pct']
    assert len(csv_df_new) == 1
    assert csv_df_new.iloc[0]['bench'] == 'bench1'
    assert csv_df_new.iloc[0]['relative_pct'] == pytest.approx(-50.0)

    # Old style
    out_file_old = "test_pb_chart_old"
    plot_parallel_bench(df, values='test_results_secs', title='Test PB Old', out_filename=out_file_old, out_dir=str(tmp_path), use_new_analysis_style=False)
    pdf_file_old = tmp_path / f"{out_file_old}.pdf"
    csv_file_old = tmp_path / f"{out_file_old}.csv"
    assert pdf_file_old.exists()
    assert csv_file_old.exists()
    csv_df_old = pd.read_csv(csv_file_old)
    assert list(csv_df_old.columns) == ['bench', 'relative_pct', 'std_pct']
    assert len(csv_df_old) == 1
    assert csv_df_old.iloc[0]['bench'] == 'bench1'
    assert csv_df_old.iloc[0]['relative_pct'] == pytest.approx(-50.0)


def test_every_pdf_has_matching_csv(tmp_path):
    output_dir = tmp_path / "charts_all_match"
    config_data = {
        "output_directory": str(output_dir),
        "mlton_benchmarks_mlton_vs_mlton": {
            "compiler": "mlton",
            "suite": "mlton",
            "tuple": "test_conapp_flatten_cc_icelake:flattening-tests:05e9492b9:20260725_223512.jsonl"
        },
        "parallel_bench_benchmarks_mlton_vs_mlton": {
            "compiler": "mlton",
            "suite": "parallel_bench",
            "tuple": "cc_tuple_flatten_fixed_hash:260813-220330:flattening-tests:e957206262ad2a8b93398cdf777dd91275a74fbd:260813-220330.processed.jsonl"
        },
        "parallel_bench_benchmarks_mpl_vs_mpl": {
            "compiler": "mpl",
            "suite": "parallel_bench",
            "tuple": "test_mpl_cores:260815-120506:home:ab3c6b6692273c761927291bb65dbe256fd5ee64:260815-120506.processed.jsonl"
        }
    }
    process_config(config_data)

    pdf_files = list(output_dir.glob("*.pdf"))
    assert len(pdf_files) > 0
    for pdf_file in pdf_files:
        csv_file = pdf_file.with_suffix(".csv")
        assert csv_file.exists(), f"Missing matching CSV for {pdf_file.name}"
        assert csv_file.stat().st_size > 0
        df = pd.read_csv(csv_file)
        assert len(df) > 0, f"CSV {csv_file.name} has no data rows"


def test_csv_values_truncated_to_3_decimal_places(tmp_path):
    df = pd.DataFrame({
        'bench': ['bench1', 'bench1'],
        'compilerAbbrev': ['MLton0', 'MLton1'],
        'runTime': [10.123456, 8.987654],
        'binaryChecksum': ['hash0', 'hash1'],
    })
    out_file = "test_trunc_chart"
    plot_mlton(df, values='runTime', title='Test Trunc', out_filename=out_file, abbrevs=('MLton0', 'MLton1'), out_dir=str(tmp_path))

    csv_file = tmp_path / f"{out_file}.csv"
    assert csv_file.exists()
    content = csv_file.read_text(encoding="utf-8")
    lines = content.strip().split("\n")
    header = lines[0].split(",")
    values = lines[1].split(",")
    assert header == ['bench', 'MLton0', 'MLton1', 'relative_pct']
    assert values[1] == "10.123"
    assert values[2] == "8.988"
    assert values[3] == "-11.22" or values[3] == "-11.220" or len(values[3].split(".")[1]) <= 3


def test_generate_all_charts_tex_includes_filenames():
    config_data = {
        "output_directory": "charts/",
        "mlton_benchmarks_mlton_vs_mlton": {
            "compiler": "mlton",
            "suite": "mlton",
            "tuple": "my_mlton_data_file.jsonl"
        },
        "parallel_bench_benchmarks_mlton_vs_mlton": {
            "compiler": "mlton",
            "suite": "parallel_bench",
            "tuple": "my_pb_mlton_data_file.jsonl"
        },
        "parallel_bench_benchmarks_mpl_vs_mpl": {
            "compiler": "mpl",
            "suite": "parallel_bench",
            "tuple": "my_pb_mpl_data_file.jsonl"
        }
    }

    tex = generate_all_charts_tex(config_data)

    assert r"\protect\nolinkurl{my_mlton_data_file.jsonl}" in tex
    assert r"\protect\nolinkurl{my_pb_mlton_data_file.jsonl}" in tex
    assert r"\protect\nolinkurl{my_pb_mpl_data_file.jsonl}" in tex
    assert r"\section{Tuple Flattening}" in tex
    assert r"\subsection{MLton Benchmarks (Tuple Flattening)}" in tex
    assert r"\subsection{\texttt{parallel-ml-bench}: MLton vs MLton (Tuple Flattening)}" in tex
    assert r"\subsection{\texttt{parallel-ml-bench}: MPL vs MPL (Tuple Flattening)}" in tex

    # Verify Data Tables section is at the end
    assert r"\section{Data Tables}" in tex
    fig_idx = tex.find(r"tuple_parallel_bench_run_mpl_vs_mpl.pdf")
    geomean_idx = tex.find(r"tuple_parallel_bench_run_mpl_vs_mpl_geomean.pdf")
    trellis_idx = tex.find(r"tuple_parallel_bench_run_mpl_vs_mpl_trellis.pdf")
    data_tables_idx = tex.find(r"\section{Data Tables}")
    csv_idx = tex.find(r"\importcsv{tuple_parallel_bench_run_mpl_vs_mpl.csv}")
    assert fig_idx < geomean_idx < trellis_idx < data_tables_idx < csv_idx


def test_latex_templates_renderers():
    from latex_templates import (
        render_mlton_subsection,
        render_parallel_bench_mlton_subsection,
        render_parallel_bench_mpl_subsection,
        render_mlton_tables_subsection,
        render_parallel_bench_mlton_tables_subsection,
        render_parallel_bench_mpl_tables_subsection,
        format_caption,
    )

    cap = format_caption("Base caption", "data.jsonl")
    assert r"Base caption Data: \protect\nolinkurl{data.jsonl}." in cap

    mlton_sub = render_mlton_subsection("tuple", "data_mlton.jsonl")
    assert r"\subsection{MLton Benchmarks (Tuple Flattening)}" in mlton_sub
    assert r"tuple_mlton_run_mlton_vs_mlton.pdf" in mlton_sub
    assert r"\protect\nolinkurl{data_mlton.jsonl}" in mlton_sub

    pb_mlton_sub = render_parallel_bench_mlton_subsection("con", "data_pb_mlton.jsonl")
    assert r"\subsection{\texttt{parallel-ml-bench}: MLton vs MLton (\texttt{ConApp} Flattening)}" in pb_mlton_sub
    assert r"con_parallel_bench_run_mlton_vs_mlton.pdf" in pb_mlton_sub
    assert r"\protect\nolinkurl{data_pb_mlton.jsonl}" in pb_mlton_sub

    pb_mpl_sub = render_parallel_bench_mpl_subsection("aos", "data_pb_mpl.jsonl")
    assert r"\subsection{\texttt{parallel-ml-bench}: MPL vs MPL (AoS Flattening)}" in pb_mpl_sub
    assert r"aos_parallel_bench_run_mpl_vs_mpl.pdf" in pb_mpl_sub
    assert r"aos_parallel_bench_run_mpl_vs_mpl_geomean.pdf" in pb_mpl_sub
    assert r"aos_parallel_bench_run_mpl_vs_mpl_trellis.pdf" in pb_mpl_sub
    assert r"\protect\nolinkurl{data_pb_mpl.jsonl}" in pb_mpl_sub

    mlton_tbl = render_mlton_tables_subsection("tuple")
    assert r"\subsubsection{MLton Benchmarks (Tuple Flattening)}" in mlton_tbl
    assert r"\importcsv{tuple_mlton_run_mlton_vs_mlton.csv}" in mlton_tbl

    pb_mlton_tbl = render_parallel_bench_mlton_tables_subsection("con")
    assert r"\subsubsection{\texttt{parallel-ml-bench}: MLton vs MLton (\texttt{ConApp} Flattening)}" in pb_mlton_tbl
    assert r"\importcsv{con_parallel_bench_run_mlton_vs_mlton.csv}" in pb_mlton_tbl

    pb_mpl_tbl = render_parallel_bench_mpl_tables_subsection("aos")
    assert r"\subsubsection{\texttt{parallel-ml-bench}: MPL vs MPL (AoS Flattening)}" in pb_mpl_tbl
    assert r"\importcsv{aos_parallel_bench_run_mpl_vs_mpl.csv}" in pb_mpl_tbl

    from latex_templates import (
        render_trial_scatter_subsection,
        render_trial_scatter_tables_subsection,
    )
    scatter_sub = render_trial_scatter_subsection("test_scatter", "delaunay", "data_file.jsonl", compiler="mlton", suite="parallel_bench", exp_type="tuple")
    assert r"\subsection{\texttt{delaunay} (\texttt{parallel-ml-bench}: MLton (Tuple Flattening))}" in scatter_sub
    assert r"\includegraphics[width=\textwidth,keepaspectratio]{test_scatter.pdf}" in scatter_sub
    assert r"\protect\nolinkurl{data_file.jsonl}" in scatter_sub

    scatter_tbl = render_trial_scatter_tables_subsection("test_scatter", "delaunay", compiler="mlton", suite="parallel_bench", exp_type="tuple")
    assert r"\subsubsection{\texttt{delaunay} (\texttt{parallel-ml-bench}: MLton (Tuple Flattening))}" in scatter_tbl
    assert r"\importcsv{test_scatter.csv}" in scatter_tbl


def test_plot_parallel_bench_drilldown(tmp_path):
    from build_charts_lib import plot_parallel_bench_drilldown
    import matplotlib.pyplot as plt

    df = pd.DataFrame({
        'bench': ['bench1', 'bench1'],
        'procs': [1, 1],
        'config': ['mlton-baseline', 'mlton-opt'],
        'warmup_result_secs': [[1.5, 1.2], [1.4, 1.1]],
        'test_results_secs': [[1.0, 1.05, 1.02], [0.8, 0.82, 0.81]],
        'binary_md5': ['hash_base', 'hash_opt'],
    })

    out_file = "test_scatter_chart"
    plot_parallel_bench_drilldown(df, bench_name='bench1', title='Scatter Test', out_filename=out_file, out_dir=str(tmp_path))

    pdf_path = tmp_path / f"{out_file}.pdf"
    csv_path = tmp_path / f"{out_file}.csv"

    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0
    assert csv_path.exists()
    assert csv_path.stat().st_size > 0

    csv_df = pd.read_csv(csv_path)
    assert list(csv_df.columns) == ['bench', 'procs', 'config', 'phase', 'trial', 'time_secs']
    assert len(csv_df) == 10  # (2 warmup + 3 test) * 2 configs
    assert set(csv_df['config']) == {'mlton-baseline', 'mlton-opt'}
    assert set(csv_df['phase']) == {'warmup', 'test'}


def test_process_config_trial_scatter_plots(tmp_path):
    output_dir = tmp_path / "charts_scatter"
    test_config_path = tmp_path / "test_config_scatter.json"

    config_data = {
        "output_directory": str(output_dir),
        "trial_scatter_plots": {
            "delunay_mlton_parallel_ml_bench_scatter": {
                "compiler": "mlton",
                "suite": "parallel_bench",
                "experiment_type": "tuple",
                "benchmark": "delunay",
                "source": "mlton_tuple_full_parallel_mlton:260816-150321:flattening-tests:c3def9c964dc7d927f01861817cdc614debfebfd:260816-150321.processed.jsonl"
            },
            "dedup_mlton_parallel_ml_bench_scatter": {
                "compiler": "mlton",
                "suite": "parallel_bench",
                "experiment_type": "con",
                "benchmark": "dedup",
                "source": "mlton_con_full_parallel_mlton:260816-131352:flattening-tests:c3def9c964dc7d927f01861817cdc614debfebfd:260816-131352.processed.jsonl"
            }
        }
    }

    with open(test_config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f)

    with open(test_config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    process_config(config)

    expected_files = [
        "delunay_mlton_parallel_ml_bench_scatter.pdf",
        "delunay_mlton_parallel_ml_bench_scatter.csv",
        "dedup_mlton_parallel_ml_bench_scatter.pdf",
        "dedup_mlton_parallel_ml_bench_scatter.csv",
        "chart_info.md",
        "all_charts.tex",
    ]

    for fname in expected_files:
        output_file = output_dir / fname
        assert output_file.exists(), f"Expected chart file {fname} was not created."
        assert output_file.stat().st_size > 0, f"Chart file {fname} is empty."

    tex_content = (output_dir / "all_charts.tex").read_text(encoding="utf-8")
    assert r"\section{Trial Scatter Plots}" in tex_content
    assert r"delunay_mlton_parallel_ml_bench_scatter.pdf" in tex_content
    assert r"dedup_mlton_parallel_ml_bench_scatter.pdf" in tex_content
    assert r"\importcsv{delunay_mlton_parallel_ml_bench_scatter.csv}" in tex_content
    assert r"\importcsv{dedup_mlton_parallel_ml_bench_scatter.csv}" in tex_content


def test_resolve_series_path():
    cfg = {
        "section_a": {
            "sub_b": "file_b.jsonl",
            "sub_dict": {"source": "file_dict.jsonl"}
        }
    }
    assert resolve_series_path(cfg, "section_a.sub_b") == "file_b.jsonl"
    assert resolve_series_path(cfg, "section_a.sub_dict") == "file_dict.jsonl"

    with pytest.raises(KeyError):
        resolve_series_path(cfg, "section_a.nonexistent")

    with pytest.raises(KeyError):
        resolve_series_path(cfg, "nonexistent.sub")

    with pytest.raises(ValueError):
        resolve_series_path({"section": {"empty_dict": {}}}, "section.empty_dict")


def test_compute_parallel_bench_geomean():
    df = pd.DataFrame({
        'bench': ['bench1', 'bench1', 'bench1', 'bench1', 'bench2', 'bench2', 'bench2', 'bench2'],
        'procs': [1, 2, 1, 2, 1, 2, 1, 2],
        'config': ['mpl-baseline', 'mpl-baseline', 'mpl-opt', 'mpl-opt', 'mpl-baseline', 'mpl-baseline', 'mpl-opt', 'mpl-opt'],
        'test_results_secs': [[2.0], [1.0], [1.0], [0.5], [4.0], [2.0], [2.0], [1.0]],
        'binary_md5': ['h1', 'h1', 'h2', 'h2', 'h3', 'h3', 'h4', 'h4'],
    })
    geomean_s = compute_parallel_bench_geomean(df)
    assert 1 in geomean_s.index
    assert 2 in geomean_s.index
    # 50% faster -> -50%
    assert geomean_s[1] == pytest.approx(-50.0)
    assert geomean_s[2] == pytest.approx(-50.0)


def test_plot_compare_geomeans(tmp_path):
    df1 = pd.DataFrame({
        'bench': ['bench1', 'bench1', 'bench1', 'bench1'],
        'procs': [1, 2, 1, 2],
        'config': ['mpl-baseline', 'mpl-baseline', 'mpl-opt', 'mpl-opt'],
        'test_results_secs': [[2.0], [1.0], [1.0], [0.5]],
        'binary_md5': ['h1', 'h1', 'h2', 'h2'],
    })
    df2 = pd.DataFrame({
        'bench': ['bench1', 'bench1', 'bench1', 'bench1'],
        'procs': [1, 2, 1, 2],
        'config': ['mpl-baseline', 'mpl-baseline', 'mpl-opt', 'mpl-opt'],
        'test_results_secs': [[2.0], [1.0], [1.5], [0.75]],
        'binary_md5': ['h1', 'h1', 'h2', 'h2'],
    })

    series_specs = [
        {"series_name": "Series A", "df": df1},
        {"series_name": "Series B", "df": df2},
    ]

    out_file = "test_compare_output"
    plot_compare_geomeans(
        series_specs=series_specs,
        title="Comparison Chart",
        out_filename=out_file,
        out_dir=str(tmp_path),
    )

    pdf_path = tmp_path / f"{out_file}.pdf"
    csv_path = tmp_path / f"{out_file}.csv"
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0
    assert csv_path.exists()
    assert csv_path.stat().st_size > 0

    csv_df = pd.read_csv(csv_path)
    assert list(csv_df.columns) == ['procs', 'Series A', 'Series B']
    assert len(csv_df) == 2
    assert csv_df.iloc[0]['procs'] == 1
    assert csv_df.iloc[0]['Series A'] == pytest.approx(-50.0)
    assert csv_df.iloc[0]['Series B'] == pytest.approx(-25.0)


def test_process_config_compare_geomeans(tmp_path):
    output_dir = tmp_path / "charts_compare"
    test_config_path = tmp_path / "test_config_compare.json"

    config_data = {
        "output_directory": str(output_dir),
        "parallel_bench_benchmarks_mpl_vs_mpl": {
            "compiler": "mpl",
            "suite": "parallel_bench",
            "tuple": "test_mpl_cores:260815-120506:home:ab3c6b6692273c761927291bb65dbe256fd5ee64:260815-120506.processed.jsonl"
        },
        "compare_geomeans": {
            "my_test_geomeans": [
                {
                    "series_name": "Tuple Baseline",
                    "series_path": "parallel_bench_benchmarks_mpl_vs_mpl.tuple"
                }
            ]
        }
    }

    with open(test_config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f)

    with open(test_config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    process_config(config)

    expected_files = [
        "my_test_geomeans.pdf",
        "my_test_geomeans.csv",
        "chart_info.md",
        "all_charts.tex",
    ]

    for fname in expected_files:
        output_file = output_dir / fname
        assert output_file.exists(), f"Expected file {fname} was not created."
        assert output_file.stat().st_size > 0, f"File {fname} is empty."

    tex_content = (output_dir / "all_charts.tex").read_text(encoding="utf-8")
    assert r"\section{Compare Geomeans}" in tex_content
    assert r"my_test_geomeans.pdf" in tex_content
    assert r"\importcsv{my_test_geomeans.csv}" in tex_content


def test_latex_templates_compare_geomeans():
    from latex_templates import (
        render_compare_geomeans_subsection,
        render_compare_geomeans_tables_subsection,
    )
    sub_tex = render_compare_geomeans_subsection("tuple_exp_geomeans", series_paths=["file1.jsonl", "file2.jsonl"])
    assert r"\subsection{Tuple Exp Geomeans}" in sub_tex
    assert r"tuple_exp_geomeans.pdf" in sub_tex
    assert r"\protect\nolinkurl{file1.jsonl}" in sub_tex
    assert r"\protect\nolinkurl{file2.jsonl}" in sub_tex

    tbl_tex = render_compare_geomeans_tables_subsection("tuple_exp_geomeans")
    assert r"\subsubsection{Tuple Exp Geomeans}" in tbl_tex
    assert r"\importcsv{tuple_exp_geomeans.csv}" in tbl_tex




