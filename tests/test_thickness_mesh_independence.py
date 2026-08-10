import csv
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "thickness_mesh_independence"
PROBE_AREA_MM2 = 14.65741468458854
PA_PER_MMHG = 133.322


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def test_mesh_screen_configuration_is_the_frozen_targeted_matrix():
    config = json.loads((EXPERIMENT / "config" / "experiment.json").read_text(encoding="utf-8"))
    assert config["source_git_commit"] == "cef09f91ca328cc39488b55047afaf9e078a980a"
    assert config["status"] == "three_mesh_confirmation_complete_amplitude_not_mesh_independent"
    assert config["decision"] == "thick_end_order_robust_but_amplitude_not_mesh_independent"
    assert config["screening"]["mesh_size_mm"] == pytest.approx(0.24)
    assert config["screening"]["eyelid_thicknesses_mm"] == [1.6, 1.8, 2.0]
    assert config["screening"]["iop_mmhg"] == [0.0, 20.0]
    assert config["screening"]["new_solver_cases"] == 6
    assert config["solver"]["maximum_parallel_cases"] == 1
    assert config["solver"]["np_per_case"] == 4
    assert config["solver"]["screening_timeout_seconds_per_attempt"] == 28800
    assert config["solver"]["confirmation_timeout_seconds_per_attempt"] == 43200
    assert config["fixed_model"]["cornea_material_scale"] == pytest.approx(0.75)
    assert config["fixed_model"]["probe_area_mm2"] == pytest.approx(PROBE_AREA_MM2)
    assert config["conditional_confirmation"]["launch_policy"].startswith("authorized_after_0p24")


def test_baseline_inventory_matches_frozen_response_and_has_paired_meshes():
    inventory_rows = read_csv(EXPERIMENT / "results" / "baseline_mesh_inventory.csv")
    prediction_rows = read_csv(ROOT / "analysis" / "outputs" / "thickness_iop_predictions.csv")
    inventory = {
        (float(row["eyelid_thickness_mm"]), float(row["iop_mmhg"])): row
        for row in inventory_rows
    }
    predictions = {
        float(row["eyelid_thickness_mm"]): row
        for row in prediction_rows
        if float(row["eyelid_thickness_mm"]) in {1.6, 1.8, 2.0}
    }
    assert set(inventory) == {(h, p) for h in (1.6, 1.8, 2.0) for p in (0.0, 20.0)}
    for thickness in (1.6, 1.8, 2.0):
        row0 = inventory[(thickness, 0.0)]
        row20 = inventory[(thickness, 20.0)]
        assert row0["status"] == row20["status"] == "complete"
        assert float(row0["mesh_size_mm"]) == float(row20["mesh_size_mm"]) == pytest.approx(0.30)
        assert row0["solver_nodes"] == row20["solver_nodes"]
        assert row0["solver_elements"] == row20["solver_elements"]
        delta_force = abs(float(row20["probe_fy_n"])) - abs(float(row0["probe_fy_n"]))
        q_mmhg = delta_force / (PROBE_AREA_MM2 * 1e-6 * PA_PER_MMHG)
        prediction = predictions[thickness]
        assert delta_force == pytest.approx(float(prediction["delta_force_n"]), abs=1e-12)
        assert q_mmhg == pytest.approx(float(prediction["delta_probe_pressure_mmhg"]), abs=1e-10)


def test_three_mesh_confirmation_preserves_order_but_fails_amplitude_limit():
    result_dir = EXPERIMENT / "results" / "confirmation"
    summary = json.loads((result_dir / "screening_summary.json").read_text(encoding="utf-8"))
    rows = read_csv(result_dir / "mesh_comparison.csv")
    assert summary["status"] == "three_mesh_confirmation_complete"
    assert summary["all_pairs_qc_pass"] is True
    assert summary["thick_end_order_preserved"] is True
    assert summary["refinement_direction_consistent_at_each_thickness"] is True
    assert summary["latest_mesh_change_within_limit"] is False
    assert summary["decision"] == "thick_end_order_robust_but_amplitude_not_mesh_independent"
    assert summary["maximum_absolute_q_change_from_previous_mesh_percent"] == pytest.approx(
        12.312655812588014
    )
    shape = summary["post_hoc_shape_diagnostic"]
    assert shape["latest_contrast_change_percent"] == pytest.approx(-1.4265843972636971)
    assert shape["latest_refinement_q_shift_range_mmhg"] == pytest.approx(0.008782095769214848)
    assert len(rows) == 9
    by_mesh = {
        mesh: sorted(
            (row for row in rows if float(row["mesh_size_mm"]) == pytest.approx(mesh)),
            key=lambda row: float(row["eyelid_thickness_mm"]),
        )
        for mesh in (0.30, 0.24, 0.20)
    }
    for mesh, mesh_rows in by_mesh.items():
        assert len(mesh_rows) == 3
        assert all(row["pair_qc_pass"].lower() == "true" for row in mesh_rows)
        q = [float(row["q_mmhg"]) for row in mesh_rows]
        assert q[0] > q[1] > q[2], mesh
    assert [float(row["q_mmhg"]) for row in by_mesh[0.20]] == pytest.approx(
        [5.858573001782491, 5.645747020674015, 5.251752138059117]
    )
    assert (result_dir / "external_artifact_manifest.json").is_file()
    assert (result_dir / "CONCLUSION.md").is_file()


def test_server_launcher_reuses_shared_runner_and_preserves_fixed_inputs():
    launcher = (EXPERIMENT / "scripts" / "server" / "launch_mesh_campaign_5090d.sh").read_text(
        encoding="utf-8"
    )
    assert "src/runners/run_indentation_sweep.py" in launcher
    assert "--eyelid-thicknesses 1.6 1.8 2.0" in launcher
    assert '--mesh-size-mm "$MESH_SIZE_MM"' in launcher
    assert '--workers "$WORKERS_PER_PRESSURE"' in launcher
    assert '--np "$NP_PER_CASE"' in launcher
    assert '--timeout-seconds "$TIMEOUT_SECONDS"' in launcher
    assert 'PRESSURES="${PRESSURES:-0 20}"' in launcher
    assert '--iop-mmhg "$pressure"' in launcher
    assert "--cornea-material-scale 0.75" in launcher
    assert "--thickness-indent-mm 0.28" in launcher
    assert "--view-policy none" in launcher
    assert "status --porcelain" in launcher


def test_visual_evidence_has_three_real_meshes_and_audited_rst_provenance():
    visual = EXPERIMENT / "results" / "visual_evidence"
    source = json.loads((visual / "source_manifest.json").read_text(encoding="utf-8"))
    assert source["status"] == "existing_rst_postprocessing_only"
    assert source["large_artifact_policy"].startswith("DB and RST remain on 5090d")
    macro = ROOT / "models" / "apdl" / "plot_mesh_independence_sections.mac"
    assert hashlib.sha256(macro.read_bytes()).hexdigest() == source["postprocessing_macro"]["sha256"]
    assert set(source["cases"]) == {"mesh0p30", "mesh0p24", "mesh0p20"}
    local_names = {
        "mesh0p30": ("mesh_0p30_section.png", "mesh_0p30_stress.png"),
        "mesh0p24": ("mesh_0p24_section.png", "mesh_0p24_stress.png"),
        "mesh0p20": ("mesh_0p20_section.png", "mesh_0p20_stress.png"),
    }
    for key, names in local_names.items():
        case = source["cases"][key]
        assert case["condition"]["eyelid_thickness_mm"] == pytest.approx(2.0)
        assert case["condition"]["iop_mmhg"] == pytest.approx(20.0)
        assert case["condition"]["indent_mm"] == pytest.approx(0.28)
        assert case["postprocess"]["run_completed"] is True
        assert case["postprocess"]["ansys_error_count"] == 0
        assert len(case["source_rst"]["sha256"]) == 64
        for output, name in zip(case["outputs"], names, strict=True):
            path = visual / "raw" / name
            assert path.is_file() and path.stat().st_size == output["size_bytes"]
            assert hashlib.sha256(path.read_bytes()).hexdigest() == output["sha256"]


def test_fixed_scale_auxiliary_views_use_one_unclipped_range_and_keep_separate_provenance():
    visual = EXPERIMENT / "results" / "visual_evidence"
    source = json.loads((visual / "fixed_scale_source_manifest.json").read_text(encoding="utf-8"))
    assert source["status"] == "existing_rst_postprocessing_only"
    assert source["evidence_role"] == "fixed_scale_auxiliary_visual_localization"
    assert source["fixed_scale"]["range_kpa"] == [0.0, 60.0]
    assert source["fixed_scale"]["maximum_pa"] > 55606
    macro = ROOT / "models" / "apdl" / "plot_mesh_independence_fixed_scale.mac"
    assert hashlib.sha256(macro.read_bytes()).hexdigest() == source["postprocessing_macro"]["sha256"]
    names = {
        "mesh0p30": "mesh_0p30_stress_fixed_0_60kpa.png",
        "mesh0p24": "mesh_0p24_stress_fixed_0_60kpa.png",
        "mesh0p20": "mesh_0p20_stress_fixed_0_60kpa.png",
    }
    assert set(source["cases"]) == set(names)
    for key, name in names.items():
        case = source["cases"][key]
        assert case["fixed_contour"]["minimum"] == pytest.approx(0.0)
        assert case["fixed_contour"]["maximum"] == pytest.approx(60000.0)
        assert case["postprocess"]["run_completed"] is True
        assert case["postprocess"]["ansys_error_count"] == 0
        path = visual / "raw" / name
        assert path.stat().st_size == case["output"]["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == case["output"]["sha256"]


def test_visual_timing_table_covers_all_accepted_endpoints_and_keeps_preflights_separate():
    visual = EXPERIMENT / "results" / "visual_evidence"
    rows = read_csv(visual / "simulation_timing.csv")
    keys = {
        (float(row["mesh_size_mm"]), float(row["eyelid_thickness_mm"]), float(row["iop_mmhg"]))
        for row in rows
    }
    assert len(rows) == len(keys) == 18
    assert keys == {
        (mesh, thickness, pressure)
        for mesh in (0.30, 0.24, 0.20)
        for thickness in (1.60, 1.80, 2.00)
        for pressure in (0.0, 20.0)
    }
    assert all(row["accepted_endpoint"] == "true" for row in rows)
    assert all(row["status"] == "complete" for row in rows)
    assert all(float(row["elapsed_seconds"]) > 0 for row in rows)
    contested = [row for row in rows if row["timing_quality"].startswith("resource_contended")]
    assert len(contested) == 1
    assert (float(contested[0]["mesh_size_mm"]), float(contested[0]["iop_mmhg"])) == (0.20, 0.0)

    preflight = read_csv(visual / "resource_preflight_timing.csv")
    assert len(preflight) == 3
    assert all(row["numerical_endpoint_accepted"] == "false" for row in preflight)
    assert sum(float(row["elapsed_seconds"]) for row in preflight) == pytest.approx(41435.0)

    summary = json.loads((visual / "timing_summary.json").read_text(encoding="utf-8"))
    assert summary["accepted_endpoint_count"] == 18
    assert summary["per_mesh"]["0.24"]["accepted_campaign_calendar_hours"] == pytest.approx(
        4.595833333333333
    )
    assert summary["per_mesh"]["0.20"]["sum_case_wall_hours"] == pytest.approx(
        30.182746944444443
    )
    assert summary["nonaccepted_resource_events"]["numerical_endpoints_used"] == 0

    artifact_manifest = json.loads((visual / "artifact_manifest.json").read_text(encoding="utf-8"))
    assert artifact_manifest["artifact_count"] == len(artifact_manifest["artifacts"])
    for artifact in artifact_manifest["artifacts"]:
        path = ROOT / artifact["path"]
        assert path.stat().st_size == artifact["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"]


def test_visual_report_embeds_composites_and_preserves_plot_interpretation_boundaries():
    visual = EXPERIMENT / "results" / "visual_evidence"
    for name in (
        "contact_zone_mesh_comparison.png",
        "mesh_sections_comparison.png",
        "stress_sections_comparison.png",
        "stress_sections_fixed_scale_comparison.png",
    ):
        assert (visual / name).is_file()
    report = (EXPERIMENT / "DETAILED_REPORT.md").read_text(encoding="utf-8")
    assert "contact_zone_mesh_comparison.png" in report
    assert "stress_sections_comparison.png" in report
    assert "stress_sections_fixed_scale_comparison.png" in report
    assert "MAPDL 原生自动色标" in report
    assert "同色同值的空间定位" in report
    assert "不能仅凭颜色" in report
    assert "绝对幅值尚未网格无关" in report
    macro = (ROOT / "models" / "apdl" / "plot_mesh_independence_sections.mac").read_text(
        encoding="utf-8"
    )
    assert "/cplane,1" in macro
    assert "/dscale,1,1" in macro
    assert "/edge,1,1" in macro
    assert "plnsol,s,eqv" in macro
