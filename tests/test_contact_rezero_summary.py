import csv

from src.postprocess.summarize_contact_rezeroed import PROBE_AREA_MM2, collect


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_collect_joins_state_and_area_outputs(tmp_path):
    write_csv(tmp_path / "contact_zero.csv", [{
        "eyelid_thickness_mm": 1.0,
        "contact_zero_total_push_mm": 0.01,
        "preload_force_n": 0.0,
        "preload_contact_area_mm2": 0.0,
    }])
    state = tmp_path / "effective_0p26"
    write_csv(state / "run_manifest.csv", [{
        "eyelid_thickness_mm": 1.0,
        "effective_indent_mm": 0.26,
        "target_total_push_mm": 0.27,
        "old_fixed_gap_indent_mm": 0.22,
        "probe_fy_n": -0.2,
        "contact_area_m2": 5e-6,
    }])
    write_csv(
        state / "analysis" / "displacement_support" /
        "displacement_support_manifest.csv",
        [{
            "eyelid_thickness_mm": 1.0,
            "outer_conservative_area_mm2": 13.0,
            "inner_pressure_participation_area_mm2": 5.0,
        }],
    )
    write_csv(
        state / "analysis" / "mechanical_area" /
        "mechanical_area_comparison.csv",
        [{
            "eyelid_thickness_mm": 1.0,
            "outer_pressure_effective_area_mm2": 4.0,
            "inner_pressure_effective_area_mm2": 5.0,
            "pressure_effective_ratio": 0.8,
        }],
    )

    rows = collect(tmp_path)

    assert len(rows) == 1
    assert rows[0]["hybrid_ae_over_ac"] == 2.6
    assert rows[0]["outer_contact_coverage_fraction"] == 5.0 / PROBE_AREA_MM2
