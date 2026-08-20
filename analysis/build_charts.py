import argparse
import json
import os
import sys

from build_charts_lib import process_config

USE_NEW_ANALYSIS_STYLE = True


def main():
    parser = argparse.ArgumentParser(description="Build benchmark charts from configuration.")
    parser.add_argument(
        "--config",
        required=True,
        help="Path to the JSON configuration file.",
    )
    parser.add_argument(
        "--use-new-analysis-style",
        dest="use_new_analysis_style",
        action="store_true",
        default=USE_NEW_ANALYSIS_STYLE,
        help="Use new analysis style (ratio of averages and bootstrapping CI).",
    )
    parser.add_argument(
        "--use-old-analysis-style",
        dest="use_new_analysis_style",
        action="store_false",
        help="Use old analysis style (average of ratios and sample stddev).",
    )
    args = parser.parse_args()

    if not os.path.exists(args.config):
        print(f"Error: Config file not found: {args.config}", file=sys.stderr)
        sys.exit(1)

    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)

    process_config(config, use_new_analysis_style=args.use_new_analysis_style)


if __name__ == "__main__":
    main()
