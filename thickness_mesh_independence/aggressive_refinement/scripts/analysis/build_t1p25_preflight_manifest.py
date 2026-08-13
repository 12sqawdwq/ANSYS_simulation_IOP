#!/usr/bin/env python3
"""Build lightweight provenance for the committed 1.25-mm L010 mesh preflight."""
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-root", type=Path, required=True)
    parser.add_argument("--external-root", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.result_root.resolve()
    rows = list(csv.DictReader((root / "preflight_manifest.csv").open(encoding="utf-8-sig")))
    indexed = {row["strategy"]: row for row in rows}
    if set(indexed) != {"G015", "L010"}:
        raise ValueError("preflight must contain G015 and L010")
    commit = (root / "source_git_commit.txt").read_text(encoding="utf-8").strip()
    baseline = json.loads((root / "model_baseline.json").read_text(encoding="utf-8"))
    if baseline["canonical_baseline"]["eyelid_thickness_mm"] != 1.25:
        raise ValueError("preflight did not freeze the 1.25-mm baseline")
    cases = {}
    for name, row in indexed.items():
        driver = (root / name / "driver.dat").read_text(encoding="utf-8")
        if ",0.00125," not in driver:
            raise ValueError(f"{name} driver does not use 1.25 mm")
        case = {
            "status": row["status"],
            "eyelid_thickness_mm": 1.25,
            "background_mesh_mm": float(row["background_mesh_mm"]),
            "nominal_local_target_mm": float(row["nominal_local_target_mm"]),
            "refinement_level": int(row["refinement_level"]),
            "selected_parent_elements": int(row["selected_parent_elements"]),
            "solid_elements_before": int(row["solid_elements_before"]),
            "solid_elements_after": int(row["solid_elements_after"]),
            "solid_nodes_before": int(row["solid_nodes_before"]),
            "solid_nodes_after": int(row["solid_nodes_after"]),
            "mapdl_error_count": int(row["mapdl_error_count"]),
            "mapdl_warning_count": int(row["mapdl_warning_count"]),
            "shape_warning_elements": int(row["shape_warning_elements"]),
            "shape_error_elements": int(row["shape_error_elements"]),
            "run_completed": row["run_completed"].lower() == "true",
            "wall_seconds": float(row["wall_seconds"]),
            "maximum_rss_kib": int(row["maximum_rss_kib"]),
            "external_db": {
                "path": row["source_dir"].rstrip("/") + f"/{name}.db",
                "size_bytes": int(row["db_size_bytes"]),
                "sha256": row["db_sha256"],
            },
        }
        if not (case["status"] == "complete" and case["run_completed"] and case["mapdl_error_count"] == 0 and case["shape_error_elements"] == 0):
            raise ValueError(f"{name} did not pass mesh preflight")
        cases[name] = case
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
        "status": "formal_t1p25_mesh_only_preflight_complete",
        "source_git_commit": commit,
        "external_root": args.external_root,
        "global_baseline_eyelid_thickness_mm": 1.25,
        "nonlinear_solution_started": False,
        "cases": cases,
        "artifacts": artifacts,
        "decision": "The 1.25-mm L010 mesh is committed, complete, and has zero MAPDL and shape errors. It is eligible for the separately guarded IOP0 solve; this preflight itself is not a numerical endpoint.",
    }
    args.output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
