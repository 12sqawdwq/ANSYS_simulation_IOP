#!/usr/bin/env bash
set -euo pipefail

repo=/home/xuanyu/PROJECT/ziyu/blueknow/simulation
python_bin=${BLUEKNOW_PYTHON:-/home/xuanyu/miniconda3/envs/grs-pilot/bin/python}
workers=${BLUEKNOW_SWEEP_WORKERS:-4}
np=${BLUEKNOW_CASE_NP:-4}

if [[ ! -x "$python_bin" ]]; then
    printf 'Python interpreter is not executable: %s\n' "$python_bin" >&2
    exit 2
fi

if [[ -n "$(git -C "$repo" status --porcelain)" ]]; then
    printf 'Formal calibration requires a clean Git worktree: %s\n' "$repo" >&2
    exit 2
fi

commit=$(git -C "$repo" rev-parse --short=8 HEAD)
timestamp=$(date -u +%Y%m%dT%H%M%SZ)
run_root=${BLUEKNOW_RUN_ROOT:-/home/xuanyu/PROJECT/ziyu/blueknow-data/thickness_calibration/${timestamp}_${commit}_calibration_0p26}

if [[ -d "$run_root" ]] && [[ -n "$(find "$run_root" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
    printf 'Run root is not empty: %s\n' "$run_root" >&2
    exit 2
fi

mkdir -p "$run_root"
nohup "$python_bin" "$repo/src/runners/run_thickness_calibration.py" \
    --run-root "$run_root" --workers "$workers" --np "$np" \
    >"$run_root/controller.log" 2>&1 </dev/null &
pid=$!
printf '%s\n' "$pid" >"$run_root/controller.pid"
printf 'RUN_ROOT=%s\nCONTROLLER_PID=%s\n' "$run_root" "$pid"
