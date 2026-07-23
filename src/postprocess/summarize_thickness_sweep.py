#!/usr/bin/env python3
"""Summarize the fixed-indentation eyelid-thickness finite-element sweep."""
from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path

try:
    from .raster_plot import plot_lines
except ImportError:  # Direct script execution.
    from raster_plot import plot_lines


SUMMARY_FIELDS = (
    "case",
    "eyelid_thickness_mm",
    "cornea_thickness_mm",
    "indent_mm",
    "mesh_size_mm",
    "iop_mmhg",
    "eyelid_material_scale",
    "cornea_material_scale",
    "probe_force_n",
    "force_ratio_to_0p8",
    "force_correction_to_0p8",
    "probe_area_mm2",
    "outer_contact_area_mm2",
    "contact_fill_fraction",
    "outer_area_mm2",
    "outer_area_ratio_to_0p8",
    "outer_surface_area_mm2",
    "outer_projected_area_mm2",
    "outer_equivalent_diameter_mm",
    "outer_break_radius_mm",
    "outer_breakpoint_method",
    "outer_area_sensitivity_fraction",
    "outer_diameter_sensitivity_mm",
    "mean_outer_pressure_kpa",
    "pmax_kpa",
    "inner_max_downward_mm",
    "inner_effect_area_mm2",
    "inner_area_1deg_mm2",
    "inner_area_2deg_mm2",
    "inner_area_3deg_mm2",
    "inner_area_smooth_2deg_mm2",
    "inner_smooth_2deg_face_count",
    "inner_surface_area_mm2",
    "inner_projected_area_mm2",
    "inner_equivalent_diameter_mm",
    "inner_break_radius_mm",
    "inner_breakpoint_method",
    "inner_area_sensitivity_fraction",
    "inner_diameter_sensitivity_mm",
    "ae_over_ac_surface",
    "ae_over_ac_projected",
    "breakpoint_qc",
    "ae_over_ac_1deg",
    "ae_over_ac_2deg",
    "ae_over_ac_3deg",
    "ae_over_ac_smooth_2deg",
    "max_penetration_mm",
    "cornea_peak_kpa",
    "eyelid_peak_kpa",
    "elapsed_seconds",
    "git_commit",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def value(row: dict[str, str], field: str) -> float:
    parsed = float(row[field])
    if not math.isfinite(parsed):
        raise ValueError(f"non-finite {field} in {row.get('case', 'unknown case')}")
    return parsed


def breakpoint_method(code: float) -> str:
    return {1: "inflection", 2: "segmented_fit"}.get(int(round(code)), "unknown")


def summary_rows(manifest: list[dict[str, str]]) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    for raw in manifest:
        if raw.get("status") != "complete":
            continue
        force = abs(value(raw, "probe_fy_n"))
        outer_contact = value(raw, "contact_area_m2") * 1e6
        outer_surface = value(raw, "outer_surface_area_m2") * 1e6
        outer_projected = value(raw, "outer_projected_area_m2") * 1e6
        inner_surface = value(raw, "inner_surface_area_m2") * 1e6
        inner_projected = value(raw, "inner_projected_area_m2") * 1e6
        inner1 = value(raw, "inner_area_1deg_m2") * 1e6
        inner2 = value(raw, "inner_area_2deg_m2") * 1e6
        inner3 = value(raw, "inner_area_3deg_m2") * 1e6
        smooth2 = value(raw, "inner_area_smooth_2deg_m2") * 1e6
        rows.append({
            "case": raw["case"],
            "eyelid_thickness_mm": value(raw, "eyelid_thickness_mm"),
            "cornea_thickness_mm": value(raw, "cornea_thickness_mm"),
            "indent_mm": value(raw, "indent_mm"),
            "mesh_size_mm": value(raw, "mesh_size_mm"),
            "iop_mmhg": value(raw, "iop_mmhg"),
            "eyelid_material_scale": value(raw, "eyelid_material_scale"),
            "cornea_material_scale": value(raw, "cornea_material_scale"),
            "probe_force_n": force,
            "probe_area_mm2": math.pi * 2.16**2,
            "outer_contact_area_mm2": outer_contact,
            "contact_fill_fraction": outer_contact / (math.pi * 2.16**2),
            "outer_area_mm2": outer_contact,
            "outer_surface_area_mm2": outer_surface,
            "outer_projected_area_mm2": outer_projected,
            "outer_equivalent_diameter_mm": 2.0 * math.sqrt(outer_projected / math.pi),
            "outer_break_radius_mm": value(raw, "outer_break_radius_m") * 1e3,
            "outer_breakpoint_method": breakpoint_method(value(raw, "outer_break_method_code")),
            "outer_area_sensitivity_fraction": value(raw, "outer_area_sensitivity_fraction"),
            "outer_diameter_sensitivity_mm": value(raw, "outer_diameter_sensitivity_m") * 1e3,
            "mean_outer_pressure_kpa": force / (outer_contact * 1e-6) / 1e3,
            "pmax_kpa": value(raw, "pmax_pa") / 1e3,
            "inner_max_downward_mm": value(raw, "inner_max_downward_m") * 1e3,
            "inner_effect_area_mm2": value(raw, "inner_effect_area_m2") * 1e6,
            "inner_area_1deg_mm2": inner1,
            "inner_area_2deg_mm2": inner2,
            "inner_area_3deg_mm2": inner3,
            "inner_area_smooth_2deg_mm2": smooth2,
            "inner_smooth_2deg_face_count": int(value(raw, "inner_smooth_2deg_face_count")),
            "inner_surface_area_mm2": inner_surface,
            "inner_projected_area_mm2": inner_projected,
            "inner_equivalent_diameter_mm": 2.0 * math.sqrt(inner_projected / math.pi),
            "inner_break_radius_mm": value(raw, "inner_break_radius_m") * 1e3,
            "inner_breakpoint_method": breakpoint_method(value(raw, "inner_break_method_code")),
            "inner_area_sensitivity_fraction": value(raw, "inner_area_sensitivity_fraction"),
            "inner_diameter_sensitivity_mm": value(raw, "inner_diameter_sensitivity_m") * 1e3,
            "ae_over_ac_surface": outer_surface / inner_surface,
            "ae_over_ac_projected": outer_projected / inner_projected,
            "breakpoint_qc": (
                "warning_scale_sensitive"
                if max(
                    value(raw, "outer_area_sensitivity_fraction"),
                    value(raw, "inner_area_sensitivity_fraction"),
                ) > 0.10
                or max(
                    value(raw, "outer_diameter_sensitivity_m"),
                    value(raw, "inner_diameter_sensitivity_m"),
                ) > 0.15e-3
                else "pass"
            ),
            "ae_over_ac_1deg": outer_contact / inner1 if inner1 > 0 else "",
            "ae_over_ac_2deg": outer_contact / inner2 if inner2 > 0 else "",
            "ae_over_ac_3deg": outer_contact / inner3 if inner3 > 0 else "",
            "ae_over_ac_smooth_2deg": outer_contact / smooth2 if smooth2 > 0 else "",
            "max_penetration_mm": value(raw, "max_penetration_m") * 1e3,
            "cornea_peak_kpa": value(raw, "cornea_peak_pa") / 1e3,
            "eyelid_peak_kpa": value(raw, "eyelid_peak_pa") / 1e3,
            "elapsed_seconds": value(raw, "elapsed_seconds"),
            "git_commit": raw["git_commit"],
        })
    rows.sort(key=lambda row: float(row["eyelid_thickness_mm"]))
    if rows:
        reference = next(
            (row for row in rows if math.isclose(float(row["eyelid_thickness_mm"]), 0.8)),
            rows[0],
        )
        for row in rows:
            row["force_ratio_to_0p8"] = float(row["probe_force_n"]) / float(reference["probe_force_n"])
            row["force_correction_to_0p8"] = float(reference["probe_force_n"]) / float(row["probe_force_n"])
            row["outer_area_ratio_to_0p8"] = float(row["outer_area_mm2"]) / float(reference["outer_area_mm2"])
    return rows


def write_csv(path: Path, rows: list[dict[str, float | str]]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in SUMMARY_FIELDS} for row in rows)
    temporary.replace(path)


def add_check(checks: list[dict[str, str]], severity: str, code: str, case: str, message: str) -> None:
    checks.append({"severity": severity, "code": code, "case": case, "message": message})


def build_qc(
    manifest: list[dict[str, str]],
    rows: list[dict[str, float | str]],
    expected_cases: list[dict] | None,
    expected_views: int = 9,
) -> dict[str, object]:
    checks: list[dict[str, str]] = []
    expected = {
        (float(item["eyelid_thickness_mm"]), float(item["indent_mm"]))
        for item in (expected_cases or [])
    }
    actual = {
        (value(row, "eyelid_thickness_mm"), value(row, "indent_mm")) for row in manifest
    }
    for thickness, indent in sorted(expected - actual):
        add_check(checks, "error", "missing_manifest_case", "",
                  f"missing eyelid thickness={thickness:g} mm, indentation={indent:g} mm")
    for raw in manifest:
        case = raw.get("case", "")
        if raw.get("status") != "complete":
            add_check(checks, "error", "case_not_complete", case,
                      f"status={raw.get('status')} reason={raw.get('failure_reason', '')}")
            continue
        if int(value(raw, "views_count")) != expected_views:
            add_check(
                checks, "error", "missing_views", case,
                f"expected exactly {expected_views} non-empty views",
            )
        push = value(raw, "commanded_push_m")
        if abs(value(raw, "probe_uy_m") + push) > max(1e-8, 0.005 * push):
            add_check(checks, "error", "probe_displacement", case, "probe displacement differs from command")
        if abs(value(raw, "probe_fx_n")) > max(1e-6, 0.05 * abs(value(raw, "probe_fy_n"))):
            add_check(checks, "warning", "lateral_force_symmetry", case,
                      "centered thickness case has lateral force above 5% of axial force")
        penetration = value(raw, "max_penetration_m")
        if penetration > 0.03e-3:
            add_check(checks, "warning", "contact_penetration", case,
                      f"maximum averaged penetration is {penetration * 1e3:.4f} mm")
        areas = [value(raw, field) for field in (
            "inner_area_1deg_m2", "inner_area_2deg_m2", "inner_area_3deg_m2"
        )]
        effect_area = value(raw, "inner_effect_area_m2")
        if not (0 <= areas[0] <= areas[1] <= areas[2] <= effect_area):
            add_check(checks, "error", "inner_area_order", case,
                      "geometric inner areas do not increase with angle threshold")
        smooth_area = value(raw, "inner_area_smooth_2deg_m2")
        smooth_count = value(raw, "inner_smooth_2deg_face_count")
        if not 0 <= smooth_area <= effect_area or smooth_count < 0:
            add_check(checks, "error", "inner_smooth_area", case,
                      "smoothed 2 degree area or face count is invalid")
        if areas[1] > 0:
            sensitivity = (areas[2] - areas[0]) / areas[1]
            if sensitivity > 1.0:
                add_check(checks, "warning", "legacy_inner_area_threshold_sensitivity", case,
                          f"legacy 1-3 degree spread is {sensitivity * 100:.1f}% of the 2 degree area")
        probe_area = math.pi * (2.16e-3) ** 2
        if value(raw, "contact_area_m2") > probe_area * 1.01:
            add_check(checks, "error", "contact_exceeds_probe", case,
                      "closed contact area exceeds the 4.32 mm probe face")
        for prefix in ("outer", "inner"):
            surface = value(raw, f"{prefix}_surface_area_m2")
            projected = value(raw, f"{prefix}_projected_area_m2")
            area_sensitivity = value(raw, f"{prefix}_area_sensitivity_fraction")
            diameter_sensitivity = value(raw, f"{prefix}_diameter_sensitivity_m")
            if surface <= 0 or projected <= 0 or projected > surface * (1.0 + 1e-9):
                add_check(checks, "error", "breakpoint_area", case,
                          f"{prefix} surface/projected breakpoint area is invalid")
            if area_sensitivity > 0.10 or diameter_sensitivity > 0.15e-3:
                add_check(
                    checks, "warning", "breakpoint_scale_sensitivity", case,
                    f"{prefix} scale sensitivity is {area_sensitivity * 100:.1f}% area and "
                    f"{diameter_sensitivity * 1e3:.3f} mm diameter",
                )
        outer_diameter = 2.0 * math.sqrt(value(raw, "outer_projected_area_m2") / math.pi)
        contact_diameter = 2.0 * math.sqrt(value(raw, "contact_area_m2") / math.pi)
        if not 2.5e-3 <= outer_diameter <= 3.1e-3:
            add_check(checks, "warning", "outer_applanation_scale", case,
                      f"outer equivalent diameter is {outer_diameter * 1e3:.3f} mm")
        if abs(outer_diameter - contact_diameter) > 0.15e-3:
            add_check(checks, "warning", "outer_contact_boundary_mismatch", case,
                      "breakpoint and contact equivalent diameters differ by more than 0.15 mm")
    if rows:
        add_check(checks, "info", "trend_span", "",
                  f"force ratio at maximum thickness is {float(rows[-1]['force_ratio_to_0p8']):.3f}")
    counts = {
        severity: sum(item["severity"] == severity for item in checks)
        for severity in ("error", "warning", "info")
    }
    return {
        "generated_at_utc": utc_now(),
        "passed": counts["error"] == 0,
        "expected_cases": len(expected) if expected_cases is not None else len(manifest),
        "manifest_cases": len(manifest),
        "complete_cases": len(rows),
        "counts": counts,
        "checks": checks,
    }


def plot_curves(run_root: Path, rows: list[dict[str, float | str]]) -> None:
    figures = run_root / "figures"
    figures.mkdir(exist_ok=True)
    x = lambda row: float(row["eyelid_thickness_mm"])
    plots = (
        ("force_vs_thickness.png", "PROBE FORCE N", (
            ("FORCE", [(x(row), float(row["probe_force_n"])) for row in rows]),
        )),
        ("outer_area_vs_thickness.png", "OUTER AREA MM2", (
            ("CONTACT", [(x(row), float(row["outer_contact_area_mm2"])) for row in rows]),
            ("SURFACE", [(x(row), float(row["outer_surface_area_mm2"])) for row in rows]),
            ("PROJECTED", [(x(row), float(row["outer_projected_area_mm2"])) for row in rows]),
        )),
        ("inner_area_vs_thickness.png", "INNER GEOMETRIC AREA MM2", (
            ("SURFACE", [(x(row), float(row["inner_surface_area_mm2"])) for row in rows]),
            ("PROJECTED", [(x(row), float(row["inner_projected_area_mm2"])) for row in rows]),
            ("LEGACY SMOOTH 2 DEG", [
                (x(row), float(row["inner_area_smooth_2deg_mm2"])) for row in rows
            ]),
        )),
        ("area_ratio_vs_thickness.png", "AE OVER AC", (
            ("SURFACE", [(x(row), float(row["ae_over_ac_surface"])) for row in rows]),
            ("PROJECTED", [(x(row), float(row["ae_over_ac_projected"])) for row in rows]),
        )),
        ("equivalent_diameter_vs_thickness.png", "EQUIVALENT DIAMETER MM", (
            ("OUTER", [(x(row), float(row["outer_equivalent_diameter_mm"])) for row in rows]),
            ("INNER", [(x(row), float(row["inner_equivalent_diameter_mm"])) for row in rows]),
        )),
        ("pressure_vs_thickness.png", "PRESSURE KPA", (
            ("MEAN", [(x(row), float(row["mean_outer_pressure_kpa"])) for row in rows]),
            ("PMAX", [(x(row), float(row["pmax_kpa"])) for row in rows]),
        )),
    )
    for filename, ylabel, series in plots:
        plot_lines(
            figures / filename,
            ylabel,
            list(series),
            x_label="Eyelid thickness (mm)",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_root", type=Path)
    cli = parser.parse_args()
    manifest = read_csv(cli.run_root / "run_manifest.csv")
    metadata_path = cli.run_root / "run_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
    rows = summary_rows(manifest)
    write_csv(cli.run_root / "summary.csv", rows)
    expected_views = 9 if metadata.get("view_policy", "all") == "all" else 0
    qc = build_qc(manifest, rows, metadata.get("cases"), expected_views)
    (cli.run_root / "qc_report.json").write_text(
        json.dumps(qc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if rows:
        plot_curves(cli.run_root, rows)
    print(f"complete={len(rows)} qc_passed={str(qc['passed']).lower()} root={cli.run_root}")
    return 0 if qc["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
