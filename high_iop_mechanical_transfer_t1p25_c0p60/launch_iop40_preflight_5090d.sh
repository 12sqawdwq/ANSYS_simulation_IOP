#!/usr/bin/env bash
set -Eeuo pipefail

REPO=/home/xuanyu/PROJECT/ziyu/blueknow/simulation
PY=/home/xuanyu/miniconda3/envs/grs-pilot/bin/python
ANSYS=/ansys_inc/v252/ansys/bin/ansys252
DATA_BASE=/home/xuanyu/PROJECT/ziyu/blueknow-data/high_iop_mechanical_transfer_t1p25_c0p60
SCRIPT_REL=high_iop_mechanical_transfer_t1p25_c0p60/launch_iop40_preflight_5090d.sh
SPEC_REL=high_iop_mechanical_transfer_t1p25_c0p60/run_spec.json
POST_REL=high_iop_mechanical_transfer_t1p25_c0p60/postprocess_iop40_preflight.py
EXTRACT_REL=src/postprocess/extract_geometry_zero_state.py

usage() {
  cat <<'EOF'
Usage:
  launch_iop40_preflight_5090d.sh --detach [RUN_ROOT]
  launch_iop40_preflight_5090d.sh --run RUN_ROOT

--detach creates a new external data directory and starts a nohup controller.
--run is the blocking controller mode used by --detach.
EOF
}

require_environment() {
  test "$(hostname -s)" = "xuanyu" || { echo "ERROR: this launcher is restricted to the 5090d host (hostname xuanyu)" >&2; return 1; }
  test -x "$PY" || { echo "ERROR: missing Python: $PY" >&2; return 1; }
  test -x "$ANSYS" || { echo "ERROR: missing ANSYS: $ANSYS" >&2; return 1; }
  test -f "$REPO/$SPEC_REL" || { echo "ERROR: missing run spec" >&2; return 1; }
  "$PY" -c 'import numpy, scipy, PIL' >/dev/null
  local dirty
  dirty=$(git -C "$REPO" status --porcelain)
  test -z "$dirty" || { echo "ERROR: formal preflight requires a clean server worktree" >&2; return 1; }
  local available_kb
  available_kb=$(df -Pk "$DATA_BASE" 2>/dev/null | awk 'NR==2 {print $4}') || true
  if [[ -n "${available_kb:-}" ]] && (( available_kb < 60 * 1024 * 1024 )); then
    echo "ERROR: less than 60 GiB available under data root" >&2
    return 1
  fi
}

write_launch_metadata() {
  local root=$1
  "$PY" - "$REPO" "$root" "$PY" "$ANSYS" <<'PY'
import hashlib, json, platform, socket, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
repo, root, python_bin, ansys_bin = map(Path, sys.argv[1:])
files = [
    repo / "high_iop_mechanical_transfer_t1p25_c0p60/run_spec.json",
    repo / "high_iop_mechanical_transfer_t1p25_c0p60/launch_iop40_preflight_5090d.sh",
    repo / "high_iop_mechanical_transfer_t1p25_c0p60/postprocess_iop40_preflight.py",
    repo / "src/runners/run_indentation_sweep.py",
    repo / "src/postprocess/extract_geometry_zero_state.py",
    repo / "models/apdl/param_eye_sweep.mac",
]
def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()
commit = subprocess.run(
    ["git", "-C", str(repo), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
).stdout.strip()
payload = {
    "started_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "host": socket.gethostname(),
    "platform": platform.platform(),
    "git_commit": commit,
    "git_dirty": False,
    "python_executable": str(python_bin),
    "ansys_executable": str(ansys_bin),
    "phase": "phase1_iop40_preflight",
    "file_sha256": {str(path.relative_to(repo)): sha256(path) for path in files},
}
(root / "launch_metadata.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
PY
}

run_controller() {
  local root=$1
  require_environment
  test -d "$root" || { echo "ERROR: missing run root: $root" >&2; return 1; }
  test ! -e "$root/run" || { echo "ERROR: run output already exists: $root/run" >&2; return 1; }
  local state="$root/controller_state.txt"
  log() { printf '%s %s\n' "$(date -Is)" "$*" | tee -a "$state"; }
  write_launch_metadata "$root"
  log "START phase=iop40_preflight pid=$$ commit=$(git -C "$REPO" rev-parse HEAD) np=8 max_attempts=2"

  set +e
  "$PY" "$REPO/src/runners/run_indentation_sweep.py" \
    --eyelid-thicknesses 1.25 \
    --thickness-indents-mm 0.28 \
    --run-root "$root/run" \
    --workers 1 --np 8 --timeout-seconds 3600 --retry-count 1 \
    --mesh-size-mm 0.30 --iop-mmhg 40 \
    --eyelid-material-scale 1.00 --cornea-material-scale 0.75 \
    --initial-gap-mm 0.30 --view-policy all \
    --ansys-bin "$ANSYS" \
    > "$root/runner.log" 2>&1
  local solver_rc=$?
  set -e
  log "SOLVER_FINISHED rc=$solver_rc"
  if (( solver_rc != 0 )); then
    log "PREFLIGHT_FAILED stage=solver"
    return "$solver_rc"
  fi

  mkdir -p "$root/analysis"
  "$PY" "$REPO/$EXTRACT_REL" \
    --manifest "$root/run/run_manifest.csv" \
    --eyelid-thickness-mm 1.25 --iop-mmhg 40 \
    --target-indent-mm 0.26 --source-indent-mm 0.28 \
    --output-dir "$root/analysis/primary_state_0p26" \
    --ansys-bin "$ANSYS" --np 1 --timeout-seconds 900 \
    --max-indent-error-mm 0.001 \
    > "$root/analysis/extract_0p26.log" 2>&1
  log "PRIMARY_STATE_EXTRACTED"

  "$PY" "$REPO/$EXTRACT_REL" \
    --manifest "$root/run/run_manifest.csv" \
    --eyelid-thickness-mm 1.25 --iop-mmhg 40 \
    --target-indent-mm 0.28 --source-indent-mm 0.28 \
    --output-dir "$root/analysis/sensitivity_state_0p28" \
    --ansys-bin "$ANSYS" --np 1 --timeout-seconds 900 \
    --max-indent-error-mm 0.000001 \
    > "$root/analysis/extract_0p28.log" 2>&1
  log "SENSITIVITY_STATE_EXTRACTED"

  "$PY" "$REPO/$POST_REL" \
    --run-root "$root" \
    --state-json "$root/analysis/primary_state_0p26/geometry_state.json" \
    --sensitivity-state-json "$root/analysis/sensitivity_state_0p28/geometry_state.json" \
    --run-spec "$root/run_spec.json" \
    > "$root/analysis/preflight_summary.log" 2>&1
  log "PREFLIGHT_PASSED analysis=$root/analysis/iop40_preflight_summary.json"
}

mode=${1:-}
case "$mode" in
  --detach)
    require_environment
    mkdir -p "$DATA_BASE"
    commit=$(git -C "$REPO" rev-parse HEAD)
    root=${2:-$DATA_BASE/$(date -u +%Y%m%dT%H%M%SZ)_${commit:0:8}_iop40_preflight}
    if [[ -e "$root" ]]; then
      echo "ERROR: run root already exists: $root" >&2
      exit 1
    fi
    mkdir -p "$root"
    cp "$REPO/$SPEC_REL" "$root/run_spec.json"
    nohup "$REPO/$SCRIPT_REL" --run "$root" > "$root/controller.nohup.log" 2>&1 &
    pid=$!
    printf '%s\n' "$pid" > "$root/controller.pid"
    printf 'RUN_ROOT=%s\nPID=%s\n' "$root" "$pid"
    ;;
  --run)
    [[ $# -eq 2 ]] || { usage >&2; exit 2; }
    root=$(realpath "$2")
    trap 'rc=$?; printf "%s CONTROLLER_EXIT rc=%s\n" "$(date -Is)" "$rc" | tee -a "$root/controller_state.txt"' EXIT
    run_controller "$root"
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
