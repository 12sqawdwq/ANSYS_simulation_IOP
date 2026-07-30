#!/usr/bin/env bash
set -Eeuo pipefail

REPO=/home/xuanyu/PROJECT/ziyu/blueknow/simulation
PY=/home/xuanyu/miniconda3/envs/grs-pilot/bin/python
ANSYS=/ansys_inc/v252/ansys/bin/ansys252
DATA_BASE=/home/xuanyu/PROJECT/ziyu/blueknow-data/high_iop_mechanical_transfer_t1p25_c0p60
SOURCE40=/home/xuanyu/PROJECT/ziyu/blueknow-data/high_iop_mechanical_transfer_t1p25_c0p60/20260730T040825Z_bdca48fe_iop40_preflight
SCRIPT_REL=high_iop_mechanical_transfer_t1p25_c0p60/launch_full_experiment_5090d.sh
SPEC_REL=high_iop_mechanical_transfer_t1p25_c0p60/run_spec_full.json
POST_REL=high_iop_mechanical_transfer_t1p25_c0p60/postprocess_full_high_iop.py
EXTRACT_REL=src/postprocess/extract_geometry_zero_state.py

usage() {
  printf '%s\n' \
    'Usage:' \
    '  launch_full_experiment_5090d.sh --detach [RUN_ROOT]' \
    '  launch_full_experiment_5090d.sh --run RUN_ROOT'
}

require_environment() {
  test "$(hostname -s)" = "xuanyu" || { echo "ERROR: restricted to 5090d (hostname xuanyu)" >&2; return 1; }
  test -x "$PY" && test -x "$ANSYS" || { echo "ERROR: required Python or ANSYS is missing" >&2; return 1; }
  test -f "$REPO/$SPEC_REL" && test -f "$REPO/$POST_REL" || { echo "ERROR: full experiment files are missing" >&2; return 1; }
  test -f "$SOURCE40/analysis/iop40_preflight_summary.json" || { echo "ERROR: accepted 40 mmHg preflight is missing" >&2; return 1; }
  "$PY" -c 'import numpy, scipy, PIL' >/dev/null
  test -z "$(git -C "$REPO" status --porcelain)" || { echo "ERROR: formal run requires a clean server worktree" >&2; return 1; }
  mkdir -p "$DATA_BASE"
  local available_kb
  available_kb=$(df -Pk "$DATA_BASE" | awk 'NR==2 {print $4}')
  (( available_kb >= 100 * 1024 * 1024 )) || { echo "ERROR: less than 100 GiB available" >&2; return 1; }
}

write_launch_metadata() {
  local root=$1
  "$PY" - "$REPO" "$root" "$PY" "$ANSYS" "$SOURCE40" <<'PY'
import hashlib, json, platform, socket, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
repo, root, python_bin, ansys_bin, source40 = map(Path, sys.argv[1:])
files = [
    repo / "high_iop_mechanical_transfer_t1p25_c0p60/run_spec_full.json",
    repo / "high_iop_mechanical_transfer_t1p25_c0p60/launch_full_experiment_5090d.sh",
    repo / "high_iop_mechanical_transfer_t1p25_c0p60/postprocess_full_high_iop.py",
    repo / "src/runners/run_indentation_sweep.py",
    repo / "src/postprocess/extract_geometry_zero_state.py",
    repo / "models/apdl/param_eye_sweep.mac",
]
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
commit=subprocess.run(['git','-C',str(repo),'rev-parse','HEAD'],check=True,capture_output=True,text=True).stdout.strip()
payload={
 'started_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds'),
 'host':socket.gethostname(),'platform':platform.platform(),'git_commit':commit,'git_dirty':False,
 'python_executable':str(python_bin),'ansys_executable':str(ansys_bin),
 'phase':'full_high_iop_matrix_after_iop40_preflight','reused_iop40_root':str(source40),
 'new_pressures_mmhg':[0,20,25,30,35],'maximum_parallel_cases':2,'np_per_case':8,
 'file_sha256':{str(p.relative_to(repo)):sha(p) for p in files},
}
(root/'launch_metadata.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
PY
}

run_pressure() {
  local root=$1 p=$2
  "$PY" "$REPO/src/runners/run_indentation_sweep.py" \
    --eyelid-thicknesses 1.25 --thickness-indents-mm 0.28 \
    --run-root "$root/iop${p}/run" --workers 1 --np 8 \
    --timeout-seconds 3600 --retry-count 1 --mesh-size-mm 0.30 \
    --iop-mmhg "$p" --eyelid-material-scale 1.00 --cornea-material-scale 0.75 \
    --initial-gap-mm 0.30 --view-policy none --ansys-bin "$ANSYS" \
    > "$root/iop${p}.runner.log" 2>&1
}

run_wave() {
  local root=$1 first=$2 second=${3:-}
  local p1 p2 rc1 rc2
  run_pressure "$root" "$first" & p1=$!
  if [[ -n "$second" ]]; then run_pressure "$root" "$second" & p2=$!; else p2=''; fi
  set +e
  wait "$p1"; rc1=$?
  if [[ -n "$p2" ]]; then wait "$p2"; rc2=$?; else rc2=0; fi
  set -e
  printf '%s WAVE_FINISHED pressures=%s%s rc=%s,%s\n' "$(date -Is)" "$first" "${second:+,$second}" "$rc1" "$rc2" | tee -a "$root/controller_state.txt"
  (( rc1 == 0 && rc2 == 0 ))
}

extract_state() {
  local root=$1 p=$2 target=$3 label=$4 tolerance=$5
  "$PY" "$REPO/$EXTRACT_REL" \
    --manifest "$root/iop${p}/run/run_manifest.csv" \
    --eyelid-thickness-mm 1.25 --iop-mmhg "$p" \
    --target-indent-mm "$target" --source-indent-mm 0.28 \
    --output-dir "$root/states/iop${p}/$label" \
    --ansys-bin "$ANSYS" --np 1 --timeout-seconds 900 \
    --max-indent-error-mm "$tolerance" \
    > "$root/states/iop${p}/${label}.log" 2>&1
}

run_controller() {
  local root=$1 state="$1/controller_state.txt"
  require_environment
  test -d "$root" || { echo "ERROR: missing root $root" >&2; return 1; }
  for p in 0 20 25 30 35; do test ! -e "$root/iop$p" || { echo "ERROR: output exists for IOP $p" >&2; return 1; }; done
  write_launch_metadata "$root"
  printf '%s START commit=%s pressures=0,20,25,30,35 reused=40 workers=2 np=8\n' "$(date -Is)" "$(git -C "$REPO" rev-parse HEAD)" | tee -a "$state"

  run_wave "$root" 0 35
  run_wave "$root" 20 30
  run_wave "$root" 25
  printf '%s ALL_NEW_SOLVERS_COMPLETED\n' "$(date -Is)" | tee -a "$state"

  mkdir -p "$root/states"
  for p in 0 20 25 30 35; do
    mkdir -p "$root/states/iop${p}"
    extract_state "$root" "$p" 0.26 primary_0p26 0.001
    extract_state "$root" "$p" 0.28 sensitivity_0p28 0.000001
    printf '%s STATES_EXTRACTED iop=%s\n' "$(date -Is)" "$p" | tee -a "$state"
  done
  mkdir -p "$root/states/iop40"
  cp "$SOURCE40/analysis/primary_state_0p26/geometry_state.json" "$root/states/iop40/primary_0p26_geometry_state.json"
  cp "$SOURCE40/analysis/sensitivity_state_0p28/geometry_state.json" "$root/states/iop40/sensitivity_0p28_geometry_state.json"
  printf '%s IOP40_STATES_PROMOTED\n' "$(date -Is)" | tee -a "$state"

  mkdir -p "$root/analysis"
  "$PY" "$REPO/$POST_REL" --run-root "$root" --run-spec "$root/run_spec_full.json" \
    > "$root/analysis/full_summary.log" 2>&1
  printf '%s FULL_CAMPAIGN_PASSED analysis=%s\n' "$(date -Is)" "$root/analysis/high_iop_full_summary.json" | tee -a "$state"
}

mode=${1:-}
case "$mode" in
  --detach)
    require_environment
    commit=$(git -C "$REPO" rev-parse HEAD)
    root=${2:-$DATA_BASE/$(date -u +%Y%m%dT%H%M%SZ)_${commit:0:8}_full_matrix}
    test ! -e "$root" || { echo "ERROR: root exists: $root" >&2; exit 1; }
    mkdir -p "$root"
    cp "$REPO/$SPEC_REL" "$root/run_spec_full.json"
    nohup "$REPO/$SCRIPT_REL" --run "$root" > "$root/controller.nohup.log" 2>&1 &
    pid=$!; printf '%s\n' "$pid" > "$root/controller.pid"
    printf 'RUN_ROOT=%s\nPID=%s\n' "$root" "$pid"
    ;;
  --run)
    [[ $# -eq 2 ]] || { usage >&2; exit 2; }
    root=$(realpath "$2")
    trap 'rc=$?; printf "%s CONTROLLER_EXIT rc=%s\n" "$(date -Is)" "$rc" | tee -a "$root/controller_state.txt"' EXIT
    run_controller "$root"
    ;;
  *) usage >&2; exit 2 ;;
esac
