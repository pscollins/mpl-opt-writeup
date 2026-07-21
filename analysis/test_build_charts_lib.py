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
    ]

    for fname in expected_files:
        output_file = output_dir / fname
        assert output_file.exists(), f"Expected chart file {fname} was not created."
        assert output_file.stat().st_size > 0, f"Chart file {fname} is empty."
