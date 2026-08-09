#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/home/xuanyu/PROJECT/ziyu/blueknow/simulation}"
CAMPAIGN_ROOT="${CAMPAIGN_ROOT:-/home/xuanyu/PROJECT/ziyu/blueknow-data/thickness_mesh_independence/20260807T113236Z_cef09f9_mesh0p24_screening_bounded}"
PYTHON_BIN="${PYTHON_BIN:-/home/xuanyu/miniconda3/envs/grs-pilot/bin/python}"
ANSYS_BIN="${ANSYS_BIN:-/ansys_inc/v252/ansys/bin/ansys252}"
CONFIG_SOURCE="${CONFIG_SOURCE:-/tmp/blueknow_mesh_experiment.json}"
MESH_SIZE_MM="${MESH_SIZE_MM:-0.24}"
WORKERS_PER_PRESSURE="${WORKERS_PER_PRESSURE:-1}"
NP_PER_CASE="${NP_PER_CASE:-8}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-28800}"
RETRY_COUNT="${RETRY_COUNT:-0}"
PRESSURES="${PRESSURES:-0 20}"
EXPECTED_COMMIT="cef09f91ca328cc39488b55047afaf9e078a980a"
RUNNER="$REPO_ROOT/src/runners/run_indentation_sweep.py"

actual_commit="$(git -C "$REPO_ROOT" rev-parse HEAD)"
if [[ "$actual_commit" != "$EXPECTED_COMMIT" ]]; then
  printf 'Unexpected Git commit: expected %s, got %s\n' "$EXPECTED_COMMIT" "$actual_commit" >&2
  exit 2
fi
if [[ -n "$(git -C "$REPO_ROOT" status --porcelain)" ]]; then
  printf 'Formal screening requires a clean 5090d worktree.\n' >&2
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
read -r -a pressure_list <<< "$PRESSURES"
if [[ "${#pressure_list[@]}" -eq 0 ]]; then
  printf 'At least one pressure is required.\n' >&2
  exit 2
fi
for pressure in "${pressure_list[@]}"; do
  if [[ "$pressure" != "0" && "$pressure" != "20" ]]; then
    printf 'Unsupported pressure for this campaign: %s\n' "$pressure" >&2
    exit 2
  fi
done

mkdir -p "$CAMPAIGN_ROOT"
cp "$0" "$CAMPAIGN_ROOT/launch_mesh_campaign_5090d.sh"
cp "$CONFIG_SOURCE" "$CAMPAIGN_ROOT/experiment.json"
printf '%s\n' "$actual_commit" > "$CAMPAIGN_ROOT/source_git_commit.txt"
printf 'started_at_utc,%s\nmesh_size_mm,%s\npressures_mmhg,%s\nworkers_per_pressure,%s\nnp_per_case,%s\ntimeout_seconds,%s\nretry_count,%s\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$MESH_SIZE_MM" "$PRESSURES" \
  "$WORKERS_PER_PRESSURE" "$NP_PER_CASE" "$TIMEOUT_SECONDS" "$RETRY_COUNT" \
  > "$CAMPAIGN_ROOT/campaign_status.csv"

common_args=(
  --eyelid-thicknesses 1.6 1.8 2.0
  --thickness-indent-mm 0.28
  --mesh-size-mm "$MESH_SIZE_MM"
  --eyelid-material-scale 1.0
  --cornea-material-scale 0.75
  --initial-gap-mm 0.30
  --workers "$WORKERS_PER_PRESSURE"
  --np "$NP_PER_CASE"
  --timeout-seconds "$TIMEOUT_SECONDS"
  --retry-count "$RETRY_COUNT"
  --view-policy none
  --ansys-bin "$ANSYS_BIN"
)

declare -A campaign_pids
for pressure in "${pressure_list[@]}"; do
  label="iop${pressure}"
  (
    cd "$REPO_ROOT"
    "$PYTHON_BIN" "$RUNNER" "${common_args[@]}" \
      --iop-mmhg "$pressure" \
      --run-root "$CAMPAIGN_ROOT/$label"
  ) > "$CAMPAIGN_ROOT/$label.log" 2>&1 &
  campaign_pids["$label"]=$!
  printf '%s_pid,%s\n' "$label" "${campaign_pids[$label]}" >> "$CAMPAIGN_ROOT/campaign_status.csv"
done

overall_rc=0
set +e
for pressure in "${pressure_list[@]}"; do
  label="iop${pressure}"
  wait "${campaign_pids[$label]}"
  rc=$?
  printf '%s_returncode,%s\n' "$label" "$rc" >> "$CAMPAIGN_ROOT/campaign_status.csv"
  if [[ "$rc" -ne 0 ]]; then
    overall_rc=1
  fi
done
set -e
printf 'ended_at_utc,%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$CAMPAIGN_ROOT/campaign_status.csv"

if [[ "$overall_rc" -eq 0 ]]; then
  printf 'complete\n' > "$CAMPAIGN_ROOT/CAMPAIGN_COMPLETE"
  exit 0
fi
printf 'failed\n' > "$CAMPAIGN_ROOT/CAMPAIGN_FAILED"
exit 1
