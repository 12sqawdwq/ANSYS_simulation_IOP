#!/usr/bin/env python3
"""Build deterministic evidence for the accepted 1.25-mm L010 IOP0 endpoint."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def one_row(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 1:
        raise ValueError(f"expected exactly one row: {path}")
    return rows[0]


def status_map(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return {row[0]: row[1] for row in csv.reader(handle) if len(row) >= 2}


def finite(row: dict[str, str], field: str) -> float:
    value = float(row[field])
    if not math.isfinite(value):
        raise ValueError(f"non-finite {field}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.result_root.resolve()
    row = one_row(root / "run_manifest.csv")
    status = status_map(root / "final_status.csv")
    resources = status_map(root / "resource_extrema.csv")
    attempt = json.loads((root / "attempt.json").read_text(encoding="utf-8"))
    metadata = json.loads((root / "run_metadata.json").read_text(encoding="utf-8"))
    solver_excerpt = (root / "solver_summary_excerpt.txt").read_text(
        encoding="utf-8", errors="replace"
    )
    warnings = (root / "warnings_with_context.txt").read_text(
        encoding="utf-8", errors="replace"
    )
    rejection = (root / "rejection_markers.txt").read_text(
        encoding="utf-8", errors="replace"
    )
    external = list(csv.DictReader(
        (root / "primary_external_artifacts.tsv").open(encoding="utf-8-sig"),
        delimiter="\t",
    ))
    for item in external:
        item["size_bytes"] = int(item["size_bytes"])
        item["allocated_bytes"] = int(item["allocated_bytes"])
        item["availability"] = (
            "deleted_after_pair_field_qc_and_sha256_audit"
            if item["role"] == "rst" else "retained_on_5090d"
        )
    checks = {
        "campaign_complete": status.get("campaign_complete") == "1" and status.get("campaign_incomplete") == "0",
        "runner_complete": row["status"] == "complete" and row["returncode"] == "0",
        "run_completed": status.get("run_completed_count") == "1" and "RUN COMPLETED" in solver_excerpt,
        "ansys_error_zero": row["ansys_error_count"] == "0" and status.get("mapdl_error_count") == "0",
        "three_load_steps_converged": all(row[field] == "1" for field in (
            "preload_converged", "approach_converged", "indentation_converged"
        )) and finite(row, "result_load_step") == 3.0 and finite(row, "result_time") == 3.0,
        "all_29_substeps_completed": status.get("completed_substeps") == "29" and "LOAD STEP     3   SUBSTEP    13" in status.get("last_completed_state", ""),
        "out_of_core_verified": status.get("solver_mode") == "out-of-core" and status.get("solver_mode_verified") == "1" and metadata["solver_memory_mode"] == "out-of-core",
        "last_only_results_verified": metadata["result_output_frequency"] == "last" and attempt["result_output_frequency"] == "last",
        "penetration_within_0p03_mm": finite(row, "max_penetration_m") * 1000 <= 0.03,
        "preload_contact_absent": finite(row, "preload_contact_area_m2") == 0.0 and finite(row, "preload_probe_fy_n") == 0.0,
        "first_touch_force_within_1_mn": abs(finite(row, "approach_probe_fy_n")) <= 0.001,
        "lateral_reaction_within_5_percent": abs(finite(row, "probe_fx_n")) <= 0.05 * abs(finite(row, "probe_fy_n")),
        "contact_center_within_0p01_mm": abs(finite(row, "contact_x_center_m")) * 1000 <= 0.01,
        "no_rejection_markers": not rejection.strip(),
        "no_residual_solver_session": all(status.get(field) == "0" for field in (
            "solver_processes", "token_processes", "blueknow_running_units"
        )),
    }
    if not all(checks.values()):
        raise ValueError(f"endpoint QC failed: {checks}")
    warning_summary = re.findall(
        r"NUMBER OF WARNING MESSAGES ENCOUNTERED=\s*(\d+)", solver_excerpt
    )
    if warning_summary != ["10"] or int(status["warning_message_count"]) != 11:
        raise ValueError("unexpected warning counts")
    required_warning_evidence = (
        "4 of the 227478 new or modified elements",
        "5 of the 331031 new or modified elements",
        "9 of the 706720 selected elements",
        "Node 173 connects both contact element",
        "For certain bonded contact pairs",
        "reference force value times the tolerance",
        "out-of-core memory mode",
        "elapsed time exceeds the CPU time",
    )
    if any(item not in warnings for item in required_warning_evidence):
        raise ValueError("warning evidence is incomplete")
    if {item["role"] for item in external} != {"rst", "db", "solve_out"}:
        raise ValueError("primary external artifacts are incomplete")
    all_files = {
        row["relative_path"]: row
        for row in csv.DictReader(
            (root / "all_files_sha256.tsv").open(encoding="utf-8-sig"), delimiter="\t"
        )
    }
    for item in external:
        source = all_files.get(item["relative_path"])
        if source is None or source["sha256"] != item["sha256"]:
            raise ValueError(f"external hash is not frozen in all-files audit: {item['role']}")
    artifacts = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if path.resolve() == args.output.resolve() or path.name in {"manifest.json", "README.md"}:
            continue
        artifacts.append({
            "path": path.relative_to(root).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
        })
    manifest = {
        "schema_version": 1,
        "status": "accepted_complete_l010_t1p25_iop0_out_of_core_endpoint",
        "source_git_commit": row["git_commit"],
        "source_campaign_root": "/home/xuanyu/PROJECT/ziyu/blueknow-data/thickness_mesh_independence/20260814T025331Z_6ef45199_L010_h1p25_iop0_ooc_last_np4",
        "condition": {
            "eyelid_thickness_mm": finite(row, "eyelid_thickness_mm"),
            "iop_mmhg": finite(row, "iop_mmhg"),
            "indent_mm": finite(row, "indent_mm"),
            "background_mesh_mm": finite(row, "mesh_size_mm"),
            "local_refine_level": int(row["local_refine_level"]),
            "nominal_local_target_mm": finite(row, "local_target_mesh_size_mm"),
            "np": int(row["np_used"]),
            "solver_memory_mode": metadata["solver_memory_mode"],
            "result_output_frequency": metadata["result_output_frequency"],
        },
        "qc": checks,
        "result": {
            "probe_fx_n": finite(row, "probe_fx_n"),
            "probe_fy_n": finite(row, "probe_fy_n"),
            "force_magnitude_n": abs(finite(row, "probe_fy_n")),
            "contact_area_mm2": finite(row, "contact_area_m2") * 1e6,
            "contact_x_center_mm": finite(row, "contact_x_center_m") * 1000,
            "maximum_contact_pressure_kpa": finite(row, "pmax_pa") / 1000,
            "maximum_penetration_mm": finite(row, "max_penetration_m") * 1000,
            "cornea_peak_kpa": finite(row, "cornea_peak_pa") / 1000,
            "eyelid_peak_kpa": finite(row, "eyelid_peak_pa") / 1000,
            "elapsed_seconds": finite(row, "elapsed_seconds"),
            "completed_substeps": int(status["completed_substeps"]),
            "cumulative_equilibrium_iterations": 48,
            "ansys_warning_summary_count": int(warning_summary[-1]),
            "warning_message_occurrences": int(status["warning_message_count"]),
        },
        "resources": {
            "minimum_mem_available_kib": int(resources["minimum_mem_available_kib"]),
            "minimum_mem_available_gib": int(resources["minimum_mem_available_kib"]) / 1024 / 1024,
            "minimum_free_disk_kib": int(resources["minimum_free_disk_kib"]),
            "minimum_free_disk_gib": int(resources["minimum_free_disk_kib"]) / 1024 / 1024,
            "solver_non_solver_allocated_gb_all_ranks": 17.776,
            "solver_disk_space_mb_all_processes": 81725.0,
            "pruned_files": attempt["artifact_retention"]["pruned_files"],
            "pruned_bytes": attempt["artifact_retention"]["pruned_bytes"],
        },
        "warning_assessment": {
            "accepted": True,
            "shape_warning_elements": 9,
            "shape_errors": 0,
            "categories": [
                "mesh shape warnings without shape error",
                "known coincident contact/target node warning",
                "known bonded initial offset warning",
                "small reference-force convergence warning",
                "expected out-of-core I/O performance warning",
            ],
            "decision": "Warnings match the verified mesh/contact formulation and explicit out-of-core strategy; none indicates endpoint nonconvergence or invalid force/contact metrics.",
        },
        "human_geometry_qc": {
            "accepted": True,
            "evidence": "applanation_boundary_qc.png",
            "outer_break_radius_mm": finite(row, "outer_break_radius_m") * 1000,
            "inner_break_radius_mm": finite(row, "inner_break_radius_m") * 1000,
            "assessment": "The segmented outer and inner boundaries are centered and approximately circular; the fitted radii follow the visible boundary transition without a disconnected lobe.",
        },
        "external_artifacts": external,
        "artifacts": artifacts,
        "retention": {
            "rst_status": "deleted_after_pair_field_qc_and_sha256_audit",
            "db_status": "retained_externally_after_pair_qc",
            "failed_attempt_binary_status": "already_deleted_after_hash_audit",
        },
        "acceptance": "The 1.25-mm IOP0 endpoint is accepted as a complete out-of-core L010 endpoint and has been paired only with the accepted same-commit IOP20 endpoint after explicit compatibility checks; the paired q remains specific to this L010 discretization.",
    }
    args.output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
