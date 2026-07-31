#!/usr/bin/env bash
set -Eeuo pipefail

REPO=/home/xuanyu/PROJECT/ziyu/blueknow/simulation
PY=/home/xuanyu/miniconda3/envs/grs-pilot/bin/python
DATA_BASE=/home/xuanyu/PROJECT/ziyu/blueknow-data/high_iop_mechanical_transfer_t1p25_c0p60/interface_force_integrals
SPEC_REL=high_iop_mechanical_transfer_t1p25_c0p60/run_spec_interface_force_integrals.json
POST_REL=high_iop_mechanical_transfer_t1p25_c0p60/postprocess_interface_force_integrals.py
SCRIPT_REL=high_iop_mechanical_transfer_t1p25_c0p60/launch_interface_force_integrals_5090d.sh

require_environment() {
  test "$(hostname -s)" = "xuanyu" || { echo "ERROR: restricted to 5090d" >&2; return 1; }
  test -x "$PY" || { echo "ERROR: Python is missing" >&2; return 1; }
  test -f "$REPO/$SPEC_REL" && test -f "$REPO/$POST_REL" || { echo "ERROR: integration files missing" >&2; return 1; }
  test -z "$(git -C "$REPO" status --porcelain)" || { echo "ERROR: formal postprocessing requires a clean worktree" >&2; return 1; }
}

run_controller() {
  local root=$1
  require_environment
  mkdir -p "$root"
  cp "$REPO/$SPEC_REL" "$root/run_spec_interface_force_integrals.json"
  "$PY" - "$REPO" "$root" <<'PY'
import hashlib,json,socket,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
repo,root=map(Path,sys.argv[1:])
files=[
 repo/'models/apdl/post_contact_force_integrals.mac',
 repo/'src/postprocess/extract_contact_force_integrals.py',
 repo/'high_iop_mechanical_transfer_t1p25_c0p60/run_spec_interface_force_integrals.json',
 repo/'high_iop_mechanical_transfer_t1p25_c0p60/postprocess_interface_force_integrals.py',
 repo/'high_iop_mechanical_transfer_t1p25_c0p60/launch_interface_force_integrals_5090d.sh',
]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
commit=subprocess.run(['git','-C',str(repo),'rev-parse','HEAD'],check=True,capture_output=True,text=True).stdout.strip()
payload={'started_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds'),'host':socket.gethostname(),'git_commit':commit,'git_dirty':False,'phase':'rst_contact_force_vector_integrals_0_to_50_step2p5','file_sha256':{str(p.relative_to(repo)):sha(p) for p in files}}
(root/'launch_metadata.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
PY
  printf '%s START commit=%s\n' "$(date -Is)" "$(git -C "$REPO" rev-parse HEAD)" | tee "$root/controller_state.txt"
  "$PY" "$REPO/$POST_REL" \
    --repo "$REPO" \
    --run-spec "$root/run_spec_interface_force_integrals.json" \
    --output-root "$root" \
    > "$root/controller.log" 2>&1
  printf '%s CONTACT_FORCE_INTEGRALS_PASSED\n' "$(date -Is)" | tee -a "$root/controller_state.txt"
}

mode=${1:-}
case "$mode" in
  --detach)
    require_environment
    commit=$(git -C "$REPO" rev-parse HEAD)
    root=${2:-$DATA_BASE/$(date -u +%Y%m%dT%H%M%SZ)_${commit:0:8}_contact_vectors}
    test ! -e "$root" || { echo "ERROR: output exists: $root" >&2; exit 1; }
    mkdir -p "$root"
    nohup "$REPO/$SCRIPT_REL" --run "$root" > "$root/controller.nohup.log" 2>&1 &
    pid=$!
    echo "$pid" > "$root/controller.pid"
    printf 'RUN_ROOT=%s\nPID=%s\n' "$root" "$pid"
    ;;
  --run)
    [[ $# -eq 2 ]] || exit 2
    root=$(realpath "$2")
    trap 'rc=$?; printf "%s CONTROLLER_EXIT rc=%s\n" "$(date -Is)" "$rc" | tee -a "$root/controller_state.txt"' EXIT
    run_controller "$root"
    ;;
  *)
    echo "Usage: $0 --detach [RUN_ROOT] | --run RUN_ROOT" >&2
    exit 2
    ;;
esac
