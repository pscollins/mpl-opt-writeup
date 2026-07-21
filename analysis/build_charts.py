import argparse
import json
import os
import sys

from build_charts_lib import process_config


def main():
    parser = argparse.ArgumentParser(description="Build benchmark charts from configuration.")
    parser.add_argument(
        "--config",
        required=True,
        help="Path to the JSON configuration file.",
    )
    args = parser.parse_args()

    if not os.path.exists(args.config):
        print(f"Error: Config file not found: {args.config}", file=sys.stderr)
        sys.exit(1)

    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)

    process_config(config)


if __name__ == "__main__":
    main()
