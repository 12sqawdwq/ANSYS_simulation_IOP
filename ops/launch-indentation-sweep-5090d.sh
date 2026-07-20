#!/usr/bin/env bash
set -euo pipefail

repo=/home/xuanyu/PROJECT/ziyu/blueknow/simulation
run_root=/home/xuanyu/PROJECT/ziyu/blueknow-data/indentation_sweep_20260720

mkdir -p "$run_root"
export BLUEKNOW_RUN_ROOT="$run_root"
python3 "$repo/src/runners/run_indentation_sweep.py" --workers 4 --np 4
python3 "$repo/src/postprocess/summarize_indentation_sweep.py" "$run_root"
