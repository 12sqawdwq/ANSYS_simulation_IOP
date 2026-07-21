#!/usr/bin/env python3
"""Report whether a detached thickness calibration is making healthy progress."""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

FATAL_MARKERS = (
    "ERROR TERMINATION", "FATAL ERROR", "SOLUTION NOT CONVERGED",
    "THE SOLUTION WAS NOT CONVERGED", "HIGHLY DISTORTED",
)
PROGRESS_PATTERN = re.compile(r"CONVERG|SUBSTEP", re.IGNORECASE)


def process_alive(pid: int | None) -> bool:
    if not pid:
        return False
    if os.name == "nt":
        import ctypes

        process_query_limited_information = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(
            process_query_limited_information, False, pid
        )
        if not handle:
            return False
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def read_manifest(path: Path) -> list[dict[str, str]]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))
    except (OSError, csv.Error):
        return []


def tail_text(path: Path, limit: int = 512_000) -> str:
    try:
        with path.open("rb") as handle:
            size = path.stat().st_size
            handle.seek(max(0, size - limit))
            return handle.read().decode(errors="replace")
    except OSError:
        return ""


def inspect(root: Path, fresh_seconds: float = 300.0) -> dict:
    now = time.time()
    pid_path = root / "controller.pid"
    try:
        pid = int(pid_path.read_text(encoding="ascii").strip())
    except (OSError, ValueError):
        pid = None

    manifests = sorted(root.rglob("run_manifest.csv"))
    rows = [row for path in manifests for row in read_manifest(path)]
    status_counts: dict[str, int] = {}
    for row in rows:
        status = row.get("status") or "pending"
        status_counts[status] = status_counts.get(status, 0) + 1

    active_logs = []
    fatal_events = []
    progress_markers = 0
    for path in sorted(root.rglob("solve.out")):
        text = tail_text(path)
        upper = text.upper()
        if "RUN COMPLETED" in upper:
            continue
        age = max(0.0, now - path.stat().st_mtime)
        markers = len(PROGRESS_PATTERN.findall(text))
        progress_markers += markers
        active_logs.append({
            "path": str(path.relative_to(root)),
            "age_seconds": round(age, 1),
            "fresh": age <= fresh_seconds,
            "progress_markers": markers,
        })
        for marker in FATAL_MARKERS:
            if marker in upper:
                fatal_events.append({"path": str(path.relative_to(root)), "marker": marker})

    complete = status_counts.get("complete", 0)
    controller_alive = process_alive(pid)
    logs_fresh = all(item["fresh"] for item in active_logs)
    failed = sum(
        count for status, count in status_counts.items()
        if status not in {"complete", "pending"}
    )
    healthy = (
        controller_alive and logs_fresh and not fatal_events and failed == 0
        and bool(active_logs or complete)
        and (complete >= 1 or progress_markers >= 3)
    )
    return {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "run_root": str(root),
        "controller_pid": pid,
        "controller_alive": controller_alive,
        "manifest_count": len(manifests),
        "status_counts": status_counts,
        "active_logs": active_logs,
        "fatal_events": fatal_events,
        "healthy_to_leave_unattended": healthy,
        "health_definition": (
            "controller alive, every active solve log fresh, no fatal marker, and at least "
            "one complete case or three convergence/substep progress markers"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_root", type=Path)
    parser.add_argument("--fresh-seconds", type=float, default=300.0)
    parser.add_argument("--write-snapshot", type=Path)
    cli = parser.parse_args()
    payload = inspect(cli.run_root.expanduser().resolve(), cli.fresh_seconds)
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if cli.write_snapshot:
        temporary = cli.write_snapshot.with_suffix(cli.write_snapshot.suffix + ".tmp")
        temporary.write_text(rendered, encoding="utf-8")
        temporary.replace(cli.write_snapshot)
    print(rendered, end="")
    return 0 if payload["healthy_to_leave_unattended"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
