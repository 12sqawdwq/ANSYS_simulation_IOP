#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SESSION_GUARD_SOURCE="${SESSION_GUARD_SOURCE:-$SCRIPT_DIR/session_guard.sh}"
# shellcheck source=session_guard.sh
source "$SESSION_GUARD_SOURCE"

REPO_ROOT="${REPO_ROOT:-/home/xuanyu/PROJECT/ziyu/blueknow/simulation}"
PYTHON_BIN="${PYTHON_BIN:-/home/xuanyu/miniconda3/envs/grs-pilot/bin/python}"
ANSYS_BIN="${ANSYS_BIN:-/ansys_inc/v252/ansys/bin/ansys252}"
RUNNER="$REPO_ROOT/src/runners/run_indentation_sweep.py"
CONFIG_SOURCE="${CONFIG_SOURCE:-$REPO_ROOT/thickness_mesh_independence/aggressive_refinement/config/experiment.json}"
BASELINE_SOURCE="${BASELINE_SOURCE:-$REPO_ROOT/config/model_baseline.json}"
BASELINE_READER_PYTHON="${BASELINE_READER_PYTHON:-/usr/bin/python3}"
THICKNESSES="${THICKNESSES:-}"
# One pressure per campaign is mandatory. IOP20 requires a new campaign after manual IOP0 QC.
PRESSURES="${PRESSURES:-0}"
NP_PER_CASE="${NP_PER_CASE:-4}"
CASE_TIMEOUT_SECONDS="${CASE_TIMEOUT_SECONDS:-86400}"
CAMPAIGN_DEADLINE_SECONDS="${CAMPAIGN_DEADLINE_SECONDS:-90000}"
MIN_AVAILABLE_MEMORY_GIB="${MIN_AVAILABLE_MEMORY_GIB:-90}"
MIN_FREE_DISK_GIB="${MIN_FREE_DISK_GIB:-150}"
ABORT_AVAILABLE_MEMORY_GIB="${ABORT_AVAILABLE_MEMORY_GIB:-30}"
ABORT_FREE_DISK_GIB="${ABORT_FREE_DISK_GIB:-100}"
MONITOR_INTERVAL_SECONDS="${MONITOR_INTERVAL_SECONDS:-10}"
SESSION_TERM_GRACE_SECONDS="${SESSION_TERM_GRACE_SECONDS:-30}"
SESSION_KILL_GRACE_SECONDS="${SESSION_KILL_GRACE_SECONDS:-10}"
: "${EXPECTED_COMMIT:?Set EXPECTED_COMMIT to the exact committed experiment source SHA.}"
: "${CAMPAIGN_ROOT:?Set CAMPAIGN_ROOT to a new path under blueknow-data.}"

actual_commit="$(git -C "$REPO_ROOT" rev-parse HEAD)"
if [[ "$actual_commit" != "$EXPECTED_COMMIT" ]]; then
  printf 'Unexpected Git commit: expected %s, got %s\n' "$EXPECTED_COMMIT" "$actual_commit" >&2
  exit 2
fi
if [[ -n "$(git -C "$REPO_ROOT" status --porcelain)" ]]; then
  printf 'Formal aggressive solve requires a clean 5090d worktree.\n' >&2
  exit 2
fi
if [[ -e "$CAMPAIGN_ROOT" ]]; then
  printf 'Campaign root already exists: %s\n' "$CAMPAIGN_ROOT" >&2
  exit 2
fi
if [[ ! -f "$CONFIG_SOURCE" ]]; then
  printf 'Experiment config is missing: %s\n' "$CONFIG_SOURCE" >&2
  exit 2
fi
if [[ ! -f "$BASELINE_SOURCE" || ! -x "$BASELINE_READER_PYTHON" ]]; then
  printf 'Global baseline config or its reader is missing.\n' >&2
  exit 2
fi
global_baseline_eyelid_thickness_mm="$(
  "$BASELINE_READER_PYTHON" -c \
    'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["canonical_baseline"]["eyelid_thickness_mm"])' \
    "$BASELINE_SOURCE"
)"
THICKNESSES="${THICKNESSES:-$global_baseline_eyelid_thickness_mm}"
if [[ ! -f "$SESSION_GUARD_SOURCE" ]]; then
  printf 'Session guard is missing: %s\n' "$SESSION_GUARD_SOURCE" >&2
  exit 2
fi
if [[ ! -x "$PYTHON_BIN" || ! -x "$ANSYS_BIN" ]]; then
  printf 'Python or ANSYS executable is missing.\n' >&2
  exit 2
fi
guard_require_user_systemd

read -r -a thickness_list <<< "$THICKNESSES"
read -r -a pressure_list <<< "$PRESSURES"
if [[ "${#thickness_list[@]}" -eq 0 || "${#pressure_list[@]}" -ne 1 ]]; then
  printf 'At least one thickness and exactly one pressure are required per campaign.\n' >&2
  exit 2
fi
for thickness in "${thickness_list[@]}"; do
  if [[ "$thickness" != "$global_baseline_eyelid_thickness_mm" \
        && "$thickness" != 1.6 && "$thickness" != 1.8 && "$thickness" != 2.0 ]]; then
    printf 'Unsupported thickness: %s\n' "$thickness" >&2
    exit 2
  fi
done
thickness_mode=explicit_thickness_override
if [[ "${#thickness_list[@]}" -eq 1 \
      && "${thickness_list[0]}" == "$global_baseline_eyelid_thickness_mm" ]]; then
  thickness_mode=global_baseline
fi
for pressure in "${pressure_list[@]}"; do
  if [[ "$pressure" != 0 && "$pressure" != 20 ]]; then
    printf 'Unsupported pressure: %s\n' "$pressure" >&2
    exit 2
  fi
done
for integer_name in NP_PER_CASE CASE_TIMEOUT_SECONDS CAMPAIGN_DEADLINE_SECONDS \
  MIN_AVAILABLE_MEMORY_GIB MIN_FREE_DISK_GIB ABORT_AVAILABLE_MEMORY_GIB \
  ABORT_FREE_DISK_GIB MONITOR_INTERVAL_SECONDS SESSION_TERM_GRACE_SECONDS \
  SESSION_KILL_GRACE_SECONDS; do
  value="${!integer_name}"
  if [[ ! "$value" =~ ^[1-9][0-9]*$ ]]; then
    printf '%s must be a positive integer, got %s\n' "$integer_name" "$value" >&2
    exit 2
  fi
done
if (( NP_PER_CASE > 4 )); then
  printf 'NP_PER_CASE must not exceed 4 for L010.\n' >&2
  exit 2
fi
if (( MIN_AVAILABLE_MEMORY_GIB <= ABORT_AVAILABLE_MEMORY_GIB \
      || MIN_FREE_DISK_GIB <= ABORT_FREE_DISK_GIB )); then
  printf 'Launch resource gates must be stricter than abort floors.\n' >&2
  exit 2
fi
if (( CASE_TIMEOUT_SECONDS > CAMPAIGN_DEADLINE_SECONDS )); then
  printf 'CASE_TIMEOUT_SECONDS must not exceed CAMPAIGN_DEADLINE_SECONDS.\n' >&2
  exit 2
fi

active_solver_processes="$(ps -u "$(id -un)" -o pid=,comm=,args= | awk \
  '$2 ~ /^(ansys[0-9]+|ansys\.e|mapdl|mpiexec|mpiexec\.hydra|hydra_pmi_proxy)$/ {print}')"
if [[ -n "$active_solver_processes" ]]; then
  printf 'Refusing launch because solver/MPI processes are already active:\n%s\n' \
    "$active_solver_processes" >&2
  exit 2
fi

resource_gate() {
  local available_kib free_disk_kib
  available_kib="$(awk '/MemAvailable:/ {print $2}' /proc/meminfo)"
  free_disk_kib="$(df -Pk "$(dirname "$CAMPAIGN_ROOT")" | awk 'NR==2 {print $4}')"
  if (( available_kib < MIN_AVAILABLE_MEMORY_GIB * 1024 * 1024 )); then
    printf 'Resource gate: %.2f GiB available memory is below %s GiB.\n' \
      "$(awk -v k="$available_kib" 'BEGIN {print k/1024/1024}')" \
      "$MIN_AVAILABLE_MEMORY_GIB" >&2
    return 1
  fi
  if (( free_disk_kib < MIN_FREE_DISK_GIB * 1024 * 1024 )); then
    printf 'Resource gate: %.2f GiB free disk is below %s GiB.\n' \
      "$(awk -v k="$free_disk_kib" 'BEGIN {print k/1024/1024}')" \
      "$MIN_FREE_DISK_GIB" >&2
    return 1
  fi
  printf 'resource_gate_utc,%s,mem_available_kib,%s,free_disk_kib,%s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$available_kib" "$free_disk_kib" \
    >> "$CAMPAIGN_ROOT/resource_gates.csv"
}

mkdir -p "$CAMPAIGN_ROOT"
cp "$0" "$CAMPAIGN_ROOT/launch_aggressive_anchor_5090d.sh"
cp "$SESSION_GUARD_SOURCE" "$CAMPAIGN_ROOT/session_guard.sh"
cp "$CONFIG_SOURCE" "$CAMPAIGN_ROOT/experiment.json"
cp "$BASELINE_SOURCE" "$CAMPAIGN_ROOT/model_baseline.json"
cp "$REPO_ROOT/models/apdl/param_eye_sweep.mac" "$CAMPAIGN_ROOT/param_eye_sweep.mac"
printf '%s\n' "$actual_commit" > "$CAMPAIGN_ROOT/source_git_commit.txt"
sha256sum "$BASELINE_SOURCE" > "$CAMPAIGN_ROOT/model_baseline.sha256"
printf 'utc,label,unit,event,detail\n' > "$CAMPAIGN_ROOT/session_guard_events.csv"
printf 'utc\tlabel\tunit\tevent\tprocess\n' > "$CAMPAIGN_ROOT/session_guard_processes.tsv"
printf 'utc,label,unit,event,status\n' > "$CAMPAIGN_ROOT/session_guard_unit_status.csv"
printf 'started_at_utc,%s\nglobal_baseline_eyelid_thickness_mm,%s\nthickness_mode,%s\nthicknesses_mm,%s\npressures_mmhg,%s\nnp_per_case,%s\ncase_timeout_seconds,%s\ncampaign_deadline_seconds,%s\nmin_available_memory_gib,%s\nabort_available_memory_gib,%s\nmin_free_disk_gib,%s\nabort_free_disk_gib,%s\nmonitor_interval_seconds,%s\nsession_term_grace_seconds,%s\nsession_kill_grace_seconds,%s\npressure_policy,exactly_one_pressure_per_campaign\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$global_baseline_eyelid_thickness_mm" \
  "$thickness_mode" "$THICKNESSES" "$PRESSURES" "$NP_PER_CASE" \
  "$CASE_TIMEOUT_SECONDS" "$CAMPAIGN_DEADLINE_SECONDS" "$MIN_AVAILABLE_MEMORY_GIB" \
  "$ABORT_AVAILABLE_MEMORY_GIB" "$MIN_FREE_DISK_GIB" "$ABORT_FREE_DISK_GIB" \
  "$MONITOR_INTERVAL_SECONDS" "$SESSION_TERM_GRACE_SECONDS" \
  "$SESSION_KILL_GRACE_SECONDS" > "$CAMPAIGN_ROOT/campaign_status.csv"

CURRENT_UNIT=""
CURRENT_TOKEN=""
CURRENT_LABEL=""
CURRENT_RUN_PID=""
cleanup_active_unit() {
  local exit_rc=$?
  trap - EXIT
  set +e
  if [[ -n "$CURRENT_UNIT" ]]; then
    guard_stop_unit_tree "$CURRENT_UNIT" "$CURRENT_TOKEN" "$CAMPAIGN_ROOT" \
      "${CURRENT_LABEL:-unknown}" launcher_exit_trap || true
  fi
  if [[ -n "$CURRENT_RUN_PID" ]] && kill -0 "$CURRENT_RUN_PID" 2>/dev/null; then
    kill -TERM "$CURRENT_RUN_PID" 2>/dev/null || true
    client_deadline=$(( $(date +%s) + 5 ))
    while kill -0 "$CURRENT_RUN_PID" 2>/dev/null && (( $(date +%s) < client_deadline )); do
      sleep 1
    done
    kill -KILL "$CURRENT_RUN_PID" 2>/dev/null || true
    wait "$CURRENT_RUN_PID" 2>/dev/null || true
  fi
  exit "$exit_rc"
}
handle_signal() {
  local signal_name="$1" signal_rc="$2"
  set +e
  printf 'launcher_signal,%s,%s\n' "$signal_name" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    >> "$CAMPAIGN_ROOT/campaign_status.csv"
  if [[ -n "$CURRENT_UNIT" ]]; then
    if guard_stop_unit_tree "$CURRENT_UNIT" "$CURRENT_TOKEN" "$CAMPAIGN_ROOT" \
        "${CURRENT_LABEL:-unknown}" "launcher_signal_$signal_name"; then
      CURRENT_UNIT=""
      CURRENT_TOKEN=""
      CURRENT_LABEL=""
    fi
  fi
  printf 'ended_at_utc,%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    >> "$CAMPAIGN_ROOT/campaign_status.csv"
  printf '%s\n' incomplete > "$CAMPAIGN_ROOT/CAMPAIGN_INCOMPLETE"
  exit "$signal_rc"
}
trap cleanup_active_unit EXIT
trap 'handle_signal INT 130' INT
trap 'handle_signal TERM 143' TERM
trap 'handle_signal HUP 129' HUP

start_epoch="$(date +%s)"
overall_rc=0
for pressure in "${pressure_list[@]}"; do
  if ! resource_gate; then
    overall_rc=1
    printf 'resource_gate_failed_pressure,%s\n' "$pressure" >> "$CAMPAIGN_ROOT/campaign_status.csv"
    break
  fi
  elapsed=$(( $(date +%s) - start_epoch ))
  remaining=$(( CAMPAIGN_DEADLINE_SECONDS - elapsed ))
  if (( remaining < 3600 )); then
    overall_rc=1
    printf 'deadline_guard_stopped_pressure,%s\n' "$pressure" >> "$CAMPAIGN_ROOT/campaign_status.csv"
    break
  fi

  label="iop${pressure}"
  args=(
    --eyelid-thicknesses "${thickness_list[@]}"
    --thickness-indent-mm 0.28
    --mesh-size-mm 0.20
    --local-refine-level 1
    --iop-mmhg "$pressure"
    --eyelid-material-scale 1.0
    --cornea-material-scale 0.75
    --initial-gap-mm 0.30
    --workers 1
    --np "$NP_PER_CASE"
    --timeout-seconds "$CASE_TIMEOUT_SECONDS"
    --retry-count 0
    --view-policy none
    --ansys-bin "$ANSYS_BIN"
    --run-root "$CAMPAIGN_ROOT/$label"
  )
  unit="blueknow-l010-${label}-${start_epoch}-$$.service"
  campaign_token="$(cat /proc/sys/kernel/random/uuid)"
  printf '%s_started_at_utc,%s\n%s_systemd_unit,%s\n%s_campaign_token,%s\n' \
    "$label" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$label" "$unit" \
    "$label" "$campaign_token" >> "$CAMPAIGN_ROOT/campaign_status.csv"

  set +e
  CURRENT_UNIT="$unit"
  CURRENT_TOKEN="$campaign_token"
  CURRENT_LABEL="$label"
  if ! guard_start_unit "$unit" "$campaign_token" "$CAMPAIGN_ROOT/$label.log" \
      "$REPO_ROOT" timeout --signal=TERM --kill-after="${SESSION_TERM_GRACE_SECONDS}s" \
      "$remaining" "$PYTHON_BIN" "$RUNNER" "${args[@]}"; then
    rc=125
    CURRENT_RUN_PID="${GUARD_RUN_PID:-}"
    guard_stop_unit_tree "$unit" "$campaign_token" "$CAMPAIGN_ROOT" "$label" \
      guard_start_failed || true
    if [[ -n "$CURRENT_RUN_PID" ]] && kill -0 "$CURRENT_RUN_PID" 2>/dev/null; then
      kill -TERM "$CURRENT_RUN_PID" 2>/dev/null || true
    fi
    wait "$CURRENT_RUN_PID" 2>/dev/null || true
    printf '%s_guard_start_failed,1\n' "$label" >> "$CAMPAIGN_ROOT/campaign_status.csv"
    CURRENT_UNIT=""
    CURRENT_TOKEN=""
    CURRENT_LABEL=""
    CURRENT_RUN_PID=""
    overall_rc=1
    set -e
    break
  fi
  run_pid="$GUARD_RUN_PID"
  CURRENT_RUN_PID="$run_pid"
  resource_abort=0
  residual_failure=0
  while kill -0 "$run_pid" 2>/dev/null; do
    sleep "$MONITOR_INTERVAL_SECONDS"
    available_kib="$(awk '/MemAvailable:/ {print $2}' /proc/meminfo)"
    free_disk_kib="$(df -Pk "$(dirname "$CAMPAIGN_ROOT")" | awk 'NR==2 {print $4}')"
    printf '%s,%s,%s,%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$label" \
      "$available_kib" "$free_disk_kib" >> "$CAMPAIGN_ROOT/resource_monitor.csv"
    if (( available_kib < ABORT_AVAILABLE_MEMORY_GIB * 1024 * 1024 \
          || free_disk_kib < ABORT_FREE_DISK_GIB * 1024 * 1024 )); then
      resource_abort=1
      printf '%s,%s,resource_guard_abort,%s,%s\n' \
        "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$label" "$available_kib" "$free_disk_kib" \
        >> "$CAMPAIGN_ROOT/resource_abort.csv"
      if ! guard_stop_unit_tree "$unit" "$campaign_token" "$CAMPAIGN_ROOT" "$label" \
          resource_guard_abort; then
        residual_failure=1
      fi
      break
    fi
  done
  wait "$run_pid"
  rc=$?
  if ! guard_finalize_unit "$unit" "$campaign_token" "$CAMPAIGN_ROOT" "$label"; then
    residual_failure=1
  fi
  if [[ "$resource_abort" -eq 1 ]]; then
    rc=143
  fi
  if [[ "$residual_failure" -eq 1 ]]; then
    rc=125
    printf '%s_session_guard_residual_failure,1\n' "$label" \
      >> "$CAMPAIGN_ROOT/campaign_status.csv"
  fi
  set -e
  CURRENT_UNIT=""
  CURRENT_TOKEN=""
  CURRENT_LABEL=""
  CURRENT_RUN_PID=""
  printf '%s_returncode,%s\n%s_ended_at_utc,%s\n' "$label" "$rc" "$label" \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$CAMPAIGN_ROOT/campaign_status.csv"
  if [[ "$rc" -ne 0 ]]; then
    overall_rc=1
    break
  fi
done

printf 'ended_at_utc,%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  >> "$CAMPAIGN_ROOT/campaign_status.csv"
if [[ "$overall_rc" -eq 0 ]]; then
  printf '%s\n' complete > "$CAMPAIGN_ROOT/CAMPAIGN_COMPLETE"
  trap - EXIT INT TERM HUP
  exit 0
fi
printf '%s\n' incomplete > "$CAMPAIGN_ROOT/CAMPAIGN_INCOMPLETE"
trap - EXIT INT TERM HUP
exit 1
