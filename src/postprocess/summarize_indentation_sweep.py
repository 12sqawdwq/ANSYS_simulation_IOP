#!/usr/bin/env python3
"""Summarize validated indentation cases and emit deterministic QC artifacts."""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

try:
    from .raster_plot import plot_lines
except ImportError:  # Direct script execution.
    from raster_plot import plot_lines

SUMMARY_FIELDS = (
    "case",
    "profile",
    "offset_mm",
    "indent_mm",
    "mesh_size_mm",
    "probe_fx_n",
    "probe_fy_n",
    "probe_force_n",
    "contact_area_m2",
    "contact_area_mm2",
    "contact_x_center_m",
    "contact_x_center_mm",
    "pmax_pa",
    "max_penetration_m",
    "max_penetration_mm",
    "n_outer",
    "cornea_peak_pa",
    "eyelid_peak_pa",
    "probe_uy_m",
    "commanded_push_m",
    "attempt_count",
    "elapsed_seconds",
    "git_commit",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def number(row: dict[str, str], field: str) -> float | None:
    value = row.get(field, "").strip()
    if not value:
        return None
    parsed = float(value)
    return parsed if math.isfinite(parsed) else None


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_summary(path: Path, rows: list[dict]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in SUMMARY_FIELDS} for row in rows)
    temporary.replace(path)


def summary_rows(manifest: list[dict[str, str]]) -> list[dict]:
    rows = []
    for row in manifest:
        if row.get("status") != "complete":
            continue
        fy = number(row, "probe_fy_n")
        area = number(row, "contact_area_m2")
        center = number(row, "contact_x_center_m")
        penetration = number(row, "max_penetration_m")
        rows.append({
            "case": row["case"],
            "profile": row["profile"],
            "offset_mm": number(row, "offset_mm"),
            "indent_mm": number(row, "indent_mm"),
            "mesh_size_mm": number(row, "mesh_size_mm"),
            "probe_fx_n": number(row, "probe_fx_n"),
            "probe_fy_n": fy,
            "probe_force_n": abs(fy) if fy is not None else "",
            "contact_area_m2": area,
            "contact_area_mm2": area * 1e6 if area is not None else "",
            "contact_x_center_m": center if center is not None else "",
            "contact_x_center_mm": center * 1e3 if center is not None else "",
            "pmax_pa": number(row, "pmax_pa"),
            "max_penetration_m": penetration,
            "max_penetration_mm": penetration * 1e3 if penetration is not None else "",
            "n_outer": number(row, "n_outer"),
            "cornea_peak_pa": number(row, "cornea_peak_pa"),
            "eyelid_peak_pa": number(row, "eyelid_peak_pa"),
            "probe_uy_m": number(row, "probe_uy_m"),
            "commanded_push_m": number(row, "commanded_push_m"),
            "attempt_count": number(row, "attempt_count"),
            "elapsed_seconds": number(row, "elapsed_seconds"),
            "git_commit": row["git_commit"],
        })
    return sorted(rows, key=lambda item: (item["offset_mm"], item["indent_mm"]))


def add_check(checks: list[dict], severity: str, code: str, case: str, message: str) -> None:
    checks.append({"severity": severity, "code": code, "case": case, "message": message})


def build_qc(
    manifest: list[dict[str, str]],
    rows: list[dict],
    expected_cases: list[dict] | None = None,
) -> dict:
    checks: list[dict] = []
    expected_pairs = {
        (float(item["offset_mm"]), float(item["indent_mm"])) for item in (expected_cases or [])
    }
    manifest_pairs = {
        (float(raw["offset_mm"]), float(raw["indent_mm"])) for raw in manifest
    }
    for offset, indent in sorted(expected_pairs - manifest_pairs):
        add_check(checks, "error", "missing_manifest_case", "",
                  f"missing offset={offset:g} mm, indentation={indent:g} mm")
    for raw in manifest:
        if raw.get("status") != "complete":
            add_check(checks, "error", "case_not_complete", raw.get("case", ""),
                      f"status={raw.get('status')} reason={raw.get('failure_reason', '')}")
    for row in rows:
        case = row["case"]
        raw = next(item for item in manifest if item["case"] == case)
        if int(float(raw["views_count"])) != 9:
            add_check(checks, "error", "missing_views", case, "expected exactly 9 non-empty views")
        push = float(row["commanded_push_m"])
        uy = float(row["probe_uy_m"])
        tolerance = max(1e-8, 0.005 * push)
        if abs(uy + push) > tolerance:
            add_check(checks, "error", "probe_displacement", case,
                      f"probe UY differs from command by {abs(uy + push):.6g} m")
        offset = float(row["offset_mm"])
        area = float(row["contact_area_m2"])
        fx = float(row["probe_fx_n"])
        fy = float(row["probe_fy_n"])
        center = row["contact_x_center_m"]
        penetration = float(row["max_penetration_m"])
        if penetration > 0.03e-3:
            add_check(checks, "warning", "contact_penetration", case,
                      f"maximum averaged penetration is {penetration * 1e3:.4f} mm")
        if math.isclose(offset, 0.0, abs_tol=1e-12):
            if area > 0 and center != "" and abs(float(center)) > 0.3e-3:
                add_check(checks, "error", "center_symmetry", case,
                          f"centered contact centroid is {float(center) * 1e3:.3f} mm")
            if abs(fx) > max(1e-6, 0.05 * abs(fy)):
                add_check(checks, "error", "lateral_force_symmetry", case,
                          f"|Fx|={abs(fx):.6g} N exceeds symmetry tolerance")
        if math.isclose(float(row["indent_mm"]), 0.0, abs_tol=1e-12):
            add_check(checks, "info", "nominal_zero_baseline", case,
                      f"Fy={fy:.6g} N, contact area={area * 1e6:.6g} mm2")

    grouped: dict[float, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[float(row["offset_mm"])].append(row)
    monotonic_fields = (
        ("probe_force_n", "reaction force"),
        ("contact_area_m2", "contact area"),
        ("n_outer", "closed contact element count"),
    )
    for offset, group in grouped.items():
        ordered = sorted(group, key=lambda item: item["indent_mm"])
        for previous, current in zip(ordered, ordered[1:]):
            for field, label in monotonic_fields:
                old = float(previous[field])
                new = float(current[field])
                if old > 0 and new < 0.95 * old:
                    add_check(checks, "warning", "nonmonotonic_trend", current["case"],
                              f"{label} decreased by more than 5% at offset={offset:g} mm")

    by_condition = {(float(row["offset_mm"]), float(row["indent_mm"])): row for row in rows}
    for (offset, indent), row in by_condition.items():
        if offset <= 0 or row["contact_x_center_m"] == "":
            continue
        baseline = by_condition.get((0.0, indent))
        if not baseline or baseline["contact_x_center_m"] == "":
            continue
        shift = float(row["contact_x_center_m"]) - float(baseline["contact_x_center_m"])
        if shift < -0.15e-3:
            add_check(checks, "warning", "contact_center_direction", row["case"],
                      f"contact center shifted {shift * 1e3:.3f} mm opposite the positive offset")

    severities = {level: sum(check["severity"] == level for check in checks)
                  for level in ("error", "warning", "info")}
    return {
        "generated_at_utc": utc_now(),
        "passed": severities["error"] == 0,
        "expected_cases": len(expected_pairs) if expected_cases is not None else len(manifest),
        "manifest_cases": len(manifest),
        "complete_cases": len(rows),
        "counts": severities,
        "checks": checks,
    }


def plot_curves(output: Path, rows: list[dict]) -> None:
    figures = output / "figures"
    figures.mkdir(exist_ok=True)
    plots = (
        ("probe_force_n", 1.0, "FORCE N", "force_vs_indent.png"),
        ("contact_area_m2", 1e6, "CONTACT AREA MM2", "contact_area_vs_indent.png"),
        ("pmax_pa", 1e-3, "PMAX KPA", "pmax_vs_indent.png"),
        ("contact_x_center_m", 1e3, "CONTACT CENTER MM", "contact_center_vs_indent.png"),
    )
    offsets = sorted({float(row["offset_mm"]) for row in rows})
    for field, scale, ylabel, filename in plots:
        series = []
        for offset in offsets:
            group = sorted((row for row in rows if float(row["offset_mm"]) == offset),
                           key=lambda item: item["indent_mm"])
            points = [(float(row["indent_mm"]), row[field]) for row in group if row[field] != ""]
            if points:
                series.append((f"OFFSET {offset:g} MM", [(x, float(y) * scale) for x, y in points]))
        plot_lines(figures / filename, ylabel, series)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_root", type=Path)
    cli = parser.parse_args()
    manifest = read_manifest(cli.run_root / "run_manifest.csv")
    metadata_path = cli.run_root / "run_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
    rows = summary_rows(manifest)
    write_summary(cli.run_root / "summary.csv", rows)
    qc = build_qc(manifest, rows, metadata.get("cases"))
    (cli.run_root / "qc_report.json").write_text(
        json.dumps(qc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if rows:
        plot_curves(cli.run_root, rows)
    print(f"complete={len(rows)} qc_passed={str(qc['passed']).lower()} root={cli.run_root}")
    return 0 if qc["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
