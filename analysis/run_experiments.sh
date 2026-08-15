#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  echo "Usage: $0 --compiler=[mlton|mpl] --suite=[mlton|parallel_bench] --base_nick=<nick>" >&2
  echo "" >&2
  echo "Options:" >&2
  echo "  --compiler <mlton|mpl>          Compiler to use (mlton or mpl, required)" >&2
  echo "  --suite <mlton|parallel_bench>  Benchmark suite to run (mlton or parallel_bench, required)" >&2
  echo "  --base_nick <nick>              Base nickname for output results (required)" >&2
  echo "  -h, --help                      Show this help message" >&2
  exit 1
}

COMPILER=""
SUITE=""
BASE_NICK=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --compiler)
      if [[ -n "${2:-}" && "$2" != --* ]]; then
        COMPILER="$2"
        shift 2
      else
        echo "Error: --compiler requires an argument." >&2
        usage
      fi
      ;;
    --compiler=*)
      COMPILER="${1#*=}"
      shift
      ;;
    --suite)
      if [[ -n "${2:-}" && "$2" != --* ]]; then
        SUITE="$2"
        shift 2
      else
        echo "Error: --suite requires an argument." >&2
        usage
      fi
      ;;
    --suite=*)
      SUITE="${1#*=}"
      shift
      ;;
    --base_nick)
      if [[ -n "${2:-}" && "$2" != --* ]]; then
        BASE_NICK="$2"
        shift 2
      else
        echo "Error: --base_nick requires an argument." >&2
        usage
      fi
      ;;
    --base_nick=*)
      BASE_NICK="${1#*=}"
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

# Validate required arguments
if [[ -z "$COMPILER" ]]; then
  echo "Error: --compiler is required." >&2
  usage
fi

if [[ -z "$SUITE" ]]; then
  echo "Error: --suite is required." >&2
  usage
fi

if [[ -z "$BASE_NICK" ]]; then
  echo "Error: --base_nick is required." >&2
  usage
fi

# Dispatch based on compiler and suite
case "${COMPILER}:${SUITE}" in
  mlton:mlton)
    BENCH_SCRIPT="$HOME/code/mlton/benchmark/benchmark-new/run_all_experiments.sh"
    COPY_TYPE="mlton"
    ;;
  mlton:parallel_bench)
    BENCH_SCRIPT="$HOME/code/parallel-ml-bench/run_all_mlton.sh"
    COPY_TYPE="parallel_bench"
    ;;
  mpl:parallel_bench)
    BENCH_SCRIPT="$HOME/code/parallel-ml-bench/run_all_mpl.sh"
    COPY_TYPE="parallel_bench"
    ;;
  mpl:mlton)
    echo "Error: Unsupported combination: compiler 'mpl' does not support suite 'mlton'." >&2
    exit 1
    ;;
  *)
    echo "Error: Invalid compiler/suite combination: --compiler='$COMPILER', --suite='$SUITE'." >&2
    usage
    ;;
esac

if [[ ! -f "$BENCH_SCRIPT" ]]; then
  echo "Error: Benchmark script '$BENCH_SCRIPT' not found." >&2
  exit 1
fi

COPY_SCRIPT="$SCRIPT_DIR/copy_latest_results.sh"
if [[ ! -f "$COPY_SCRIPT" ]]; then
  echo "Error: Copy script '$COPY_SCRIPT' not found." >&2
  exit 1
fi

echo "=================================================="
echo "Running experiments for compiler='$COMPILER', suite='$SUITE', base_nick='$BASE_NICK'"
echo "Benchmark script: $BENCH_SCRIPT"
echo "=================================================="

"$BENCH_SCRIPT" --base_nick="$BASE_NICK"

echo "=================================================="
echo "Copying latest 4 $COPY_TYPE results"
echo "=================================================="

"$COPY_SCRIPT" --type="$COPY_TYPE" --count 4
