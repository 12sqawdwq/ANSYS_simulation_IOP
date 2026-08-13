#!/usr/bin/env python3
"""Build lightweight, deterministic evidence for the accepted L010 H2.00 IOP0 endpoint."""
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
    if not value == value or value in (float("inf"), float("-inf")):
        raise ValueError(f"non-finite {field}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-root", type=Path, required=True)
    parser.add_argument("--solve-out", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.result_root.resolve()
    solve = args.solve_out.resolve()
    row = one_row(root / "iop0_run_manifest.csv")
    attempt = json.loads((root / "attempt.json").read_text(encoding="utf-8"))
    status = status_map(root / "source_campaign_status.csv")
    live = status_map(root / "post_completion_live_audit.csv")
    external = list(csv.DictReader((root / "external_artifacts.csv").open(encoding="utf-8-sig")))
    for item in external:
        item["size_bytes"] = int(item["size_bytes"])
        item["allocated_bytes"] = int(item["allocated_bytes"])
    text = solve.read_text(errors="replace")
    required_external_roles = {
        "rst", "db", "solve_out", "run_manifest", "run_metadata",
        "resource_monitor", "campaign_status",
    }
    if {item["role"] for item in external} != required_external_roles:
        raise ValueError("external artifact roles are incomplete")
    if sha256(solve) != next(item["sha256"] for item in external if item["role"] == "solve_out"):
        raise ValueError("solve.out hash does not match external evidence")
    checks = {
        "campaign_complete": status.get("iop0_returncode") == "0",
        "runner_complete": row["status"] == "complete" and row["returncode"] == "0",
        "run_completed": "RUN COMPLETED" in text,
        "ansys_error_zero": int(row["ansys_error_count"]) == 0 and "NUMBER OF ERROR   MESSAGES ENCOUNTERED=          0" in text,
        "three_load_steps_converged": all(row[field] == "1" for field in ("preload_converged", "approach_converged", "indentation_converged")) and finite(row, "result_load_step") == 3.0,
        "penetration_within_0p03_mm": finite(row, "max_penetration_m") * 1000 <= 0.03,
        "preload_contact_absent": finite(row, "preload_contact_area_m2") == 0.0 and finite(row, "preload_probe_fy_n") == 0.0,
        "first_touch_force_within_1_mn": abs(finite(row, "approach_probe_fy_n")) <= 0.001,
        "no_residual_solver_session": all(live.get(field) == "0" for field in ("campaign_token_residual_processes", "named_solver_mpi_processes", "active_blueknow_units")),
    }
    if not all(checks.values()):
        raise ValueError(f"endpoint QC failed: {checks}")
    monitor_rows = list(csv.reader((root / "resource_monitor.csv").open(encoding="utf-8-sig")))
    min_mem_kib = min(int(item[2]) for item in monitor_rows)
    min_disk_kib = min(int(item[3]) for item in monitor_rows)
    artifacts = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if path.resolve() == args.output.resolve():
            continue
        artifacts.append({
            "path": path.relative_to(root).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
        })
    warning_matches = re.findall(
        r"NUMBER OF WARNING MESSAGES ENCOUNTERED=\s*(\d+)", text
    )
    if not warning_matches:
        raise ValueError("MAPDL warning summary is missing")
    rst_path = next(item["path"] for item in external if item["role"] == "rst")
    source_campaign_root = rst_path.split("/iop0/", 1)[0]
    manifest = {
        "schema_version": 1,
        "status": "accepted_complete_l010_h2p00_iop0_endpoint",
        "source_git_commit": row["git_commit"],
        "source_campaign_root": source_campaign_root,
        "condition": {
            "eyelid_thickness_mm": finite(row, "eyelid_thickness_mm"),
            "iop_mmhg": finite(row, "iop_mmhg"),
            "indent_mm": finite(row, "indent_mm"),
            "background_mesh_mm": finite(row, "mesh_size_mm"),
            "local_refine_level": int(row["local_refine_level"]),
            "nominal_local_target_mm": finite(row, "local_target_mesh_size_mm"),
            "np": int(row["np_used"]),
        },
        "qc": checks,
        "result": {
            "probe_fy_n": finite(row, "probe_fy_n"),
            "contact_area_mm2": finite(row, "contact_area_m2") * 1e6,
            "maximum_contact_pressure_kpa": finite(row, "pmax_pa") / 1000,
            "maximum_penetration_mm": finite(row, "max_penetration_m") * 1000,
            "cornea_peak_kpa": finite(row, "cornea_peak_pa") / 1000,
            "eyelid_peak_kpa": finite(row, "eyelid_peak_pa") / 1000,
            "elapsed_seconds": finite(row, "elapsed_seconds"),
            "ansys_warning_count": int(warning_matches[-1]),
        },
        "resources": {
            "minimum_mem_available_kib": min_mem_kib,
            "minimum_free_disk_kib": min_disk_kib,
            "pruned_files": attempt["artifact_retention"]["pruned_files"],
            "pruned_bytes": attempt["artifact_retention"]["pruned_bytes"],
        },
        "external_artifacts": external,
        "artifacts": artifacts,
        "acceptance": "The IOP0 endpoint is accepted as a 2.00-mm explicit thickness override. It is not a 1.25-mm baseline endpoint and does not authorize or provide IOP20 or q.",
    }
    args.output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
