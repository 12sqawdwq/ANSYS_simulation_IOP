#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SESSION_TERM_GRACE_SECONDS="${SESSION_TERM_GRACE_SECONDS:-2}"
SESSION_KILL_GRACE_SECONDS="${SESSION_KILL_GRACE_SECONDS:-5}"
# shellcheck source=session_guard.sh
source "$SCRIPT_DIR/session_guard.sh"

guard_require_user_systemd

workdir="$(mktemp -d /tmp/blueknow-session-guard-test.XXXXXX)"
unit="blueknow-session-guard-test-$$.service"
token="test-$(cat /proc/sys/kernel/random/uuid)"
worker="$workdir/nested_worker.sh"
log="$workdir/unit.log"
cleanup() {
  set +e
  if guard_has_processes "$unit" "$token"; then
    guard_stop_unit_tree "$unit" "$token" "$workdir" test trap_cleanup >/dev/null 2>&1 || true
  fi
  [[ -n "${GUARD_RUN_PID:-}" ]] && wait "$GUARD_RUN_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

cat > "$worker" <<'WORKER'
#!/usr/bin/env bash
set -u
setsid bash -c 'trap "" TERM; exec -a mapdl-session-guard-test sleep 300' &
setsid bash -c 'trap "" TERM; exec -a hydra-pmi-session-guard-test sleep 300' &
trap '' TERM
wait
WORKER
chmod 700 "$worker"
printf 'utc,label,unit,event,detail\n' > "$workdir/session_guard_events.csv"
printf 'utc\tlabel\tunit\tevent\tprocess\n' > "$workdir/session_guard_processes.tsv"
printf 'utc,label,unit,event,status\n' > "$workdir/session_guard_unit_status.csv"

guard_start_unit "$unit" "$token" "$log" "$workdir" "$worker"
client_pid="$GUARD_RUN_PID"
sleep 1
before_count="$(guard_all_pids "$unit" "$token" | wc -l)"
if (( before_count < 3 )); then
  printf 'Expected at least three contained processes, found %s\n' "$before_count" >&2
  exit 1
fi

guard_stop_unit_tree "$unit" "$token" "$workdir" test nested_setsid_term_kill
set +e
wait "$client_pid"
client_rc=$?
set -e
if guard_has_processes "$unit" "$token"; then
  printf 'Session guard left residual processes\n' >&2
  exit 1
fi
grep -q ',term_sent,' "$workdir/session_guard_events.csv"
grep -q ',kill_sent,' "$workdir/session_guard_events.csv"
grep -q ',no_residual_processes,' "$workdir/session_guard_events.csv"
grep -q 'mapdl-session-guard-test' "$workdir/session_guard_processes.tsv"
grep -q 'hydra-pmi-session-guard-test' "$workdir/session_guard_processes.tsv"
systemctl --user reset-failed "$unit" >/dev/null 2>&1 || true
printf 'SESSION_GUARD_TEST_PASS unit=%s contained_before=%s client_rc=%s\n' \
  "$unit" "$before_count" "$client_rc"
printf 'audit_dir=%s\n' "$workdir"
trap - EXIT INT TERM
