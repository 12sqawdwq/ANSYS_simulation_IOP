#!/usr/bin/env python3
"""Remove reproducible MAPDL scratch files while retaining auditable results."""
from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


POLICY = "mapdl-auditable-results"
POLICY_REVISION = 1
SCRATCH_SUFFIXES = {
    ".cnd",
    ".dsp",
    ".dsptri",
    ".dsub",
    ".emat",
    ".esav",
    ".full",
    ".gst",
    ".ldhi",
    ".mntr",
    ".mode",
    ".osav",
    ".page",
    ".pcs",
    ".rdb",
    ".sub",
    ".tri",
}


@dataclass(frozen=True)
class PruneStats:
    files_selected: int
    bytes_selected: int
    applied: bool
    selected_files: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["selected_files"] = list(self.selected_files)
        payload["policy"] = POLICY
        payload["policy_revision"] = POLICY_REVISION
        return payload


def _is_rank_result(name: str, job_name: str) -> bool:
    return re.fullmatch(rf"{re.escape(job_name)}\d+\.rst", name, re.IGNORECASE) is not None


def _is_distributed_partition(name: str) -> bool:
    return re.search(r"\.r\d{3}$", name, re.IGNORECASE) is not None


def _is_removable(path: Path, job_name: str, keep_primary_results: bool) -> bool:
    name_lower = path.name.lower()
    if path.suffix.lower() in SCRATCH_SUFFIXES or _is_distributed_partition(path.name):
        return True
    if _is_rank_result(path.name, job_name):
        return True
    if not keep_primary_results and name_lower in {
        f"{job_name.lower()}.rst",
        f"{job_name.lower()}.db",
    }:
        return True
    return False


def prune_attempt(
    attempt_dir: Path,
    job_name: str,
    *,
    keep_primary_results: bool,
    apply: bool = True,
) -> PruneStats:
    """Prune one attempt without touching logs, metrics, APDL inputs, or PNG views."""
    attempt_dir = attempt_dir.resolve()
    if not attempt_dir.is_dir():
        raise FileNotFoundError(f"attempt directory does not exist: {attempt_dir}")
    selected = sorted(
        path for path in attempt_dir.iterdir()
        if path.is_file() and _is_removable(path, job_name, keep_primary_results)
    )
    byte_count = sum(path.stat().st_size for path in selected)
    if apply:
        for path in selected:
            path.unlink()
    return PruneStats(
        files_selected=len(selected),
        bytes_selected=byte_count,
        applied=apply,
        selected_files=tuple(path.name for path in selected),
    )


def _selected_complete_attempts(run_root: Path) -> set[Path]:
    manifest_path = run_root / "run_manifest.csv"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"run manifest does not exist: {manifest_path}")
    selected: set[Path] = set()
    with manifest_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("status") != "complete" or not row.get("attempt_dir"):
                continue
            attempt = (run_root / row["attempt_dir"]).resolve()
            if run_root != attempt and run_root not in attempt.parents:
                raise ValueError(f"attempt path escapes run root: {row['attempt_dir']}")
            selected.add(attempt)
    return selected


def prune_run(run_root: Path, *, apply: bool = False) -> dict[str, object]:
    run_root = run_root.expanduser().resolve()
    selected_complete = _selected_complete_attempts(run_root)
    attempts = sorted(path.resolve() for path in run_root.glob("*/attempt_*") if path.is_dir())
    reports: list[dict[str, object]] = []
    total_files = 0
    total_bytes = 0
    for attempt in attempts:
        stats = prune_attempt(
            attempt,
            attempt.parent.name,
            keep_primary_results=attempt in selected_complete,
            apply=apply,
        )
        total_files += stats.files_selected
        total_bytes += stats.bytes_selected
        reports.append({
            "attempt_dir": str(attempt.relative_to(run_root)),
            "kept_primary_results": attempt in selected_complete,
            **stats.to_dict(),
        })
    report: dict[str, object] = {
        "run_root": str(run_root),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "applied": apply,
        "attempts": len(attempts),
        "files_selected": total_files,
        "bytes_selected": total_bytes,
        "policy": POLICY,
        "policy_revision": POLICY_REVISION,
        "attempt_reports": reports,
    }
    if apply:
        temporary = run_root / "prune_report.json.tmp"
        temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(run_root / "prune_report.json")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_root", type=Path)
    parser.add_argument("--apply", action="store_true", help="delete selected files; default is dry-run")
    cli = parser.parse_args()
    report = prune_run(cli.run_root, apply=cli.apply)
    print(json.dumps({key: report[key] for key in (
        "run_root", "applied", "attempts", "files_selected", "bytes_selected"
    )}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
