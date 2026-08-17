import json
import pandas as pd
import pytest
from build_charts_lib import (
    process_config,
    plot_mlton,
    plot_parallel_bench,
    plot_parallel_bench_cores,
    plot_parallel_bench_size,
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
    ]

    for fname in expected_files:
        output_file = output_dir / fname
        assert output_file.exists(), f"Expected chart file {fname} was not created."
        assert output_file.stat().st_size > 0, f"Chart file {fname} is empty."

    chart_info_content = (output_dir / "chart_info.md").read_text(encoding="utf-8")
    assert "Data generated at " in chart_info_content
    assert "using the following config:" in chart_info_content


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
        "chart_info.md",
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


def test_plot_parallel_bench_cores(tmp_path):
    df = pd.DataFrame({
        'bench': ['bench1', 'bench1', 'bench1', 'bench1'],
        'procs': [1, 2, 1, 2],
        'config': ['mpl-baseline', 'mpl-baseline', 'mpl-opt', 'mpl-opt'],
        'test_results_secs': [[1.0, 1.1], [0.5, 0.55], [0.8, 0.85], [0.4, 0.45]],
        'binary_md5': ['hash_base', 'hash_base', 'hash_opt', 'hash_opt'],
    })

    out_file = "test_cores_chart"
    plot_parallel_bench_cores(df, title="Test Cores", out_filename=out_file, out_dir=str(tmp_path))
    created_pdf = tmp_path / f"{out_file}.pdf"
    assert created_pdf.exists()
    assert created_pdf.stat().st_size > 0

    created_csv = tmp_path / f"{out_file}.csv"
    assert created_csv.exists()
    assert created_csv.stat().st_size > 0
    csv_df = pd.read_csv(created_csv)
    assert list(csv_df.columns) == ['bench', 'procs', 'relative_pct', 'std_pct']
    assert len(csv_df) == 2


def test_plot_parallel_bench_size(tmp_path):
    df = pd.DataFrame({
        'bench': ['bench1', 'bench1'],
        'procs': [1, 1],
        'config': ['mpl-baseline', 'mpl-opt'],
        'binary_bytes': [1000, 900],
        'binary_md5': ['hash_base', 'hash_opt'],
    })

    out_file = "test_size_chart"
    plot_parallel_bench_size(df, title="Test Size", out_filename=out_file, out_dir=str(tmp_path))
    created_pdf = tmp_path / f"{out_file}.pdf"
    assert created_pdf.exists()
    assert created_pdf.stat().st_size > 0

    created_csv = tmp_path / f"{out_file}.csv"
    assert created_csv.exists()
    assert created_csv.stat().st_size > 0
    csv_df = pd.read_csv(created_csv)
    assert list(csv_df.columns) == ['bench', 'relative_pct', 'std_pct']
    assert csv_df.iloc[0]['bench'] == 'bench1'
    assert csv_df.iloc[0]['relative_pct'] == pytest.approx(-10.0)


def test_plot_parallel_bench_size_multicore(tmp_path):
    df = pd.DataFrame({
        'bench': ['bench1', 'bench1', 'bench1', 'bench1'],
        'procs': [1, 2, 1, 2],
        'config': ['mpl-baseline', 'mpl-baseline', 'mpl-opt', 'mpl-opt'],
        'binary_bytes': [1000, 1000, 900, 900],
        'binary_md5': ['hash_base', 'hash_base', 'hash_opt', 'hash_opt'],
    })

    out_file = "test_size_chart_multi"
    plot_parallel_bench_size(df, title="Test Multi Size", out_filename=out_file, out_dir=str(tmp_path))
    created_pdf = tmp_path / f"{out_file}.pdf"
    assert created_pdf.exists()
    assert created_pdf.stat().st_size > 0

    created_csv = tmp_path / f"{out_file}.csv"
    assert created_csv.exists()
    assert created_csv.stat().st_size > 0
    csv_df = pd.read_csv(created_csv)
    assert list(csv_df.columns) == ['bench', 'relative_pct', 'std_pct']
    assert len(csv_df) == 1
    assert csv_df.iloc[0]['relative_pct'] == pytest.approx(-10.0)


def test_process_config_all_sections(tmp_path):
    output_dir = tmp_path / "charts_all"
    test_config_path = tmp_path / "test_config_all.json"

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
        "tuple_parallel_bench_run_mlton_vs_mlton.pdf",
        "tuple_parallel_bench_run_mlton_vs_mlton.csv",
        "tuple_parallel_bench_size_mlton_vs_mlton.pdf",
        "tuple_parallel_bench_size_mlton_vs_mlton.csv",
        "tuple_parallel_bench_run_mpl_vs_mpl.pdf",
        "tuple_parallel_bench_run_mpl_vs_mpl.csv",
        "tuple_parallel_bench_size_mpl_vs_mpl.pdf",
        "tuple_parallel_bench_size_mpl_vs_mpl.csv",
        "chart_info.md",
    ]

    for fname in expected_files:
        output_file = output_dir / fname
        assert output_file.exists(), f"Expected chart file {fname} was not created."
        assert output_file.stat().st_size > 0, f"Chart file {fname} is empty."


def test_plot_mlton_csv_content(tmp_path):
    df = pd.DataFrame({
        'bench': ['bench1', 'bench1'],
        'compilerAbbrev': ['MLton0', 'MLton1'],
        'runTime': [10.0, 8.0],
        'binaryChecksum': ['hash0', 'hash1'],
    })
    out_file = "test_mlton_chart"
    plot_mlton(df, values='runTime', title='Test MLton', out_filename=out_file, abbrevs=('MLton0', 'MLton1'), out_dir=str(tmp_path))

    pdf_file = tmp_path / f"{out_file}.pdf"
    csv_file = tmp_path / f"{out_file}.csv"
    assert pdf_file.exists()
    assert csv_file.exists()

    csv_df = pd.read_csv(csv_file)
    assert list(csv_df.columns) == ['bench', 'MLton0', 'MLton1', 'relative_pct']
    assert len(csv_df) == 1
    row = csv_df.iloc[0]
    assert row['bench'] == 'bench1'
    assert row['MLton0'] == pytest.approx(10.0)
    assert row['MLton1'] == pytest.approx(8.0)
    assert row['relative_pct'] == pytest.approx(-20.0)


def test_plot_parallel_bench_csv_content(tmp_path):
    df = pd.DataFrame({
        'bench': ['bench1', 'bench1'],
        'config': ['mlton-baseline', 'mlton-opt'],
        'test_results_secs': [[2.0, 4.0], [1.0, 2.0]],
        'binary_md5': ['hash0', 'hash1'],
    })
    out_file = "test_pb_chart"
    plot_parallel_bench(df, values='test_results_secs', title='Test PB', out_filename=out_file, out_dir=str(tmp_path))

    pdf_file = tmp_path / f"{out_file}.pdf"
    csv_file = tmp_path / f"{out_file}.csv"
    assert pdf_file.exists()
    assert csv_file.exists()

    csv_df = pd.read_csv(csv_file)
    assert list(csv_df.columns) == ['bench', 'relative_pct', 'std_pct']
    assert len(csv_df) == 1
    row = csv_df.iloc[0]
    assert row['bench'] == 'bench1'
    assert row['relative_pct'] == pytest.approx(-50.0)


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
