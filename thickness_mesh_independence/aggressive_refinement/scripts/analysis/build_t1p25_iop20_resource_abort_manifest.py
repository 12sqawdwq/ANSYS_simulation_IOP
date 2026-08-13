#!/usr/bin/env python3
"""Build lightweight provenance for the near-endpoint 1.25-mm IOP20 resource abort."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
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


def monitor_summary(path: Path) -> dict[str, object]:
    rows = []
    for row in csv.reader(path.open(encoding="utf-8", newline="")):
        if len(row) == 4:
            rows.append((row[0], int(row[2]), int(row[3])))
    if not rows:
        raise ValueError("resource monitor is empty")
    minimum_memory = min(rows, key=lambda item: item[1])
    minimum_disk = min(rows, key=lambda item: item[2])
    return {
        "samples": len(rows),
        "first_utc": rows[0][0],
        "last_utc": rows[-1][0],
        "minimum_mem_available_kib": minimum_memory[1],
        "minimum_mem_available_gib": minimum_memory[1] / 1024 / 1024,
        "minimum_free_disk_kib": minimum_disk[2],
        "minimum_free_disk_gib": minimum_disk[2] / 1024 / 1024,
    }


def selected_binary_stats(path: Path) -> tuple[int, int, int]:
    rows = list(csv.DictReader(path.open(encoding="utf-8", newline=""), delimiter="\t"))
    return (
        len(rows),
        sum(int(row["size_bytes"]) for row in rows),
        sum(int(row["allocated_bytes"]) for row in rows),
    )


def parse_substeps(solve_text: str) -> dict[int, list[tuple[int, int, float]]]:
    pattern = re.compile(
        r"\*\*\* LOAD STEP\s+(\d+)\s+SUBSTEP\s+(\d+)\s+COMPLETED\.\s+"
        r"CUM ITER =\s+(\d+)\s*\n \*\*\* TIME =\s+([0-9.E+-]+)"
    )
    result: dict[int, list[tuple[int, int, float]]] = {}
    for match in pattern.finditer(solve_text):
        load_step = int(match.group(1))
        result.setdefault(load_step, []).append(
            (int(match.group(2)), int(match.group(3)), float(match.group(4)))
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-root", type=Path, required=True)
    parser.add_argument("--external-root", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.result_root.resolve()
    attempt = root / "iop20" / "eyelid_1p25mm_indent_0p28mm" / "attempt_1"
    audit = root / "resource_abort_audit"
    solve_path = attempt / "solve.out"
    solve_text = solve_path.read_text(encoding="utf-8", errors="replace")
    upper_solve = solve_text.upper()
    source_commit = (root / "source_git_commit.txt").read_text(encoding="utf-8").strip()
    campaign = two_column_csv(root / "campaign_status.csv")
    final_status = two_column_csv(audit / "final_status.csv")
    cleanup = two_column_csv(audit / "cleanup_summary.csv")
    supplemental = two_column_csv(audit / "supplemental_cleanup_summary.csv")
    residual = two_column_csv(audit / "supplemental_dsp_residual_cleanup_summary.csv")
    metadata = json.loads((root / "iop20" / "run_metadata.json").read_text(encoding="utf-8"))
    substeps = parse_substeps(solve_text)
    if source_commit != "5d3ece4bccf67e382bdfa639b0da80711c8008b8":
        raise ValueError("unexpected source commit")
    if final_status["classification"] != "resource_guard_abort_near_endpoint_with_converged_intermediate_states":
        raise ValueError("unexpected abort classification")
    if any(int(final_status[key]) for key in ("solver_processes", "token_processes", "blueknow_running_units")):
        raise ValueError("session containment audit has residual activity")
    if metadata["iop_mmhg"] != 20 or [case["eyelid_thickness_mm"] for case in metadata["cases"]] != [1.25]:
        raise ValueError("resource-abort evidence is not the 1.25-mm IOP20 case")
    if "IN-CORE MEMORY MODE" not in upper_solve or "RUN COMPLETED" in upper_solve:
        raise ValueError("solver mode/completion state does not match the resource abort")
    if [len(substeps.get(step, [])) for step in (1, 2, 3)] != [8, 8, 12]:
        raise ValueError("unexpected completed-substep counts")
    if substeps[3][-1] != (12, 54, 2.92813):
        raise ValueError("unexpected final converged state")
    cleanup_manifests = [
        audit / "deleted_binary_manifest.tsv",
        audit / "supplemental_deleted_binary_manifest.tsv",
        audit / "supplemental_dsp_residual_deleted_manifest.tsv",
    ]
    cleanup_stats = [selected_binary_stats(path) for path in cleanup_manifests]
    if int(cleanup["remaining_manifest_entries"]) or int(supplemental["remaining_entries"]) or int(residual["remaining_entries"]):
        raise ValueError("cleanup left selected files behind")
    abort_row = next(csv.reader((root / "resource_abort.csv").open(encoding="utf-8", newline="")))
    resources = monitor_summary(root / "resource_monitor.csv")
    artifacts = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if (
            path.resolve() == args.output.resolve()
            or path.name in {"manifest.json", "README.md"}
        ):
            continue
        artifacts.append({
            "path": path.relative_to(root).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
        })
    manifest = {
        "schema_version": 1,
        "status": "resource_guard_abort_near_endpoint_with_converged_intermediate_states",
        "classification": "resource_guard_abort_near_endpoint_with_converged_intermediate_states",
        "source_git_commit": source_commit,
        "external_root": args.external_root,
        "condition": {
            "eyelid_thickness_mm": 1.25,
            "iop_mmhg": 20.0,
            "indent_mm": 0.28,
            "background_mesh_mm": 0.20,
            "local_refine_level": 1,
            "nominal_local_target_mm": 0.10,
            "np": 4,
            "equations": 2711583,
            "solver_mode": "in_core",
        },
        "resource_abort": {
            "utc": abort_row[0],
            "reason": "available_memory_below_30_gib_floor",
            "trigger_mem_available_kib": int(abort_row[3]),
            "trigger_mem_available_gib": int(abort_row[3]) / 1024 / 1024,
            "trigger_free_disk_kib": int(abort_row[4]),
            "launcher_returncode": int(campaign["iop20_returncode"]),
            **resources,
        },
        "numerical_state_at_abort": {
            "load_step_completed_substeps": {str(step): len(substeps[step]) for step in (1, 2, 3)},
            "completed_substeps_total": sum(len(substeps[step]) for step in (1, 2, 3)),
            "cumulative_equilibrium_iterations": substeps[3][-1][1],
            "last_converged_pseudotime": 2.928125,
            "last_converged_indentation_mm": 0.259875,
            "remaining_indentation_mm": 0.020125,
            "mapdl_error_count": upper_solve.count("*** ERROR ***"),
            "nonconvergence_markers": sum(upper_solve.count(marker) for marker in (
                "SOLUTION NOT CONVERGED", "THE SOLUTION WAS NOT CONVERGED", "CONVERGENCE FAILURE"
            )),
            "bisection_markers": upper_solve.count("BISECTION"),
            "cutback_markers": upper_solve.count("CUTBACK"),
            "negative_pivot_markers": upper_solve.count("NEGATIVE PIVOT"),
            "shape_error_markers": upper_solve.count("SHAPE ERROR"),
            "shape_warning_elements": 9,
            "warning_messages": upper_solve.count("*** WARNING ***"),
            "run_completed": False,
            "complete_endpoint": False,
            "accepted_endpoint": False,
            "eligible_for_scientific_comparison": False,
            "formal_f20_available": False,
            "q_calculable": False,
        },
        "containment": {
            "inner_unit_final_state": "inactive/dead",
            "solver_processes_after": int(final_status["solver_processes"]),
            "token_processes_after": int(final_status["token_processes"]),
            "active_blueknow_units_after": int(final_status["blueknow_running_units"]),
        },
        "cleanup": {
            "files_deleted": sum(item[0] for item in cleanup_stats),
            "apparent_bytes_deleted": sum(item[1] for item in cleanup_stats),
            "allocated_bytes_deleted": sum(item[2] for item in cleanup_stats),
            "remaining_selected_files": 0,
            "policy": "Only incomplete DB/RST and reproducible solver scratch from the failed attempt_1 were deleted after path, size, mtime, class, and SHA-256 capture.",
        },
        "restart_decision": {
            "old_binary_restart_authorized": False,
            "same_in_core_strategy_authorized": False,
            "new_root_required": True,
            "strategy": "Explicit out-of-core sparse solve with only the last result of each load step stored; retain the existing resource floors and verify out-of-core from solve.out during the run.",
        },
        "artifacts": artifacts,
        "decision": "The intermediate states establish a stable converged path but not the 0.28-mm IOP20 endpoint. No formal F20 or q may be extracted. Rerun from a new root with the resource-controlled out-of-core strategy.",
    }
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
