#!/usr/bin/env python3
"""Collect lightweight records from aggressive mesh-only MAPDL preflights."""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
from pathlib import Path

FIELDS = (
    "strategy",
    "status",
    "background_mesh_mm",
    "nominal_local_target_mm",
    "refinement_halfwidth_mm",
    "refinement_level",
    "selected_parent_elements",
    "solid_elements_before",
    "solid_elements_after",
    "solid_nodes_before",
    "solid_nodes_after",
    "element_growth_ratio",
    "node_growth_ratio",
    "mapdl_error_count",
    "mapdl_warning_count",
    "shape_warning_elements",
    "shape_error_elements",
    "run_completed",
    "wall_seconds",
    "maximum_rss_kib",
    "db_size_bytes",
    "db_sha256",
    "source_dir",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def last_int(pattern: str, text: str, default: int = -1) -> int:
    matches = re.findall(pattern, text, flags=re.IGNORECASE)
    return int(matches[-1]) if matches else default


def parse_time(text: str) -> tuple[float, int]:
    rss = last_int(r"Maximum resident set size \(kbytes\):\s*(\d+)", text)
    match = re.search(r"Elapsed \(wall clock\) time \(h:mm:ss or m:ss\):\s*([^\s]+)", text)
    if not match:
        return -1.0, rss
    parts = [float(item) for item in match.group(1).split(":")]
    if len(parts) == 2:
        seconds = parts[0] * 60 + parts[1]
    elif len(parts) == 3:
        seconds = parts[0] * 3600 + parts[1] * 60 + parts[2]
    else:
        seconds = -1.0
    return seconds, rss


def parse_case(path: Path) -> dict[str, object]:
    inventory_path = path / "aggressive_mesh_inventory.csv"
    inventory: dict[str, str] = {}
    if inventory_path.is_file():
        with inventory_path.open(newline="", encoding="utf-8-sig") as handle:
            inventory = next(csv.DictReader(handle))
    mesh_path = path / "mesh.out"
    if not mesh_path.is_file():
        mesh_path = path / "mesh_log.txt"
    time_path = path / "time.out"
    if not time_path.is_file():
        time_path = path / "resource_time.txt"
    mesh_text = mesh_path.read_text(errors="replace") if mesh_path.is_file() else ""
    time_text = time_path.read_text(errors="replace") if time_path.is_file() else ""
    wall_seconds, maximum_rss = parse_time(time_text)
    elements_before = float(inventory.get("elem_b", "nan"))
    elements_after = float(inventory.get("elem_a", "nan"))
    nodes_before = float(inventory.get("node_b", "nan"))
    nodes_after = float(inventory.get("node_a", "nan"))
    element_ratio = (
        elements_after / elements_before
        if elements_before > 0 and elements_after > 0
        else -1.0
    )
    node_ratio = nodes_after / nodes_before if nodes_before > 0 and nodes_after > 0 else -1.0
    rounded = lambda value: round(value) if value == value else -1
    db_candidates = sorted(path.glob("*.db"))
    db = db_candidates[0] if len(db_candidates) == 1 else None
    status = "complete" if (path / "PREFLIGHT_COMPLETE").is_file() else "failed"
    return {
        "strategy": path.name,
        "status": status,
        "background_mesh_mm": float(inventory.get("bg_m", "nan")) * 1000,
        "nominal_local_target_mm": float(inventory.get("target_m", "nan")) * 1000,
        "refinement_halfwidth_mm": float(inventory.get("half_m", "nan")) * 1000,
        "refinement_level": rounded(float(inventory.get("level", "nan"))),
        "selected_parent_elements": rounded(float(inventory.get("parents", "nan"))),
        "solid_elements_before": rounded(elements_before),
        "solid_elements_after": rounded(elements_after),
        "solid_nodes_before": rounded(nodes_before),
        "solid_nodes_after": rounded(nodes_after),
        "element_growth_ratio": element_ratio,
        "node_growth_ratio": node_ratio,
        "mapdl_error_count": last_int(r"NUMBER OF ERROR\s+MESSAGES ENCOUNTERED=\s*(\d+)", mesh_text),
        "mapdl_warning_count": last_int(r"NUMBER OF WARNING MESSAGES ENCOUNTERED=\s*(\d+)", mesh_text),
        "shape_warning_elements": sum(
            int(value)
            for value in re.findall(
                r"Shape testing revealed that (\d+).*?violate shape warning limits",
                mesh_text,
                flags=re.IGNORECASE | re.DOTALL,
            )
        ),
        "shape_error_elements": sum(
            int(value)
            for value in re.findall(
                r"Shape testing revealed that (\d+).*?violate shape error limits",
                mesh_text,
                flags=re.IGNORECASE | re.DOTALL,
            )
        ),
        "run_completed": "RUN COMPLETED" in mesh_text,
        "wall_seconds": wall_seconds,
        "maximum_rss_kib": maximum_rss,
        "db_size_bytes": db.stat().st_size if db else -1,
        "db_sha256": sha256(db) if db else "",
        "source_dir": str(path.resolve()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.campaign_root.resolve()
    cases = [path for path in sorted(root.iterdir()) if path.is_dir()]
    rows = [
        parse_case(path)
        for path in cases
        if (path / "mesh.out").exists() or (path / "mesh_log.txt").exists()
    ]
    if not rows:
        raise ValueError("no mesh-only preflight cases found")
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return 0 if all(row["status"] == "complete" for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
