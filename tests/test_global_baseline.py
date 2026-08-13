import json
import math
import re
from pathlib import Path

import pytest

from src.runners import run_indentation_sweep as runner


ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "config" / "model_baseline.json"
EXPECTED_EYELID_THICKNESS_MM = 1.25


def load_json(relative_path: str) -> dict:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def test_machine_readable_global_baseline_is_frozen_to_t1p25() -> None:
    config = load_json("config/model_baseline.json")
    assert config["schema_version"] == 1
    assert config["canonical_baseline"]["eyelid_thickness_mm"] == EXPECTED_EYELID_THICKNESS_MM
    assert config["scope"]["default_for_all_new_experiments"] is True
    assert config["scope"]["historical_results_are_immutable"] is True
    assert config["override_policy"]["explicit_actual_thickness_required"] is True
    assert config["override_policy"]["explicit_reason_required"] is True


def test_runner_uses_global_baseline_for_every_non_thickness_profile() -> None:
    assert runner.GLOBAL_BASELINE_PATH == BASELINE_PATH
    assert runner.DEFAULT_EYELID_THICKNESS_MM == EXPECTED_EYELID_THICKNESS_MM
    assert runner.CaseSpec(0.0, 0.0, 0).eyelid_thickness_mm == EXPECTED_EYELID_THICKNESS_MM

    parser = runner.build_parser()
    for profile in ("smoke", "coarse", "full"):
        selected_profile, cases = runner.choose_cases(
            parser, parser.parse_args(["--profile", profile])
        )
        assert selected_profile == profile
        assert cases
        assert all(
            math.isclose(
                case.eyelid_thickness_mm,
                EXPECTED_EYELID_THICKNESS_MM,
                abs_tol=1e-12,
            )
            for case in cases
        )


def test_runner_requires_explicit_override_and_preserves_thickness_sweeps() -> None:
    parser = runner.build_parser()
    without_reason = parser.parse_args(
        ["--profile", "smoke", "--baseline-eyelid-thickness-mm", "1.6"]
    )
    with pytest.raises(SystemExit):
        runner.choose_cases(parser, without_reason)

    _, overridden = runner.choose_cases(
        parser,
        parser.parse_args(
            [
                "--profile",
                "smoke",
                "--baseline-eyelid-thickness-mm",
                "1.6",
                "--eyelid-thickness-override-reason",
                "registered boundary sensitivity",
            ]
        ),
    )
    assert all(case.eyelid_thickness_mm == 1.6 for case in overridden)

    profile, thickness_cases = runner.choose_cases(
        parser, parser.parse_args(["--profile", "thickness"])
    )
    assert profile == "thickness"
    assert [case.eyelid_thickness_mm for case in thickness_cases] == list(runner.THICKNESS_MM)
    assert any(
        not math.isclose(
            case.eyelid_thickness_mm,
            EXPECTED_EYELID_THICKNESS_MM,
            abs_tol=1e-12,
        )
        for case in thickness_cases
    )


def test_apdl_direct_call_fallback_matches_global_baseline() -> None:
    apdl = (ROOT / "models" / "apdl" / "param_eye_sweep.mac").read_text(
        encoding="utf-8"
    )
    assert "global baseline default 1.25 mm" in apdl
    assert re.search(r"(?m)^te = 1\.25e-3\s+! repository-wide", apdl)
    assert "te = 1.0e-3" not in apdl


def test_analysis_and_baseline_high_iop_configs_match_global_reference() -> None:
    analysis_config = (ROOT / "analysis" / "config.yaml").read_text(encoding="utf-8")
    match = re.search(r"(?m)^\s*reference_thickness_mm:\s*([0-9.]+)\s*$", analysis_config)
    assert match
    assert float(match.group(1)) == EXPECTED_EYELID_THICKNESS_MM

    for relative_path in (
        "high_iop_mechanical_transfer_t1p25_c0p60/config/calibration_0_to_50.json",
        "high_iop_mechanical_transfer_t1p25_c0p60/config/extrapolation_50_to_60.json",
        "high_iop_mechanical_transfer_t1p25_c0p60/config/interface_force_integrals.json",
    ):
        config = load_json(relative_path)
        assert config["global_baseline_reference"] == {
            "eyelid_thickness_mm": EXPECTED_EYELID_THICKNESS_MM,
            "case_role": "canonical_baseline",
        }
        assert config["geometry"]["eyelid_thickness_mm"] == EXPECTED_EYELID_THICKNESS_MM


def test_thick_end_mesh_experiments_declare_baseline_roles() -> None:
    original = load_json("thickness_mesh_independence/config/experiment.json")
    original_reference = original["global_baseline_reference"]
    assert original_reference["eyelid_thickness_mm"] == EXPECTED_EYELID_THICKNESS_MM
    assert original_reference["case_role"] == "explicit_thickness_override"
    assert original_reference["override_reason"].strip()

    aggressive = load_json(
        "thickness_mesh_independence/aggressive_refinement/config/experiment.json"
    )
    reference = aggressive["global_baseline_reference"]
    assert reference["eyelid_thickness_mm"] == EXPECTED_EYELID_THICKNESS_MM
    assert reference["case_role"] == "canonical_baseline"
    assert reference["legacy_explicit_overrides_mm"] == [1.6, 1.8, 2.0]
    assert reference["override_reason"].strip()
    assert aggressive["baseline_t1p25_campaign"]["eyelid_thickness_mm"] == 1.25
    assert aggressive["baseline_t1p25_campaign"]["iop20_authorized"] is False


def test_standard_launcher_passes_the_global_baseline_explicitly() -> None:
    launcher = (ROOT / "ops" / "launch-indentation-sweep-5090d.sh").read_text(
        encoding="utf-8"
    )
    assert "config/model_baseline.json" in launcher
    assert '--baseline-eyelid-thickness-mm "$baseline_eyelid_thickness_mm"' in launcher
