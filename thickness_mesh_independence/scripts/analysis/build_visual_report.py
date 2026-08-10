#!/usr/bin/env python3
"""Build audited timing tables and visual composites for the mesh study."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any

MESHES = (0.30, 0.24, 0.20)
THICKNESSES = (1.60, 1.80, 2.00)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_key_value_csv(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        return {row[0]: row[1] for row in csv.reader(handle) if len(row) >= 2}


def elapsed_seconds(start: str, end: str) -> float:
    return (datetime.fromisoformat(end.replace("Z", "+00:00")) - datetime.fromisoformat(start.replace("Z", "+00:00"))).total_seconds()


def float_key(value: str | float) -> float:
    return round(float(value), 6)


def load_scale_map(results_root: Path) -> dict[tuple[float, float], dict[str, int]]:
    rows = read_csv(results_root / "confirmation" / "mesh_comparison.csv")
    scale: dict[tuple[float, float], dict[str, int]] = {}
    for row in rows:
        key = (float_key(row["mesh_size_mm"]), float_key(row["eyelid_thickness_mm"]))
        scale[key] = {
            "solver_elements": int(row["solver_elements"]),
            "solver_nodes": int(row["solver_nodes"]),
            "solver_equations_iop0": int(row["solver_equations_iop0"]),
            "solver_equations_iop20": int(row["solver_equations_iop20"]),
        }
    return scale


def canonical_row(
    source: dict[str, str],
    scale: dict[str, int],
    source_manifest: str,
    external_attempt_dir: str,
    campaign_workers: int,
    timing_quality: str,
) -> dict[str, Any]:
    pressure = float(source["iop_mmhg"])
    seconds = float(source["elapsed_seconds"])
    np_used = int(source["np_used"])
    equations = scale["solver_equations_iop0" if pressure == 0 else "solver_equations_iop20"]
    return {
        "mesh_size_mm": f"{float(source['mesh_size_mm']):.2f}",
        "eyelid_thickness_mm": f"{float(source['eyelid_thickness_mm']):.2f}",
        "iop_mmhg": f"{pressure:.0f}",
        "status": source["status"],
        "accepted_endpoint": "true",
        "np_used": np_used,
        "campaign_workers": campaign_workers,
        "started_at_utc": source["started_at_utc"],
        "ended_at_utc": source["ended_at_utc"],
        "elapsed_seconds": f"{seconds:.3f}",
        "elapsed_hours": f"{seconds / 3600:.6f}",
        "rank_hours": f"{seconds * np_used / 3600:.6f}",
        "solver_elements": scale["solver_elements"],
        "solver_nodes": scale["solver_nodes"],
        "solver_equations": equations,
        "ansys_error_count": source.get("ansys_error_count", "0") or "0",
        "result_load_step": source.get("result_load_step", "3") or "3",
        "returncode": source.get("returncode", "0") or "0",
        "timing_quality": timing_quality,
        "source_manifest": source_manifest,
        "external_attempt_dir": external_attempt_dir,
        "source_git_commit": source["source_git_commit"],
    }


def collect_timing_rows(repo_root: Path) -> list[dict[str, Any]]:
    study = repo_root / "thickness_mesh_independence"
    results = study / "results"
    visual = results / "visual_evidence"
    scale_map = load_scale_map(results)
    rows: list[dict[str, Any]] = []

    for source in read_csv(visual / "baseline_timing_source.csv"):
        key = (float_key(source["mesh_size_mm"]), float_key(source["eyelid_thickness_mm"]))
        rows.append(
            canonical_row(
                source,
                scale_map[key],
                source["source_manifest"],
                "",
                int(source["campaign_workers"]),
                "historical_campaign_with_heterogeneous_rank_count",
            )
        )

    manifest_specs = (
        (0.24, 0, results / "screening" / "iop0_run_manifest.csv", results / "screening" / "iop0_run_metadata.json"),
        (0.24, 20, results / "screening" / "iop20_run_manifest.csv", results / "screening" / "iop20_run_metadata.json"),
        (0.20, 0, results / "confirmation" / "iop0_run_manifest.csv", results / "confirmation" / "iop0_run_metadata.json"),
        (0.20, 20, results / "confirmation" / "iop20_run_manifest.csv", results / "confirmation" / "iop20_run_metadata.json"),
    )
    for mesh, pressure, manifest_path, metadata_path in manifest_specs:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        external_root = metadata["run_root"]
        for source in read_csv(manifest_path):
            thickness = float(source["eyelid_thickness_mm"])
            if thickness not in THICKNESSES or float(source["iop_mmhg"]) != pressure:
                continue
            key = (float_key(mesh), float_key(thickness))
            quality = "accepted_bounded_wall_time"
            if mesh == 0.20 and pressure == 0 and thickness == 1.60:
                quality = "resource_contended_actual_time_not_representative"
            source_manifest = manifest_path.relative_to(repo_root).as_posix()
            external_attempt = f"{external_root}/{source['attempt_dir']}"
            normalized = dict(source)
            normalized["source_git_commit"] = source["git_commit"]
            rows.append(
                canonical_row(
                    normalized,
                    scale_map[key],
                    source_manifest,
                    external_attempt,
                    int(metadata["workers"]),
                    quality,
                )
            )

    rows.sort(key=lambda row: (float(row["mesh_size_mm"]), float(row["eyelid_thickness_mm"]), float(row["iop_mmhg"])), reverse=True)
    expected = {(mesh, thickness, pressure) for mesh in MESHES for thickness in THICKNESSES for pressure in (0, 20)}
    observed = {(float(row["mesh_size_mm"]), float(row["eyelid_thickness_mm"]), int(row["iop_mmhg"])) for row in rows}
    if observed != expected or len(rows) != 18:
        raise ValueError(f"expected 18 unique accepted endpoints, observed {len(rows)}: {sorted(expected - observed)}")
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build_summary(repo_root: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    visual = repo_root / "thickness_mesh_independence" / "results" / "visual_evidence"
    preflight = read_csv(visual / "resource_preflight_timing.csv")
    post_source = json.loads((visual / "source_manifest.json").read_text(encoding="utf-8"))
    per_mesh: dict[str, Any] = {}
    for mesh in MESHES:
        selected = [row for row in rows if float(row["mesh_size_mm"]) == mesh]
        seconds = [float(row["elapsed_seconds"]) for row in selected]
        pressure_totals = {
            str(pressure): sum(float(row["elapsed_seconds"]) for row in selected if int(row["iop_mmhg"]) == pressure) / 3600
            for pressure in (0, 20)
        }
        per_mesh[f"{mesh:.2f}"] = {
            "accepted_endpoint_count": len(selected),
            "sum_case_wall_hours": sum(seconds) / 3600,
            "median_case_wall_hours": statistics.median(seconds) / 3600,
            "minimum_case_wall_hours": min(seconds) / 3600,
            "maximum_case_wall_hours": max(seconds) / 3600,
            "sum_rank_hours": sum(float(row["rank_hours"]) for row in selected),
            "case_wall_hours_by_pressure": pressure_totals,
            "np_values": sorted({int(row["np_used"]) for row in selected}),
            "element_range": [min(int(row["solver_elements"]) for row in selected), max(int(row["solver_elements"]) for row in selected)],
            "equation_range": [min(int(row["solver_equations"]) for row in selected), max(int(row["solver_equations"]) for row in selected)],
        }

    screening_status = read_key_value_csv(repo_root / "thickness_mesh_independence" / "results" / "screening" / "campaign_status.csv")
    confirmation_iop0 = read_key_value_csv(repo_root / "thickness_mesh_independence" / "results" / "confirmation" / "iop0_source_campaign_status.csv")
    confirmation_iop20 = read_key_value_csv(repo_root / "thickness_mesh_independence" / "results" / "confirmation" / "iop20_source_campaign_status.csv")
    per_mesh["0.24"]["accepted_campaign_calendar_hours"] = elapsed_seconds(screening_status["started_at_utc"], screening_status["ended_at_utc"]) / 3600
    per_mesh["0.20"]["accepted_pressure_campaign_hours"] = {
        "iop0_campaign": elapsed_seconds(confirmation_iop0["started_at_utc"], confirmation_iop0["ended_at_utc"]) / 3600,
        "iop20_campaign": elapsed_seconds(confirmation_iop20["started_at_utc"], confirmation_iop20["ended_at_utc"]) / 3600,
        "sum": (
            elapsed_seconds(confirmation_iop0["started_at_utc"], confirmation_iop0["ended_at_utc"])
            + elapsed_seconds(confirmation_iop20["started_at_utc"], confirmation_iop20["ended_at_utc"])
        ) / 3600,
    }
    per_mesh["0.30"]["accepted_campaign_calendar_hours"] = None
    per_mesh["0.30"]["calendar_note"] = "The six endpoints came from heterogeneous historical campaigns; no single campaign makespan is valid."

    postprocessing = {}
    for key, case in post_source["cases"].items():
        postprocessing[f"{case['mesh_size_mm']:.2f}"] = case["postprocess"]
    preflight_seconds = sum(float(row["elapsed_seconds"]) for row in preflight)
    max_rank_hours = sum(float(row["elapsed_seconds"]) * int(row["maximum_mpi_ranks"]) / 3600 for row in preflight)
    return {
        "schema_version": 1,
        "accepted_endpoint_count": len(rows),
        "per_mesh": per_mesh,
        "nonaccepted_resource_events": {
            "count": len(preflight),
            "sum_event_wall_hours": preflight_seconds / 3600,
            "maximum_rank_hour_upper_bound": max_rank_hours,
            "numerical_endpoints_used": 0,
        },
        "existing_rst_postprocessing": postprocessing,
        "timing_interpretation": [
            "elapsed_seconds is subprocess wall-clock time, not CPU time.",
            "Rank-hours are elapsed time multiplied by requested MPI ranks and are not a measured CPU-utilization value.",
            "The 0.30 mm rows use mixed 4-rank and 8-rank historical campaigns; cross-mesh wall-time ratios are not controlled speedup benchmarks.",
            "The 0.20 mm IOP0 1.60 mm endpoint overlapped an aborted IOP20 branch and is retained as actual history but is not representative of exclusive-resource runtime.",
        ],
    }


def load_font(size: int):
    from PIL import ImageFont

    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def build_composite(raw_dir: Path, output_path: Path, suffix: str, scale_rows: dict[float, dict[str, int]], crop: tuple[int, int, int, int] | None = None) -> None:
    from PIL import Image, ImageDraw

    panel_width = 960
    header_height = 104
    source_images = []
    for mesh in MESHES:
        token = f"{mesh:.2f}".replace(".", "p")
        image = Image.open(raw_dir / f"mesh_{token}_{suffix}.png").convert("RGB")
        if crop is not None:
            image = image.crop(crop)
        panel_height = round(image.height * panel_width / image.width)
        image = image.resize((panel_width, panel_height), Image.Resampling.LANCZOS)
        source_images.append((mesh, image))
    height = header_height + max(image.height for _, image in source_images)
    canvas = Image.new("RGB", (panel_width * len(source_images), height), "white")
    draw = ImageDraw.Draw(canvas)
    title_font = load_font(30)
    detail_font = load_font(25)
    for index, (mesh, image) in enumerate(source_images):
        x = index * panel_width
        scale = scale_rows[mesh]
        labels = (
            (f"Global size {mesh:.2f} mm", title_font, 12),
            (f"{scale['solver_elements']:,} elements | {scale['solver_equations']:,} equations", detail_font, 57),
        )
        for label, font, y in labels:
            bbox = draw.textbbox((0, 0), label, font=font)
            draw.text((x + (panel_width - (bbox[2] - bbox[0])) / 2, y), label, fill="black", font=font)
        canvas.paste(image, (x, header_height))
        if index:
            draw.line((x, 0, x, height), fill=(160, 160, 160), width=2)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, format="PNG", optimize=False, compress_level=9)


def build_composites(repo_root: Path, raw_dir: Path | None = None, output_dir: Path | None = None) -> None:
    visual = repo_root / "thickness_mesh_independence" / "results" / "visual_evidence"
    raw_dir = raw_dir or visual / "raw"
    output_dir = output_dir or visual
    scale_map = load_scale_map(repo_root / "thickness_mesh_independence" / "results")
    h2 = {
        mesh: {
            "solver_elements": scale_map[(float_key(mesh), 2.0)]["solver_elements"],
            "solver_equations": scale_map[(float_key(mesh), 2.0)]["solver_equations_iop20"],
        }
        for mesh in MESHES
    }
    build_composite(raw_dir, output_dir / "mesh_sections_comparison.png", "section", h2)
    build_composite(raw_dir, output_dir / "stress_sections_comparison.png", "stress", h2)
    build_composite(raw_dir, output_dir / "contact_zone_mesh_comparison.png", "section", h2, crop=(600, 570, 1543, 1100))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_artifact_manifest(repo_root: Path) -> None:
    visual = repo_root / "thickness_mesh_independence" / "results" / "visual_evidence"
    patterns = ("*.csv", "*.json", "*.png", "raw/*.png")
    paths = sorted({path for pattern in patterns for path in visual.glob(pattern) if path.name != "artifact_manifest.json"})
    entries = []
    for path in paths:
        entries.append({"path": path.relative_to(repo_root).as_posix(), "size_bytes": path.stat().st_size, "sha256": sha256(path)})
    payload = {"schema_version": 1, "artifact_count": len(entries), "artifacts": entries}
    (visual / "artifact_manifest.json").write_bytes((json.dumps(payload, indent=2) + "\n").encode("utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--raw-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--skip-composites", action="store_true")
    parser.add_argument("--composites-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    if args.composites_only:
        build_composites(repo_root, args.raw_dir, args.output_dir)
        return 0
    visual = repo_root / "thickness_mesh_independence" / "results" / "visual_evidence"
    rows = collect_timing_rows(repo_root)
    write_csv(visual / "simulation_timing.csv", rows)
    summary = build_summary(repo_root, rows)
    (visual / "timing_summary.json").write_bytes((json.dumps(summary, indent=2) + "\n").encode("utf-8"))
    if not args.skip_composites:
        build_composites(repo_root, args.raw_dir, args.output_dir)
    write_artifact_manifest(repo_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
