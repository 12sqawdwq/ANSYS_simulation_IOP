#!/usr/bin/env python3
"""Build a deterministic provenance manifest for committed mesh-only P0 evidence."""
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
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.result_root.resolve()
    with (root / "preflight_manifest.csv").open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if {row["strategy"] for row in rows} != {"G015", "L010"}:
        raise ValueError("formal P0 must contain exactly G015 and L010")
    cases: dict[str, object] = {}
    for row in rows:
        cases[row["strategy"]] = {
            "status": row["status"],
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
                "path": row["source_dir"].rstrip("/") + f"/{row['strategy']}.db",
                "size_bytes": int(row["db_size_bytes"]),
                "sha256": row["db_sha256"],
            },
        }
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
        "status": "formal_committed_mesh_only_preflight_complete",
        "source_git_commit": args.source_commit,
        "external_root": args.external_root,
        "nonlinear_solution_started": False,
        "cases": cases,
        "artifacts": artifacts,
        "decision": {
            "G015": "mesh-only complete; more expensive than L010 while coarser in the target interfaces",
            "L010": "mesh-only complete and eligible for a separately authorized 2.00-mm 0/20-mmHg anchor pair",
            "L005": "development mesh-only evidence rejects a nonlinear solve under current resources; not part of formal P0",
        },
        "claim_boundary": "P0 validates committed mesh construction and planning resources only. It contains no force, q, or nonlinear convergence endpoint.",
    }
    args.output.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
