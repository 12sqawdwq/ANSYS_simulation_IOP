#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/home/xuanyu/PROJECT/ziyu/blueknow/simulation}"
EXPECTED_COMMIT="${EXPECTED_COMMIT:-$(git -C "$REPO_ROOT" rev-parse HEAD)}"
launcher="${LAUNCHER:-$REPO_ROOT/thickness_mesh_independence/aggressive_refinement/scripts/server/launch_aggressive_anchor_5090d.sh}"
workdir="$(mktemp -d /tmp/blueknow-anchor-launcher-test.XXXXXX)"
campaign="$workdir/campaign"
fake_python="$workdir/fake_python.sh"

if [[ -n "$(git -C "$REPO_ROOT" status --porcelain)" ]]; then
  printf 'Launcher integration test requires a clean worktree\n' >&2
  exit 2
fi
cat > "$fake_python" <<'FAKE'
#!/usr/bin/env bash
set -u
setsid bash -c 'trap "" TERM; exec -a mapdl-anchor-launcher-test sleep 300' &
setsid bash -c 'trap "" TERM; exec -a hydra-anchor-launcher-test sleep 300' &
trap '' TERM
wait
FAKE
chmod 700 "$fake_python"

cleanup() {
  set +e
  if [[ -n "${launcher_pid:-}" ]] && kill -0 "$launcher_pid" 2>/dev/null; then
    kill -TERM "$launcher_pid" 2>/dev/null || true
    sleep 1
    kill -KILL "$launcher_pid" 2>/dev/null || true
  fi
  pgrep -f 'mapdl-anchor-launcher-test|hydra-anchor-launcher-test' | xargs -r kill -KILL 2>/dev/null || true
}
trap cleanup EXIT INT TERM

EXPECTED_COMMIT="$EXPECTED_COMMIT" \
CAMPAIGN_ROOT="$campaign" \
REPO_ROOT="$REPO_ROOT" \
PYTHON_BIN="$fake_python" \
ANSYS_BIN=/bin/true \
THICKNESSES=2.0 \
PRESSURES=0 \
NP_PER_CASE=4 \
CASE_TIMEOUT_SECONDS=600 \
CAMPAIGN_DEADLINE_SECONDS=7200 \
MIN_AVAILABLE_MEMORY_GIB=2 \
ABORT_AVAILABLE_MEMORY_GIB=1 \
MIN_FREE_DISK_GIB=2 \
ABORT_FREE_DISK_GIB=1 \
MONITOR_INTERVAL_SECONDS=1 \
SESSION_TERM_GRACE_SECONDS=2 \
SESSION_KILL_GRACE_SECONDS=5 \
bash "$launcher" > "$workdir/launcher.log" 2>&1 &
launcher_pid=$!

ready=0
for _ in $(seq 1 30); do
  if [[ -f "$campaign/campaign_status.csv" ]] \
      && grep -q '^iop0_systemd_unit,' "$campaign/campaign_status.csv" \
      && pgrep -f 'mapdl-anchor-launcher-test' >/dev/null \
      && pgrep -f 'hydra-anchor-launcher-test' >/dev/null; then
    ready=1
    break
  fi
  if ! kill -0 "$launcher_pid" 2>/dev/null; then
    break
  fi
  sleep 1
done
if [[ "$ready" -ne 1 ]]; then
  printf 'Launcher integration fixture did not become ready\n' >&2
  cat "$workdir/launcher.log" >&2 || true
  exit 1
fi

kill -TERM "$launcher_pid"
set +e
wait "$launcher_pid"
launcher_rc=$?
set -e
if [[ "$launcher_rc" -ne 143 ]]; then
  printf 'Expected launcher signal exit 143, got %s\n' "$launcher_rc" >&2
  exit 1
fi
fixture_empty=0
for _ in $(seq 1 5); do
  if ! pgrep -f 'mapdl-anchor-launcher-test|hydra-anchor-launcher-test' >/dev/null; then
    fixture_empty=1
    break
  fi
  # Killed children can remain briefly as init-reapable zombies after the
  # cgroup and token process sets are already empty.
  sleep 1
done
if [[ "$fixture_empty" -ne 1 ]]; then
  printf 'Launcher signal path left residual nested processes\n' >&2
  exit 1
fi
test -f "$campaign/CAMPAIGN_INCOMPLETE"
grep -q '^launcher_signal,TERM,' "$campaign/campaign_status.csv"
grep -q ',term_sent,launcher_signal_TERM' "$campaign/session_guard_events.csv"
grep -q ',kill_sent,launcher_signal_TERM' "$campaign/session_guard_events.csv"
grep -q ',no_residual_processes,launcher_signal_TERM' "$campaign/session_guard_events.csv"
grep -q 'mapdl-anchor-launcher-test' "$campaign/session_guard_processes.tsv"
grep -q 'hydra-anchor-launcher-test' "$campaign/session_guard_processes.tsv"
unit="$(awk -F, '$1=="iop0_systemd_unit" {print $2}' "$campaign/campaign_status.csv")"
systemctl --user reset-failed "$unit" >/dev/null 2>&1 || true
printf 'ANCHOR_LAUNCHER_SIGNAL_TEST_PASS launcher_rc=%s unit=%s\n' "$launcher_rc" "$unit"
printf 'audit_dir=%s\n' "$workdir"
trap - EXIT INT TERM
