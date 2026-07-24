#!/usr/bin/env bash
set -euo pipefail

repo=/home/xuanyu/PROJECT/ziyu/blueknow/simulation
python_bin=${BLUEKNOW_PYTHON:-/home/xuanyu/miniconda3/envs/grs-pilot/bin/python}
indent_values=${BLUEKNOW_THICKNESS_INDENTS_MM:-"0.26 0.28"}
workers=${BLUEKNOW_SWEEP_WORKERS:-4}
np=${BLUEKNOW_CASE_NP:-4}
initial_gap_mm=${BLUEKNOW_INITIAL_GAP_MM:-0.30}
eyelid_material_scale=${BLUEKNOW_EYELID_MATERIAL_SCALE:-1.00}
cornea_material_scale=${BLUEKNOW_CORNEA_MATERIAL_SCALE:-0.75}
read -r -a indents_mm <<< "$indent_values"

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
run_root=${BLUEKNOW_RUN_ROOT:-/home/xuanyu/PROJECT/ziyu/blueknow-data/thickness_sweep/${timestamp}_${commit}_thickness_geometry_zero}

if [[ -d "$run_root" ]] && [[ -n "$(find "$run_root" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
    printf 'run root is not empty: %s\n' "$run_root" >&2
    exit 2
fi

mkdir -p "$run_root"
export BLUEKNOW_RUN_ROOT="$run_root"
printf 'RUN_ROOT=%s\n' "$run_root"
set +e
"$python_bin" "$repo/src/runners/run_indentation_sweep.py" \
    --profile thickness \
    --thickness-indents-mm "${indents_mm[@]}" \
    --initial-gap-mm "$initial_gap_mm" \
    --eyelid-material-scale "$eyelid_material_scale" \
    --cornea-material-scale "$cornea_material_scale" \
    --workers "$workers" \
    --np "$np"
solver_status=$?
"$python_bin" "$repo/src/postprocess/summarize_thickness_sweep.py" "$run_root"
summary_status=$?
set -e

if (( solver_status != 0 || summary_status != 0 )); then
    exit 1
fi
