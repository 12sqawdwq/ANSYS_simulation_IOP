#!/usr/bin/env bash
# Cgroup-backed process containment for aggressive MAPDL campaigns.
# This file is sourced by launchers and can also be exercised by the server test.

SESSION_TERM_GRACE_SECONDS="${SESSION_TERM_GRACE_SECONDS:-30}"
SESSION_KILL_GRACE_SECONDS="${SESSION_KILL_GRACE_SECONDS:-10}"
SESSION_START_TIMEOUT_SECONDS="${SESSION_START_TIMEOUT_SECONDS:-15}"
GUARD_RUN_PID=""

_guard_utc() {
  date -u +%Y-%m-%dT%H:%M:%SZ
}

guard_require_user_systemd() {
  command -v systemd-run >/dev/null 2>&1 || {
    printf 'session guard requires systemd-run\n' >&2
    return 1
  }
  command -v systemctl >/dev/null 2>&1 || {
    printf 'session guard requires systemctl\n' >&2
    return 1
  }
  [[ "$(stat -fc %T /sys/fs/cgroup 2>/dev/null || true)" == "cgroup2fs" ]] || {
    printf 'session guard requires cgroup v2\n' >&2
    return 1
  }
  systemctl --user show-environment >/dev/null 2>&1 || {
    printf 'session guard requires an accessible user systemd manager\n' >&2
    return 1
  }
}

guard_cgroup_path() {
  local unit="$1" cgroup
  cgroup="$(systemctl --user show "$unit" --property=ControlGroup --value 2>/dev/null || true)"
  [[ -n "$cgroup" && "$cgroup" != "/" ]] || return 0
  printf '/sys/fs/cgroup%s\n' "$cgroup"
}

guard_cgroup_pids() {
  local unit="$1" path file
  path="$(guard_cgroup_path "$unit")"
  [[ -n "$path" && -d "$path" ]] || return 0
  while IFS= read -r -d '' file; do
    cat "$file" 2>/dev/null || true
  done < <(find "$path" -type f -name cgroup.procs -print0 2>/dev/null)
}

guard_token_pids() {
  local token="$1" environ pid
  [[ -n "$token" ]] || return 0
  for environ in /proc/[0-9]*/environ; do
    [[ -r "$environ" ]] || continue
    if grep -zFxq "BLUEKNOW_CAMPAIGN_TOKEN=$token" "$environ" 2>/dev/null; then
      pid="${environ#/proc/}"
      printf '%s\n' "${pid%/environ}"
    fi
  done
}

guard_all_pids() {
  local unit="$1" token="$2"
  {
    guard_cgroup_pids "$unit"
    guard_token_pids "$token"
  } | awk '/^[0-9]+$/' | sort -nu
}

guard_has_processes() {
  [[ -n "$(guard_all_pids "$1" "$2")" ]]
}

guard_record_event() {
  local audit_dir="$1" label="$2" unit="$3" event="$4" detail="${5:-}"
  printf '%s,%s,%s,%s,%s\n' "$(_guard_utc)" "$label" "$unit" "$event" "$detail" \
    >> "$audit_dir/session_guard_events.csv"
}

guard_record_processes() {
  local audit_dir="$1" label="$2" unit="$3" token="$4" event="$5" pid row
  while IFS= read -r pid; do
    [[ -n "$pid" ]] || continue
    row="$(ps -p "$pid" -o pid=,ppid=,sid=,pgid=,user=,comm=,args= 2>/dev/null || true)"
    [[ -n "$row" ]] || continue
    printf '%s\t%s\t%s\t%s\t%s\n' "$(_guard_utc)" "$label" "$unit" "$event" "$row" \
      >> "$audit_dir/session_guard_processes.tsv"
  done < <(guard_all_pids "$unit" "$token")
}

guard_record_unit_status() {
  local audit_dir="$1" label="$2" unit="$3" event="$4" line
  line="$(systemctl --user show "$unit" \
    --property=ActiveState,SubState,Result,ExecMainCode,ExecMainStatus,ControlGroup \
    --value 2>/dev/null | paste -sd '|' - || true)"
  printf '%s,%s,%s,%s,%s\n' "$(_guard_utc)" "$label" "$unit" "$event" "$line" \
    >> "$audit_dir/session_guard_unit_status.csv"
}

guard_start_unit() {
  local unit="$1" token="$2" log_path="$3" workdir="$4"
  shift 4
  [[ "$unit" == *.service ]] || {
    printf 'session guard unit must end in .service: %s\n' "$unit" >&2
    return 2
  }
  if systemctl --user list-units --all --full "$unit" --no-legend 2>/dev/null | grep -Fq "$unit"; then
    printf 'session guard unit already exists: %s\n' "$unit" >&2
    return 2
  fi
  systemd-run --user --quiet --wait --pipe \
    --unit="$unit" \
    --property=Type=exec \
    --property=KillMode=control-group \
    --property="TimeoutStopSec=${SESSION_TERM_GRACE_SECONDS}s" \
    --working-directory="$workdir" \
    --setenv="BLUEKNOW_CAMPAIGN_TOKEN=$token" \
    -- "$@" > "$log_path" 2>&1 &
  GUARD_RUN_PID=$!

  local deadline state
  deadline=$(( $(date +%s) + SESSION_START_TIMEOUT_SECONDS ))
  while (( $(date +%s) <= deadline )); do
    state="$(systemctl --user show "$unit" --property=ActiveState --value 2>/dev/null || true)"
    if [[ "$state" == "active" || "$state" == "activating" ]]; then
      return 0
    fi
    if ! kill -0 "$GUARD_RUN_PID" 2>/dev/null; then
      wait "$GUARD_RUN_PID" || true
      printf 'session guard unit failed to start: %s\n' "$unit" >&2
      return 1
    fi
    sleep 0.2
  done
  printf 'session guard unit start timed out: %s\n' "$unit" >&2
  return 1
}

guard_signal_all() {
  local unit="$1" token="$2" signal_name="$3" pid
  systemctl --user kill --kill-whom=all --signal="$signal_name" "$unit" >/dev/null 2>&1 || true
  while IFS= read -r pid; do
    [[ -n "$pid" ]] || continue
    kill -"$signal_name" "$pid" 2>/dev/null || true
  done < <(guard_token_pids "$token" | sort -nu)
}

guard_wait_empty() {
  local unit="$1" token="$2" seconds="$3" deadline
  deadline=$(( $(date +%s) + seconds ))
  while guard_has_processes "$unit" "$token"; do
    (( $(date +%s) < deadline )) || return 1
    sleep 1
  done
}

guard_stop_unit_tree() {
  local unit="$1" token="$2" audit_dir="$3" label="$4" reason="$5"
  guard_record_event "$audit_dir" "$label" "$unit" stop_requested "$reason"
  guard_record_unit_status "$audit_dir" "$label" "$unit" before_term
  guard_record_processes "$audit_dir" "$label" "$unit" "$token" before_term
  guard_signal_all "$unit" "$token" TERM
  guard_record_event "$audit_dir" "$label" "$unit" term_sent "$reason"

  if ! guard_wait_empty "$unit" "$token" "$SESSION_TERM_GRACE_SECONDS"; then
    guard_record_processes "$audit_dir" "$label" "$unit" "$token" before_kill
    guard_signal_all "$unit" "$token" KILL
    guard_record_event "$audit_dir" "$label" "$unit" kill_sent "$reason"
    guard_wait_empty "$unit" "$token" "$SESSION_KILL_GRACE_SECONDS" || true
  fi

  guard_record_unit_status "$audit_dir" "$label" "$unit" after_stop
  if guard_has_processes "$unit" "$token"; then
    guard_record_processes "$audit_dir" "$label" "$unit" "$token" residual_after_kill
    guard_record_event "$audit_dir" "$label" "$unit" residual_detected "$reason"
    return 1
  fi
  guard_record_event "$audit_dir" "$label" "$unit" no_residual_processes "$reason"
  return 0
}

guard_finalize_unit() {
  local unit="$1" token="$2" audit_dir="$3" label="$4"
  guard_record_unit_status "$audit_dir" "$label" "$unit" client_wait_complete
  if guard_has_processes "$unit" "$token"; then
    guard_stop_unit_tree "$unit" "$token" "$audit_dir" "$label" post_wait_residual
    return $?
  fi
  guard_record_event "$audit_dir" "$label" "$unit" no_residual_processes natural_completion
  return 0
}
