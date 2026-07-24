import csv
import math

from src.postprocess.analyze_probe_force_curve import (
    PROBE_AREA_MM2,
    fit_breakpoint,
    read_raw,
)


def test_read_raw_removes_initial_gap_and_converts_pressure(tmp_path):
    path = tmp_path / "eyelid_1p20mm.csv"
    with path.open("w", newline="", encoding="ascii") as handle:
        writer = csv.writer(handle)
        for index in range(7):
            indent_mm = index * 0.1
            uy_m = -(0.05 + indent_mm) / 1000.0
            writer.writerow((indent_mm / 1000.0, 1.1, 0, -0.5, uy_m, uy_m))

    rows = read_raw(path, gap_mm=0.05)

    assert math.isclose(float(rows[-1]["actual_indentation_mm"]), 0.6)
    assert abs(float(rows[-1]["displacement_error_um"])) < 1e-9
    assert math.isclose(
        float(rows[-1]["probe_equivalent_pressure_kpa"]),
        0.5 / PROBE_AREA_MM2 * 1000.0,
    )


def test_continuous_segment_fit_finds_a_clear_slope_change():
    rows = []
    for index in range(33):
        indent = index * 0.025
        force = 0.5 * indent + 1.0 * max(0.0, indent - 0.4)
        rows.append({
            "indentation_mm": indent,
            "probe_force_n": force,
            "eyelid_thickness_mm": 1.2,
        })

    result = fit_breakpoint(rows)

    assert abs(float(result["candidate_indent_mm"]) - 0.4) <= 0.025
    assert math.isclose(float(result["pre_slope_n_per_mm"]), 0.5, rel_tol=1e-8)
    assert math.isclose(float(result["post_slope_n_per_mm"]), 1.5, rel_tol=1e-8)
    assert result["evidence"] == "strong"
