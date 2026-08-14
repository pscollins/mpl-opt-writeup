import json
from build_charts_lib import process_config


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
        "tuple_mlton_compile_mlton_vs_mlton.pdf",
        "tuple_mlton_size_mlton_vs_mlton.pdf",
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
        "tuple_parallel_bench_size_mlton_vs_mlton.pdf",
        "con_parallel_bench_run_mlton_vs_mlton.pdf",
        "con_parallel_bench_size_mlton_vs_mlton.pdf",
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
        "tuple_mlton_compile_mlton_vs_mlton.pdf",
        "tuple_mlton_size_mlton_vs_mlton.pdf",
        "con_mlton_run_mlton_vs_mlton.pdf",
        "con_mlton_compile_mlton_vs_mlton.pdf",
        "con_mlton_size_mlton_vs_mlton.pdf",
        "tuple_parallel_bench_run_mlton_vs_mlton.pdf",
        "tuple_parallel_bench_size_mlton_vs_mlton.pdf",
        "con_parallel_bench_run_mlton_vs_mlton.pdf",
        "con_parallel_bench_size_mlton_vs_mlton.pdf",
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
    assert (output_dir / "tuple_parallel_bench_size_mlton_vs_mlton.pdf").exists()
    assert not (output_dir / "tuple_mlton_run_mlton_vs_mlton.pdf").exists()


