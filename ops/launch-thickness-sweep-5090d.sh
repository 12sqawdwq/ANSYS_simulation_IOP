#!/usr/bin/env bash
set -euo pipefail

repo=/home/xuanyu/PROJECT/ziyu/blueknow/simulation
python_bin=${BLUEKNOW_PYTHON:-/home/xuanyu/miniconda3/envs/grs-pilot/bin/python}

if [[ ! -x "$python_bin" ]]; then
    printf 'Python interpreter is not executable: %s\n' "$python_bin" >&2
    exit 2
fi

if ! "$python_bin" -c 'import PIL' >/dev/null 2>&1; then
    printf 'Python environment must provide Pillow: %s\n' "$python_bin" >&2
    exit 2
fi

commit=$(git -C "$repo" rev-parse --short=8 HEAD)
timestamp=$(date -u +%Y%m%dT%H%M%SZ)
run_root=${BLUEKNOW_RUN_ROOT:-/home/xuanyu/PROJECT/ziyu/blueknow-data/thickness_sweep/${timestamp}_${commit}_thickness}

if [[ -d "$run_root" ]] && [[ -n "$(find "$run_root" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
    printf 'run root is not empty: %s\n' "$run_root" >&2
    exit 2
fi

mkdir -p "$run_root"
export BLUEKNOW_RUN_ROOT="$run_root"
printf 'RUN_ROOT=%s\n' "$run_root"
set +e
"$python_bin" "$repo/src/runners/run_indentation_sweep.py" --profile thickness --workers 4 --np 4
solver_status=$?
"$python_bin" "$repo/src/postprocess/summarize_thickness_sweep.py" "$run_root"
summary_status=$?
set -e

if (( solver_status != 0 || summary_status != 0 )); then
    exit 1
fi
