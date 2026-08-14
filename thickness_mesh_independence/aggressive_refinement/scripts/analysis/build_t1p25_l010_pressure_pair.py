#!/usr/bin/env python3
"""Pair accepted 1.25-mm L010 IOP0/IOP20 endpoints and compute q20."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

PROBE_AREA_MM2 = 14.65741468458854
PA_PER_MMHG = 133.32236842105263
EXPECTED_COMMIT = "6ef45199bec06139538c5a68a1538ae683ea1c3b"


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


def finite(row: dict[str, str], field: str) -> float:
    value = float(row[field])
    if not math.isfinite(value):
        raise ValueError(f"non-finite {field}")
    return value


def write_csv(path: Path, row: dict[str, object]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iop0-root", type=Path, required=True)
    parser.add_argument("--iop20-root", type=Path, required=True)
    parser.add_argument("--coarse-reference-csv", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    iop0_root = args.iop0_root.resolve()
    iop20_root = args.iop20_root.resolve()
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    manifest0_path = iop0_root / "manifest.json"
    manifest20_path = iop20_root / "manifest.json"
    manifest0 = json.loads(manifest0_path.read_text(encoding="utf-8"))
    manifest20 = json.loads(manifest20_path.read_text(encoding="utf-8"))
    row0 = one_row(iop0_root / "run_manifest.csv")
    row20 = one_row(iop20_root / "run_manifest.csv")
    metadata0 = json.loads((iop0_root / "run_metadata.json").read_text(encoding="utf-8"))
    metadata20 = json.loads((iop20_root / "run_metadata.json").read_text(encoding="utf-8"))
    accepted_statuses = {
        manifest0["status"], manifest20["status"]
    } == {
        "accepted_complete_l010_t1p25_iop0_out_of_core_endpoint",
        "accepted_complete_l010_t1p25_iop20_out_of_core_endpoint",
    }
    exact_fields = (
        "eyelid_thickness_mm", "cornea_thickness_mm", "indent_mm", "mesh_size_mm",
        "local_refine_level", "local_refine_halfwidth_mm", "local_target_mesh_size_mm",
        "eyelid_material_scale", "cornea_material_scale", "eyelid_c10_mpa",
        "eyelid_c01_mpa", "eyelid_d1_pa_inv", "cornea_c10_mpa", "cornea_c01_mpa",
        "cornea_d1_pa_inv", "initial_gap_m", "np_used", "git_commit", "git_dirty",
    )
    matching_fields = all(row0[field] == row20[field] for field in exact_fields)
    checks = {
        "both_endpoints_accepted": accepted_statuses,
        "same_source_commit": manifest0["source_git_commit"] == manifest20["source_git_commit"] == EXPECTED_COMMIT,
        "same_geometry_material_mesh_and_parallelism": matching_fields,
        "only_pressure_differs": finite(row0, "iop_mmhg") == 0.0 and finite(row20, "iop_mmhg") == 20.0,
        "same_mesh_inventory": sha256(iop0_root / "aggressive_mesh_inventory.csv") == sha256(iop20_root / "aggressive_mesh_inventory.csv"),
        "same_apdl_inputs": metadata0["apdl_sha256"] == metadata20["apdl_sha256"],
        "same_global_baseline": metadata0["global_baseline"] == metadata20["global_baseline"],
        "same_solver_and_result_strategy": all(
            metadata0[field] == metadata20[field] == expected
            for field, expected in (
                ("solver_memory_mode", "out-of-core"),
                ("result_output_frequency", "last"),
                ("np", 4),
                ("retry_count", 0),
                ("view_policy", "none"),
            )
        ),
        "three_load_steps_each": all(
            row[field] == "1"
            for row in (row0, row20)
            for field in ("preload_converged", "approach_converged", "indentation_converged")
        ),
        "same_endpoint_load_state": all(
            finite(row, "result_load_step") == 3.0 and finite(row, "result_time") == 3.0
            for row in (row0, row20)
        ),
        "ansys_error_zero_each": row0["ansys_error_count"] == row20["ansys_error_count"] == "0",
        "force_increment_positive": abs(finite(row20, "probe_fy_n")) > abs(finite(row0, "probe_fy_n")),
    }
    if not all(checks.values()):
        raise ValueError(f"pressure-pair QC failed: {checks}")
    force0 = abs(finite(row0, "probe_fy_n"))
    force20 = abs(finite(row20, "probe_fy_n"))
    delta_force = force20 - force0
    delta_pressure_pa = delta_force / (PROBE_AREA_MM2 * 1e-6)
    q_mmhg = delta_pressure_pa / PA_PER_MMHG
    if q_mmhg <= 0:
        raise ValueError("q20 must be positive after the force-magnitude convention")
    with args.coarse_reference_csv.open(newline="", encoding="utf-8-sig") as handle:
        reference_rows = list(csv.DictReader(handle))
    candidates = [
        item for item in reference_rows
        if item.get("output") == "P_probe_delta_at_20"
        and float(item["reference_thickness_mm"]) == 1.25
        and item.get("unit") == "mmHg"
    ]
    if len(candidates) != 1:
        raise ValueError("expected one 1.25-mm coarse q reference")
    coarse_q = float(candidates[0]["reference_value"])
    coarse_change_percent = 100.0 * (q_mmhg / coarse_q - 1.0)
    pair_row = {
        "eyelid_thickness_mm": finite(row0, "eyelid_thickness_mm"),
        "iop0_mmhg": finite(row0, "iop_mmhg"),
        "iop20_mmhg": finite(row20, "iop_mmhg"),
        "indent_mm": finite(row0, "indent_mm"),
        "background_mesh_mm": finite(row0, "mesh_size_mm"),
        "local_refine_level": int(row0["local_refine_level"]),
        "nominal_local_target_mm": finite(row0, "local_target_mesh_size_mm"),
        "force0_magnitude_n": force0,
        "force20_magnitude_n": force20,
        "delta_force_n": delta_force,
        "probe_area_mm2": PROBE_AREA_MM2,
        "delta_probe_pressure_pa": delta_pressure_pa,
        "q20_mmhg": q_mmhg,
        "coarse_global_0p30_q20_mmhg": coarse_q,
        "l010_change_from_coarse_global_0p30_percent": coarse_change_percent,
        "pair_qc_pass": 1,
        "source_git_commit": EXPECTED_COMMIT,
    }
    pair_csv = output_root / "pressure_pair.csv"
    write_csv(pair_csv, pair_row)
    field_root = output_root / "field_qc"
    with (field_root / "status.csv").open(newline="", encoding="utf-8-sig") as handle:
        field_status_map = {row[0]: row[1] for row in csv.reader(handle) if len(row) >= 2}
    with (field_root / "artifact_manifest.tsv").open(newline="", encoding="utf-8-sig") as handle:
        field_external = {row["role"]: row for row in csv.DictReader(handle, delimiter="\t")}
    for item in field_external.values():
        item["size_bytes"] = int(item["size_bytes"])
    field_checks = {
        "iop0_mapdl_error_zero": field_status_map.get("iop0_mapdl_error_count") == "0",
        "iop20_mapdl_error_zero": field_status_map.get("iop20_mapdl_error_count") == "0",
        "nine_native_views_each": field_status_map.get("iop0_png_count") == field_status_map.get("iop20_png_count") == "9",
        "load_step_3_time_3p0": field_status_map.get("result_state") == "load_step_3_time_3p0",
        "native_auto_scale_view_007": field_status_map.get("view_policy") == "native_auto_scale_plot_sweep_views_007",
        "no_residual_postprocess_session": field_status_map.get("solver_processes_after") == field_status_map.get("running_blueknow_units_after") == "0",
        "iop0_007_hash_matches_external_root": sha256(field_root / "central_section_iop0_007.png") == field_external["iop0_central_007"]["sha256"],
        "iop20_007_hash_matches_external_root": sha256(field_root / "central_section_iop20_007.png") == field_external["iop20_central_007"]["sha256"],
    }
    if not all(field_checks.values()):
        raise ValueError(f"field QC failed: {field_checks}")
    cleanup_root = field_root / "rst_cleanup"
    with (cleanup_root / "cleanup_summary.csv").open(newline="", encoding="utf-8-sig") as handle:
        cleanup_status = {row[0]: row[1] for row in csv.reader(handle) if len(row) >= 2}
    with (cleanup_root / "deleted_rst_manifest.tsv").open(newline="", encoding="utf-8-sig") as handle:
        deleted_rst = {row["role"]: row for row in csv.DictReader(handle, delimiter="\t")}
    cleanup_hashes = {}
    for line in (cleanup_root / "sha256.txt").read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        cleanup_hashes[name] = digest
    cleanup_checks = {
        "two_rst_files_deleted": cleanup_status.get("deleted_file_count") == "2",
        "rst_files_absent_after": cleanup_status.get("iop0_rst_remaining") == cleanup_status.get("iop20_rst_remaining") == "0",
        "db_files_retained": cleanup_status.get("iop0_db_retained") == cleanup_status.get("iop20_db_retained") == "1",
        "no_residual_cleanup_session": cleanup_status.get("solver_processes_after") == cleanup_status.get("running_blueknow_units_after") == "0",
        "deleted_iop0_rst_hash_matches_field_provenance": deleted_rst["iop0"]["sha256"] == field_external["iop0_source_rst"]["sha256"],
        "deleted_iop20_rst_hash_matches_field_provenance": deleted_rst["iop20"]["sha256"] == field_external["iop20_source_rst"]["sha256"],
        "cleanup_files_hash_complete": all(sha256(cleanup_root / name) == digest for name, digest in cleanup_hashes.items()),
    }
    if not all(cleanup_checks.values()):
        raise ValueError(f"RST cleanup audit failed: {cleanup_checks}")
    source_artifacts = [
        {
            "role": "accepted_iop0_manifest",
            "path": manifest0_path.relative_to(Path.cwd()).as_posix(),
            "size_bytes": manifest0_path.stat().st_size,
            "sha256": sha256(manifest0_path),
        },
        {
            "role": "accepted_iop20_manifest",
            "path": manifest20_path.relative_to(Path.cwd()).as_posix(),
            "size_bytes": manifest20_path.stat().st_size,
            "sha256": sha256(manifest20_path),
        },
        {
            "role": "coarse_global_0p30_reference",
            "path": args.coarse_reference_csv.resolve().relative_to(Path.cwd()).as_posix(),
            "size_bytes": args.coarse_reference_csv.stat().st_size,
            "sha256": sha256(args.coarse_reference_csv),
        },
    ]
    manifest = {
        "schema_version": 1,
        "status": "accepted_complete_l010_t1p25_iop0_iop20_pressure_pair",
        "source_git_commit": EXPECTED_COMMIT,
        "pair_qc": checks,
        "definition": {
            "formula": "q20=(|probe_fy_iop20|-|probe_fy_iop0|)/(A_probe*Pa_per_mmHg)",
            "force_semantics": "F is the positive indentation-force magnitude; raw MAPDL probe_fy is negative under the model coordinate convention.",
            "probe_area_mm2": PROBE_AREA_MM2,
            "pa_per_mmhg": PA_PER_MMHG,
        },
        "result": pair_row,
        "endpoint_differences": {
            "contact_area_change_mm2": manifest20["result"]["contact_area_mm2"] - manifest0["result"]["contact_area_mm2"],
            "maximum_contact_pressure_change_kpa": manifest20["result"]["maximum_contact_pressure_kpa"] - manifest0["result"]["maximum_contact_pressure_kpa"],
            "maximum_penetration_change_mm": manifest20["result"]["maximum_penetration_mm"] - manifest0["result"]["maximum_penetration_mm"],
        },
        "field_qc": {
            "checks": field_checks,
            "external_root": "/home/xuanyu/PROJECT/ziyu/blueknow-data/thickness_mesh_independence/20260814T085004Z_6ef45199_L010_h1p25_iop0_iop20_field_qc",
            "authoritative_view": "007 actual-scale deformed central section with native automatic colour scale",
            "visual_assessment": "Both endpoint sections are centered and mechanically continuous. IOP20 shows a coherent redistribution and a higher native maximum equivalent stress (44.488 kPa versus 40.366 kPa); native scales are intentionally not forced equal.",
            "external_artifacts": [field_external[key] for key in sorted(field_external)],
        },
        "rst_cleanup": {
            "checks": cleanup_checks,
            "authorization": cleanup_status["authorization"],
            "reason": cleanup_status["reason"],
            "apparent_bytes_deleted": int(cleanup_status["apparent_bytes_deleted"]),
            "allocated_bytes_deleted": int(cleanup_status["allocated_bytes_deleted"]),
            "db_retention": "Both endpoint DB files remain on 5090d with verified SHA-256.",
            "audit_path": "field_qc/rst_cleanup/cleanup_summary.csv",
        },
        "coarse_reference_comparison": {
            "comparison_role": "directional_mesh_sensitivity_context_not_a_formal_two_percent_convergence_test",
            "global_0p30_q20_mmhg": coarse_q,
            "l010_q20_mmhg": q_mmhg,
            "l010_change_from_global_0p30_percent": coarse_change_percent,
            "interpretation": "The L010 pair is internally valid, but a single contact-refined pair cannot establish absolute mesh independence. Its material difference from the existing global-0.30 result reinforces the existing amplitude-nonconvergence warning.",
        },
        "source_artifacts": source_artifacts,
        "artifacts": [
            {
                "path": path.relative_to(output_root).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in sorted(item for item in output_root.rglob("*") if item.is_file())
            if path.name not in {"manifest.json", "README.md"}
        ],
        "claim_boundary": "This result is the accepted q20 for the L010 discretization at 1.25 mm and 0.28 mm indentation. It is not a mesh-independent tissue threshold, a production calibration, or an independent validation of the pressure algorithm.",
    }
    (output_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
