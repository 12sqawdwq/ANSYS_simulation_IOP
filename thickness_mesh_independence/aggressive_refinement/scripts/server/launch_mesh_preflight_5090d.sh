#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/home/xuanyu/PROJECT/ziyu/blueknow/simulation}"
PYTHON_BIN="${PYTHON_BIN:-/home/xuanyu/miniconda3/envs/grs-pilot/bin/python}"
ANSYS_BIN="${ANSYS_BIN:-/ansys_inc/v252/ansys/bin/ansys252}"
CONFIG_SOURCE="${CONFIG_SOURCE:-$REPO_ROOT/thickness_mesh_independence/aggressive_refinement/config/experiment.json}"
RUN_EXTREME="${RUN_EXTREME:-0}"
: "${EXPECTED_COMMIT:?Set EXPECTED_COMMIT to the exact committed experiment source SHA.}"
: "${CAMPAIGN_ROOT:?Set CAMPAIGN_ROOT to a new path under blueknow-data.}"

actual_commit="$(git -C "$REPO_ROOT" rev-parse HEAD)"
if [[ "$actual_commit" != "$EXPECTED_COMMIT" ]]; then
  printf 'Unexpected Git commit: expected %s, got %s\n' "$EXPECTED_COMMIT" "$actual_commit" >&2
  exit 2
fi
if [[ -n "$(git -C "$REPO_ROOT" status --porcelain)" ]]; then
  printf 'Formal preflight requires a clean 5090d worktree.\n' >&2
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
if [[ "$RUN_EXTREME" != 0 && "$RUN_EXTREME" != 1 ]]; then
  printf 'RUN_EXTREME must be 0 or 1.\n' >&2
  exit 2
fi

available_kib="$(awk '/MemAvailable:/ {print $2}' /proc/meminfo)"
free_disk_kib="$(df -Pk "$(dirname "$CAMPAIGN_ROOT")" | awk 'NR==2 {print $4}')"
if (( available_kib < 70 * 1024 * 1024 )); then
  printf 'Preflight requires at least 70 GiB MemAvailable; found %.2f GiB.\n' \
    "$(awk -v k="$available_kib" 'BEGIN {print k/1024/1024}')" >&2
  exit 3
fi
if (( free_disk_kib < 80 * 1024 * 1024 )); then
  printf 'Preflight requires at least 80 GiB free disk; found %.2f GiB.\n' \
    "$(awk -v k="$free_disk_kib" 'BEGIN {print k/1024/1024}')" >&2
  exit 3
fi

mkdir -p "$CAMPAIGN_ROOT"
cp "$0" "$CAMPAIGN_ROOT/launch_mesh_preflight_5090d.sh"
cp "$CONFIG_SOURCE" "$CAMPAIGN_ROOT/experiment.json"
cp "$REPO_ROOT/models/apdl/param_eye_sweep.mac" "$CAMPAIGN_ROOT/param_eye_sweep.mac"
cp "$REPO_ROOT/thickness_mesh_independence/aggressive_refinement/scripts/analysis/collect_mesh_preflight.py" \
  "$CAMPAIGN_ROOT/collect_mesh_preflight.py"
printf '%s\n' "$actual_commit" > "$CAMPAIGN_ROOT/source_git_commit.txt"
printf '%s  %s\n' "$(sha256sum "$CAMPAIGN_ROOT/param_eye_sweep.mac" | awk '{print $1}')" \
  param_eye_sweep.mac > "$CAMPAIGN_ROOT/source_sha256.txt"
printf 'started_at_utc,%s\nrun_extreme,%s\nmem_available_kib,%s\nfree_disk_kib,%s\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$RUN_EXTREME" "$available_kib" "$free_disk_kib" \
  > "$CAMPAIGN_ROOT/campaign_status.csv"

declare -a strategies=("G015:0.00015:100:900" "L010:0.00020:110:900")
if [[ "$RUN_EXTREME" == 1 ]]; then
  strategies+=("L005:0.00020:120:1800")
fi

overall_rc=0
for item in "${strategies[@]}"; do
  IFS=: read -r label background_m encoded_mode timeout_seconds <<< "$item"
  case_root="$CAMPAIGN_ROOT/$label"
  mkdir "$case_root"
  cp "$CAMPAIGN_ROOT/param_eye_sweep.mac" "$case_root/param_eye_sweep.mac"
  cat > "$case_root/driver.dat" <<EOF
/batch
/filname,$label
*use,param_eye_sweep.mac,0,0.00028,$encoded_mode,$background_m,0.00200,2666.447368421,1.0,0.75,0.00030
/eof
EOF
  printf '%s_started_at_utc,%s\n' "$label" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    >> "$CAMPAIGN_ROOT/campaign_status.csv"
  set +e
  (
    cd "$case_root"
    timeout "$timeout_seconds" /usr/bin/time -v "$ANSYS_BIN" -b -np 1 -j "$label" \
      -i driver.dat -o mesh.out > time.out 2>&1
  )
  rc=$?
  set -e
  printf '%s_returncode,%s\n%s_ended_at_utc,%s\n' "$label" "$rc" "$label" \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$CAMPAIGN_ROOT/campaign_status.csv"
  if [[ "$rc" -ne 0 ]] \
      || ! grep -q 'RUN COMPLETED' "$case_root/mesh.out" \
      || ! grep -Eq 'NUMBER OF ERROR[[:space:]]+MESSAGES ENCOUNTERED=[[:space:]]+0' "$case_root/mesh.out" \
      || [[ ! -s "$case_root/aggressive_mesh_inventory.csv" ]]; then
    overall_rc=1
    printf '%s\n' failed > "$case_root/PREFLIGHT_FAILED"
    break
  fi
  printf '%s\n' complete > "$case_root/PREFLIGHT_COMPLETE"
done

if ! "$PYTHON_BIN" "$CAMPAIGN_ROOT/collect_mesh_preflight.py" \
  --campaign-root "$CAMPAIGN_ROOT" \
  --output "$CAMPAIGN_ROOT/preflight_manifest.csv"; then
  overall_rc=1
fi
printf 'ended_at_utc,%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  >> "$CAMPAIGN_ROOT/campaign_status.csv"
if [[ "$overall_rc" -eq 0 ]]; then
  printf '%s\n' complete > "$CAMPAIGN_ROOT/CAMPAIGN_COMPLETE"
  exit 0
fi
printf '%s\n' failed > "$CAMPAIGN_ROOT/CAMPAIGN_FAILED"
exit 1
