#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  echo "Usage: $0 --compiler=[mlton|mpl|all] --suite=[mlton|parallel_bench|all] [--flavors=<flavors>] --base_nick=<nick> [--pre-flatten-recursive-steps=<N>] [--dry-run]" >&2
  echo "" >&2
  echo "Options:" >&2
  echo "  --compiler <mlton|mpl|all>          Compiler to use (mlton, mpl, or all, required)" >&2
  echo "  --suite <mlton|parallel_bench|all>  Benchmark suite to run (mlton, parallel_bench, or all, required)" >&2
  echo "  --flavors <flavors>                 Comma-separated list of flavors to benchmark (optional)" >&2
  echo "  --base_nick <nick>                  Base nickname for output results (required)" >&2
  echo "  --pre-flatten-recursive-steps <N>   Override recursive pre-flattening steps limit (e.g. 0)" >&2
  echo "  --dry-run                           Show commands without executing" >&2
  echo "  -h, --help                          Show this help message" >&2
  exit 1
}

COMPILER=""
SUITE=""
FLAVORS=""
BASE_NICK=""
PRE_FLATTEN_RECURSIVE_STEPS="${PRE_FLATTEN_RECURSIVE_STEPS:-}"
DRY_RUN=false

# Also check EXTRA_SHARED_FLAGS or EXTRA_FLAGS in env for pre-flatten-recursive-steps
if [[ -z "$PRE_FLATTEN_RECURSIVE_STEPS" && "${EXTRA_SHARED_FLAGS:-}" =~ -pre-flatten-recursive-steps[[:space:]=]+([0-9]+) ]]; then
  PRE_FLATTEN_RECURSIVE_STEPS="${BASH_REMATCH[1]}"
fi
if [[ -z "$PRE_FLATTEN_RECURSIVE_STEPS" && "${EXTRA_FLAGS:-}" =~ -pre-flatten-recursive-steps[[:space:]=]+([0-9]+) ]]; then
  PRE_FLATTEN_RECURSIVE_STEPS="${BASH_REMATCH[1]}"
fi

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
    --flavors)
      if [[ -n "${2:-}" && "$2" != --* ]]; then
        FLAVORS="$2"
        shift 2
      else
        echo "Error: --flavors requires an argument." >&2
        usage
      fi
      ;;
    --flavors=*)
      FLAVORS="${1#*=}"
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
    --pre-flatten-recursive-steps|--pre_flatten_recursive_steps)
      if [[ -n "${2:-}" && "$2" != --* ]]; then
        PRE_FLATTEN_RECURSIVE_STEPS="$2"
        shift 2
      else
        echo "Error: $1 requires an argument." >&2
        usage
      fi
      ;;
    --pre-flatten-recursive-steps=*|--pre_flatten_recursive_steps=*)
      PRE_FLATTEN_RECURSIVE_STEPS="${1#*=}"
      shift
      ;;
    --dry-run|--dry_run)
      DRY_RUN=true
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

COPY_SCRIPT="$SCRIPT_DIR/copy_latest_results.sh"
if [[ ! -f "$COPY_SCRIPT" ]]; then
  echo "Error: Copy script '$COPY_SCRIPT' not found." >&2
  exit 1
fi

COMPILERS=()
if [[ "$COMPILER" == "all" ]]; then
  COMPILERS=("mlton" "mpl")
elif [[ "$COMPILER" == "mlton" || "$COMPILER" == "mpl" ]]; then
  COMPILERS=("$COMPILER")
else
  echo "Error: Invalid --compiler='$COMPILER'. Must be 'mlton', 'mpl', or 'all'." >&2
  usage
fi

SUITES=()
if [[ "$SUITE" == "all" ]]; then
  SUITES=("mlton" "parallel_bench")
elif [[ "$SUITE" == "mlton" || "$SUITE" == "parallel_bench" ]]; then
  SUITES=("$SUITE")
else
  echo "Error: Invalid --suite='$SUITE'. Must be 'mlton', 'parallel_bench', or 'all'." >&2
  usage
fi

WRAPPER_DIR="$SCRIPT_DIR/.wrappers"
cleanup_wrappers() {
  rm -rf "$WRAPPER_DIR"
}
trap cleanup_wrappers EXIT

setup_wrappers() {
  local steps="$1"
  local real_home="${REAL_HOME:-$HOME}"

  mkdir -p "$WRAPPER_DIR/code/mlton/build/bin" "$WRAPPER_DIR/code/mpl/build/bin"

  cat << EOF > "$WRAPPER_DIR/code/mlton/build/bin/mlton"
#!/bin/bash
new_args=()
prev=""
for arg in "\$@"; do
  if [ "\$prev" = "-pre-flatten-recursive-steps" ]; then
    new_args+=("$steps")
  elif [[ "\$arg" == -pre-flatten-recursive-steps=* ]]; then
    new_args+=("-pre-flatten-recursive-steps=$steps")
  else
    new_args+=("\$arg")
  fi
  prev="\$arg"
done
exec "$real_home/code/mlton/build/bin/mlton" "\${new_args[@]}"
EOF
  chmod +x "$WRAPPER_DIR/code/mlton/build/bin/mlton"

  cat << EOF > "$WRAPPER_DIR/code/mpl/build/bin/mpl"
#!/bin/bash
new_args=()
prev=""
for arg in "\$@"; do
  if [ "\$prev" = "-pre-flatten-recursive-steps" ]; then
    new_args+=("$steps")
  elif [[ "\$arg" == -pre-flatten-recursive-steps=* ]]; then
    new_args+=("-pre-flatten-recursive-steps=$steps")
  else
    new_args+=("\$arg")
  fi
  prev="\$arg"
done
exec "$real_home/code/mpl/build/bin/mpl" "\${new_args[@]}"
EOF
  chmod +x "$WRAPPER_DIR/code/mpl/build/bin/mpl"
}

for c in "${COMPILERS[@]}"; do
  for s in "${SUITES[@]}"; do
    if [[ "$c" == "mpl" && "$s" == "mlton" ]]; then
      echo "Notice: Skipping combination compiler='mpl', suite='mlton' (unsupported)."
      continue
    fi

    # Determine default flavors and scripts
    case "${c}:${s}" in
      mlton:mlton)
        BENCH_SCRIPT="$HOME/code/mlton/benchmark/benchmark-new/run_all_experiments.sh"
        COPY_TYPE="mlton"
        if [[ -n "$PRE_FLATTEN_RECURSIVE_STEPS" ]]; then
          DEFAULT_FLAVORS="con,tuple"
        else
          DEFAULT_FLAVORS="aos,soa,con,tuple"
        fi
        ;;
      mlton:parallel_bench)
        BENCH_SCRIPT="$HOME/code/parallel-ml-bench/run_all_mlton.sh"
        COPY_TYPE="parallel_bench"
        if [[ -n "$PRE_FLATTEN_RECURSIVE_STEPS" ]]; then
          DEFAULT_FLAVORS="con,tuple"
        else
          DEFAULT_FLAVORS="aos,soa,conapp,tuple"
        fi
        ;;
      mpl:parallel_bench)
        BENCH_SCRIPT="$HOME/code/parallel-ml-bench/run_all_mpl.sh"
        COPY_TYPE="parallel_bench"
        if [[ -n "$PRE_FLATTEN_RECURSIVE_STEPS" ]]; then
          DEFAULT_FLAVORS="con,tuple"
        else
          DEFAULT_FLAVORS="aos,soa,conapp,tuple"
        fi
        ;;
    esac

    CUR_FLAVORS="${FLAVORS:-$DEFAULT_FLAVORS}"
    NUM_COMMAS="${CUR_FLAVORS//[^,]/}"
    NUM_FILES=$((${#NUM_COMMAS} + 1))

    if [[ ! -f "$BENCH_SCRIPT" ]]; then
      echo "Error: Benchmark script '$BENCH_SCRIPT' not found." >&2
      exit 1
    fi

    echo "=================================================="
    echo "Running experiments for compiler='$c', suite='$s', base_nick='$BASE_NICK', flavors='$CUR_FLAVORS'"
    if [[ -n "$PRE_FLATTEN_RECURSIVE_STEPS" ]]; then
      echo "Recursive steps override: -pre-flatten-recursive-steps $PRE_FLATTEN_RECURSIVE_STEPS"
    fi
    echo "=================================================="

    if [[ "$s" == "mlton" && "$c" == "mlton" ]]; then
      if [[ -n "$PRE_FLATTEN_RECURSIVE_STEPS" ]]; then
        # Use run_experiments.py directly to ensure extra_shared_flags is appended after CONFIG_FLAGS
        IFS=',' read -ra FLAVOR_ARRAY <<< "$CUR_FLAVORS"
        for flavor in "${FLAVOR_ARRAY[@]}"; do
          flavor="${flavor//[[:space:]]/}"
          config_flavor="$flavor"
          if [[ "$config_flavor" == "con" ]]; then
            config_flavor="conapp"
          fi
          echo "Running MLton experiment for flavor '$flavor' (config: $config_flavor, recursive steps: $PRE_FLATTEN_RECURSIVE_STEPS)..."
          if [[ "$DRY_RUN" == "true" ]]; then
            echo "[DRY-RUN] python3 $HOME/code/mlton/benchmark/benchmark-new/run_experiments.py --test_config=$config_flavor --name=test_${flavor}_flatten_${BASE_NICK} --extra_shared_flags=\"-pre-flatten-recursive-steps $PRE_FLATTEN_RECURSIVE_STEPS\""
          else
            python3 "$HOME/code/mlton/benchmark/benchmark-new/run_experiments.py" \
              --test_config="$config_flavor" \
              --name="test_${flavor}_flatten_${BASE_NICK}" \
              --extra_shared_flags="-pre-flatten-recursive-steps $PRE_FLATTEN_RECURSIVE_STEPS"
          fi
        done
      else
        if [[ "$DRY_RUN" == "true" ]]; then
          echo "[DRY-RUN] $BENCH_SCRIPT --base_nick=$BASE_NICK --flavors=$CUR_FLAVORS"
        else
          "$BENCH_SCRIPT" --base_nick="$BASE_NICK" --flavors="$CUR_FLAVORS"
        fi
      fi
    else
      # parallel_bench (mlton or mpl)
      if [[ -n "$PRE_FLATTEN_RECURSIVE_STEPS" ]]; then
        setup_wrappers "$PRE_FLATTEN_RECURSIVE_STEPS"
        real_home="${REAL_HOME:-$HOME}"
        if [[ "$DRY_RUN" == "true" ]]; then
          echo "[DRY-RUN] HOME=$WRAPPER_DIR REAL_HOME=$real_home $BENCH_SCRIPT --base_nick=$BASE_NICK --flavors=$CUR_FLAVORS"
        else
          HOME="$WRAPPER_DIR" REAL_HOME="$real_home" "$BENCH_SCRIPT" --base_nick="$BASE_NICK" --flavors="$CUR_FLAVORS"
        fi
      else
        if [[ "$DRY_RUN" == "true" ]]; then
          echo "[DRY-RUN] $BENCH_SCRIPT --base_nick=$BASE_NICK --flavors=$CUR_FLAVORS"
        else
          "$BENCH_SCRIPT" --base_nick="$BASE_NICK" --flavors="$CUR_FLAVORS"
        fi
      fi
    fi

    if [[ "$DRY_RUN" != "true" ]]; then
      echo "=================================================="
      echo "Copying latest $NUM_FILES $COPY_TYPE results to $SCRIPT_DIR/data/"
      echo "=================================================="
      "$COPY_SCRIPT" --type="$COPY_TYPE" --count "$NUM_FILES"
    else
      echo "[DRY-RUN] $COPY_SCRIPT --type=$COPY_TYPE --count=$NUM_FILES"
    fi

  done
done

echo "=================================================="
echo "All requested experiments completed successfully."
echo "=================================================="
