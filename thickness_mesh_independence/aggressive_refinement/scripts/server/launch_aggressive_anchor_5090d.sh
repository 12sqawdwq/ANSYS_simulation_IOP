#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/home/xuanyu/PROJECT/ziyu/blueknow/simulation}"
PYTHON_BIN="${PYTHON_BIN:-/home/xuanyu/miniconda3/envs/grs-pilot/bin/python}"
ANSYS_BIN="${ANSYS_BIN:-/ansys_inc/v252/ansys/bin/ansys252}"
RUNNER="$REPO_ROOT/src/runners/run_indentation_sweep.py"
CONFIG_SOURCE="${CONFIG_SOURCE:-$REPO_ROOT/thickness_mesh_independence/aggressive_refinement/config/experiment.json}"
THICKNESSES="${THICKNESSES:-2.0}"
PRESSURES="${PRESSURES:-0 20}"
NP_PER_CASE="${NP_PER_CASE:-4}"
CASE_TIMEOUT_SECONDS="${CASE_TIMEOUT_SECONDS:-86400}"
CAMPAIGN_DEADLINE_SECONDS="${CAMPAIGN_DEADLINE_SECONDS:-129600}"
MIN_AVAILABLE_MEMORY_GIB="${MIN_AVAILABLE_MEMORY_GIB:-70}"
MIN_FREE_DISK_GIB="${MIN_FREE_DISK_GIB:-80}"
ABORT_AVAILABLE_MEMORY_GIB="${ABORT_AVAILABLE_MEMORY_GIB:-15}"
ABORT_FREE_DISK_GIB="${ABORT_FREE_DISK_GIB:-30}"
MONITOR_INTERVAL_SECONDS="${MONITOR_INTERVAL_SECONDS:-60}"
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
read -r -a thickness_list <<< "$THICKNESSES"
read -r -a pressure_list <<< "$PRESSURES"
if [[ "${#thickness_list[@]}" -eq 0 || "${#pressure_list[@]}" -eq 0 ]]; then
  printf 'At least one thickness and pressure are required.\n' >&2
  exit 2
fi
for thickness in "${thickness_list[@]}"; do
  if [[ "$thickness" != 1.6 && "$thickness" != 1.8 && "$thickness" != 2.0 ]]; then
    printf 'Unsupported thickness: %s\n' "$thickness" >&2
    exit 2
  fi
done
for pressure in "${pressure_list[@]}"; do
  if [[ "$pressure" != 0 && "$pressure" != 20 ]]; then
    printf 'Unsupported pressure: %s\n' "$pressure" >&2
    exit 2
  fi
done

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
cp "$CONFIG_SOURCE" "$CAMPAIGN_ROOT/experiment.json"
cp "$REPO_ROOT/models/apdl/param_eye_sweep.mac" "$CAMPAIGN_ROOT/param_eye_sweep.mac"
printf '%s\n' "$actual_commit" > "$CAMPAIGN_ROOT/source_git_commit.txt"
printf 'started_at_utc,%s\nthicknesses_mm,%s\npressures_mmhg,%s\nnp_per_case,%s\ncase_timeout_seconds,%s\ncampaign_deadline_seconds,%s\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$THICKNESSES" "$PRESSURES" "$NP_PER_CASE" \
  "$CASE_TIMEOUT_SECONDS" "$CAMPAIGN_DEADLINE_SECONDS" > "$CAMPAIGN_ROOT/campaign_status.csv"
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
  printf '%s_started_at_utc,%s\n' "$label" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    >> "$CAMPAIGN_ROOT/campaign_status.csv"
  set +e
  (
    cd "$REPO_ROOT"
    exec setsid timeout "$remaining" "$PYTHON_BIN" "$RUNNER" "${args[@]}"
  ) > "$CAMPAIGN_ROOT/$label.log" 2>&1 &
  run_pid=$!
  resource_abort=0
  while kill -0 "$run_pid" 2>/dev/null; do
    sleep "$MONITOR_INTERVAL_SECONDS"
    available_kib="$(awk '/MemAvailable:/ {print $2}' /proc/meminfo)"
    free_disk_kib="$(df -Pk "$(dirname "$CAMPAIGN_ROOT")" | awk 'NR==2 {print $4}')"
    printf '%s,%s,%s,%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$label" \
      "$available_kib" "$free_disk_kib" >> "$CAMPAIGN_ROOT/resource_monitor.csv"
    if (( available_kib < ABORT_AVAILABLE_MEMORY_GIB * 1024 * 1024 \
          || free_disk_kib < ABORT_FREE_DISK_GIB * 1024 * 1024 )); then
      resource_abort=1
      kill -TERM -- "-$run_pid" 2>/dev/null || kill -TERM "$run_pid" 2>/dev/null || true
      printf '%s,%s,resource_guard_abort\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$label" \
        >> "$CAMPAIGN_ROOT/resource_abort.csv"
      break
    fi
  done
  wait "$run_pid"
  rc=$?
  if [[ "$resource_abort" -eq 1 && "$rc" -eq 0 ]]; then
    rc=143
  fi
  set -e
  printf '%s_returncode,%s\n%s_ended_at_utc,%s\n' "$label" "$rc" "$label" \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$CAMPAIGN_ROOT/campaign_status.csv"
  if [[ "$rc" -ne 0 ]]; then
    overall_rc=1
    break
  fi
done
printf 'ended_at_utc,%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  >> "$CAMPAIGN_ROOT/campaign_status.csv"
if [[ "$overall_rc" -eq 0 && "${#pressure_list[@]}" -eq 2 ]]; then
  printf '%s\n' complete > "$CAMPAIGN_ROOT/CAMPAIGN_COMPLETE"
  exit 0
fi
printf '%s\n' incomplete > "$CAMPAIGN_ROOT/CAMPAIGN_INCOMPLETE"
exit 1
