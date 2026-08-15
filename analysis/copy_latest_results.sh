#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${TARGET_DIR:-$SCRIPT_DIR/data}"

usage() {
  echo "Usage: $0 --type=[parallel_bench|mlton] --count <N>" >&2
  echo "" >&2
  echo "Options:" >&2
  echo "  --type <TYPE>  Type of results to copy (parallel_bench or mlton, required)" >&2
  echo "  --count <N>    Number of most recent output files to copy (required, positive integer)" >&2
  echo "  -h, --help     Show this help message" >&2
  exit 1
}

COUNT=""
TYPE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --type)
      if [[ -n "${2:-}" && "$2" != --* ]]; then
        TYPE="$2"
        shift 2
      else
        echo "Error: --type requires an argument." >&2
        usage
      fi
      ;;
    --type=*)
      TYPE="${1#*=}"
      shift
      ;;
    --count)
      if [[ -n "${2:-}" && "$2" != --* ]]; then
        COUNT="$2"
        shift 2
      else
        echo "Error: --count requires an argument." >&2
        usage
      fi
      ;;
    --count=*)
      COUNT="${1#*=}"
      shift
      ;;
    -h|--help)
      usage
      ;;
    *)
      echo "Error: Unknown argument '$1'" >&2
      usage
      ;;
  esac
done

if [[ -z "$TYPE" ]]; then
  echo "Error: --type is required." >&2
  usage
fi

case "$TYPE" in
  mlton)
    DEFAULT_SOURCE_DIR="$HOME/code/mlton/benchmark/benchmark-new/outputs"
    ;;
  parallel_bench)
    DEFAULT_SOURCE_DIR="$HOME/code/parallel-ml-bench/processed_results"
    ;;
  *)
    echo "Error: Invalid --type '$TYPE'. Must be 'parallel_bench' or 'mlton'." >&2
    usage
    ;;
esac

SOURCE_DIR="${SOURCE_DIR:-$DEFAULT_SOURCE_DIR}"

if [[ -z "$COUNT" ]]; then
  echo "Error: --count is required." >&2
  usage
fi

if ! [[ "$COUNT" =~ ^[1-9][0-9]*$ ]]; then
  echo "Error: --count must be a positive integer, got '$COUNT'." >&2
  exit 1
fi

if [[ ! -d "$SOURCE_DIR" ]]; then
  echo "Error: Source directory '$SOURCE_DIR' does not exist." >&2
  exit 1
fi

mkdir -p "$TARGET_DIR"

echo "Copying the $COUNT most recent file(s) from '$SOURCE_DIR' to '$TARGET_DIR'..."

# Get the $COUNT most recent files sorted by modification time (newest first)
mapfile -t FILES < <(find "$SOURCE_DIR" -maxdepth 1 -type f -printf '%T@ %p\n' | sort -rn | head -n "$COUNT" | cut -d' ' -f2-)

if [[ ${#FILES[@]} -eq 0 ]]; then
  echo "No files found in '$SOURCE_DIR'."
  exit 0
fi

for file in "${FILES[@]}"; do
  echo "$file -> $TARGET_DIR/"
  cp "$file" "$TARGET_DIR/"
done

echo "Successfully copied ${#FILES[@]} file(s)."
