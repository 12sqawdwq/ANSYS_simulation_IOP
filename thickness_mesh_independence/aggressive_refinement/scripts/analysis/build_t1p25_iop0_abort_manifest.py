#!/usr/bin/env python3
"""Build lightweight provenance for the user-requested 1.25-mm IOP0 abort."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def two_column_csv(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in csv.reader(path.open(encoding="utf-8-sig", newline="")):
        if len(row) >= 2:
            result[row[0]] = row[1]
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-root", type=Path, required=True)
    parser.add_argument("--external-root", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.result_root.resolve()
    status = two_column_csv(root / "user_requested_stop_audit" / "final_status.csv")
    containment = two_column_csv(root / "user_requested_stop_audit" / "containment_before_cleanup.csv")
    cleanup = two_column_csv(root / "user_requested_stop_audit" / "cleanup_summary.csv")
    campaign = two_column_csv(root / "campaign_status.csv")
    metadata = json.loads((root / "iop0" / "run_metadata.json").read_text(encoding="utf-8"))
    if status["classification"] != "user_requested_priority_switch_abort":
        raise ValueError("unexpected abort classification")
    if any(int(containment[key]) for key in ("token_processes", "solver_processes", "blueknow_running_units")):
        raise ValueError("session containment audit has residual activity")
    if int(cleanup["remaining_manifest_entries"]) != 0:
        raise ValueError("cleanup left manifest entries behind")
    if metadata["iop_mmhg"] != 0 or [case["eyelid_thickness_mm"] for case in metadata["cases"]] != [1.25]:
        raise ValueError("abort evidence is not the 1.25-mm IOP0 case")
    artifacts = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if path.resolve() == args.output.resolve():
            continue
        artifacts.append({
            "path": path.relative_to(root).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
        })
    manifest = {
        "schema_version": 1,
        "status": "user_requested_priority_switch_abort_complete",
        "classification": "user_requested_priority_switch_abort",
        "source_git_commit": campaign["started_at_utc"] and (root / "source_git_commit.txt").read_text(encoding="utf-8").strip(),
        "external_root": args.external_root,
        "condition": {
            "eyelid_thickness_mm": 1.25,
            "iop_mmhg": 0.0,
            "local_refine_level": 1,
            "np": 4,
            "equations": 2711583,
            "solver_mode": "in_core",
        },
        "stop": {
            "launcher_signal": campaign["launcher_signal"],
            "launcher_exit_code": 143,
            "inner_unit_final_state": "inactive/dead",
            "token_processes_after": int(containment["token_processes"]),
            "solver_processes_after": int(containment["solver_processes"]),
            "active_blueknow_units_after": int(containment["blueknow_running_units"]),
        },
        "numerical_state_at_stop": {
            "mapdl_error_count": int(status["mapdl_error_count"]),
            "completed_substeps": int(status["completed_substeps"]),
            "run_completed": bool(int(status["run_completed_count"])),
            "complete_endpoint": False,
            "accepted_endpoint": False,
            "eligible_for_scientific_comparison": False,
            "q_calculable": False,
        },
        "cleanup": {
            "files_deleted": int(cleanup["files"]),
            "apparent_bytes_deleted": int(cleanup["apparent_bytes"]),
            "remaining_manifest_entries": int(cleanup["remaining_manifest_entries"]),
            "policy": "Only incomplete RST/DB and solver scratch from attempt_1 were deleted after path, size, mtime, class, and SHA-256 capture.",
        },
        "artifacts": artifacts,
        "decision": "The IOP0 run was actively stopped at the user's request to prioritize IOP20. It is not a numerical failure, accepted endpoint, baseline force, or member of a pressure pair; it must be rerun from a new root before q can be calculated.",
    }
    args.output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
