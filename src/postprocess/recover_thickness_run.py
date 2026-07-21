#!/usr/bin/env python3
"""Recover completed thickness cases after the supervising runner was interrupted."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.postprocess.thickness_geometry import analyze_files, write_results as write_geometry_results
from src.runners.run_indentation_sweep import (
    GAP_M,
    MANIFEST_FIELDS,
    CaseSpec,
    atomic_json,
    atomic_manifest,
    prune_attempt,
    utc_now,
    validate_attempt,
)


def read_manifest(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def elapsed_seconds(attempt: Path) -> float:
    driver = attempt / "driver.dat"
    output = attempt / "solve.out"
    if not driver.exists() or not output.exists():
        return 0.0
    return max(0.0, output.stat().st_mtime - driver.stat().st_mtime)


def build_row(
    case: CaseSpec,
    metadata: dict,
    attempt: Path,
    outcome,
    elapsed: float,
) -> dict:
    row = {field: "" for field in MANIFEST_FIELDS}
    row.update({
        "case": case.name,
        "profile": metadata.get("profile", "thickness"),
        "offset_mm": case.offset_mm,
        "indent_mm": case.indent_mm,
        "eyelid_thickness_mm": case.eyelid_thickness_mm,
        "cornea_thickness_mm": 0.6,
        "mesh_size_mm": metadata.get("mesh_size_mm", 0.3),
        "status": outcome.status,
        "failure_reason": outcome.reason,
        "attempt_count": 1,
        "selected_attempt": 1,
        "np_used": metadata.get("np", ""),
        "returncode": 0,
        "started_at_utc": metadata.get("started_at_utc", ""),
        "ended_at_utc": utc_now(),
        "elapsed_seconds": round(elapsed, 3),
        "timeout_seconds": metadata.get("timeout_seconds", ""),
        "ansys_error_count": outcome.error_count,
        "views_count": outcome.views_count,
        "artifact_pruned_files": outcome.artifact_pruned_files,
        "artifact_pruned_bytes": outcome.artifact_pruned_bytes,
        "artifact_prune_error": outcome.artifact_prune_error,
        "commanded_push_m": GAP_M + case.indent_mm / 1000.0,
        "attempt_dir": str(attempt.relative_to(Path(metadata["run_root"]))),
        "git_commit": metadata.get("git_commit", ""),
        "git_dirty": str(metadata.get("git_dirty", False)).lower(),
    })
    row.update(outcome.metrics)
    if outcome.rst_path is not None:
        row["result_rst"] = str(outcome.rst_path.relative_to(Path(metadata["run_root"])))
    return row


def recover(run_root: Path) -> tuple[int, int]:
    run_root = run_root.expanduser().resolve()
    metadata_path = run_root / "run_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["run_root"] = str(run_root)

    rows_by_case = {
        row["case"]: row
        for row in read_manifest(run_root / "run_manifest.csv")
        if row.get("status") == "complete"
    }
    cases = [
        CaseSpec(
            float(item["offset_mm"]),
            float(item["indent_mm"]),
            index,
            float(item["eyelid_thickness_mm"]),
            "thickness",
        )
        for index, item in enumerate(metadata["cases"])
    ]
    recovered: list[str] = []
    incomplete: list[str] = []

    for case in cases:
        if case.name in rows_by_case:
            continue
        attempt = run_root / case.name / "attempt_1"
        solve_output = attempt / "solve.out"
        output = solve_output.read_text(errors="replace") if solve_output.exists() else ""
        if "RUN COMPLETED" not in output.upper():
            incomplete.append(case.name)
            continue
        geometry = analyze_files(
            attempt / "inner_preload_faces.csv",
            attempt / "inner_final_faces.csv",
        )
        write_geometry_results(attempt, geometry)
        elapsed = elapsed_seconds(attempt)
        outcome = validate_attempt(attempt, case, 0, False, elapsed)
        if outcome.status == "complete":
            try:
                stats = prune_attempt(attempt, case.name, keep_primary_results=True)
                outcome.artifact_pruned_files = stats.files_selected
                outcome.artifact_pruned_bytes = stats.bytes_selected
            except OSError as error:
                outcome.artifact_prune_error = str(error)
        row = build_row(case, metadata, attempt, outcome, elapsed)
        rows_by_case[case.name] = row
        if outcome.status == "complete":
            recovered.append(case.name)
        else:
            incomplete.append(case.name)

    order = {case.name: case.order for case in cases}
    rows = list(rows_by_case.values())
    atomic_manifest(run_root / "run_manifest.csv", rows, order)
    complete = sum(row.get("status") == "complete" for row in rows)
    metadata.update({
        "ended_at_utc": utc_now(),
        "completed_cases": complete,
        "failed_cases": len(cases) - complete,
        "recovery": {
            "reason": "supervisor stopped before timeout while MAPDL children continued",
            "recovered_cases": recovered,
            "incomplete_cases": incomplete,
        },
    })
    atomic_json(metadata_path, metadata)
    print(f"complete={complete} expected={len(cases)} recovered={len(recovered)}")
    for case in incomplete:
        print(f"incomplete={case}")
    return complete, len(cases)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_root", type=Path)
    cli = parser.parse_args()
    complete, expected = recover(cli.run_root)
    return 0 if complete == expected else 1


if __name__ == "__main__":
    raise SystemExit(main())
