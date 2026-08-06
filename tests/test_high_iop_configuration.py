from __future__ import annotations

import json
import math
import unittest
from pathlib import Path

from src.runners.run_indentation_sweep import PA_PER_MMHG, material_properties


REPO_ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_ROOT = REPO_ROOT / "high_iop_mechanical_transfer_t1p25_c0p60"
CALIBRATION_SPEC = EXPERIMENT_ROOT / "config" / "calibration_0_to_50.json"
EXTRAPOLATION_SPEC = EXPERIMENT_ROOT / "config" / "extrapolation_50_to_60.json"
STEP5_RESULT = EXPERIMENT_ROOT / "results" / "20260730_440e44e5_iop_5_to_50_summary.json"
CALIBRATION_RESULT = EXPERIMENT_ROOT / "results" / "20260730_290d0544_iop_0_to_50_step2p5_summary.json"


class HighIopConfigurationTests(unittest.TestCase):
    def test_exact_pressure_conversion_is_frozen(self) -> None:
        for path in (CALIBRATION_SPEC, EXTRAPOLATION_SPEC):
            spec = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(PA_PER_MMHG, spec["pressure_conversion"]["pa_per_mmhg"])

    def test_absolute_material_properties_match_current_specs(self) -> None:
        calibration = json.loads(CALIBRATION_SPEC.read_text(encoding="utf-8"))
        extrapolation = json.loads(EXTRAPOLATION_SPEC.read_text(encoding="utf-8"))
        self.assertEqual(
            calibration["absolute_material_parameters"],
            extrapolation["absolute_material_parameters"],
        )
        for tissue, values in calibration["absolute_material_parameters"].items():
            expected = material_properties(values["c10_mpa"], values["c01_mpa"])
            self.assertTrue(math.isclose(expected["c10_mpa"], values["c10_mpa"], abs_tol=1e-14))
            self.assertTrue(math.isclose(expected["c01_mpa"], values["c01_mpa"], abs_tol=1e-14))
            self.assertTrue(math.isclose(expected["d1_pa_inv"], values["d1_pa_inv"], abs_tol=1e-14))

    def test_primary_and_solve_indent_are_distinct(self) -> None:
        for path in (CALIBRATION_SPEC, EXTRAPOLATION_SPEC):
            geometry = json.loads(path.read_text(encoding="utf-8"))["geometry"]
            self.assertEqual(geometry["solve_indent_mm"], 0.28)
            self.assertEqual(geometry["primary_target_indent_mm"], 0.26)
            self.assertEqual(geometry["expected_primary_result_indent_mm"], 0.259875)
            self.assertLess(geometry["primary_target_indent_mm"], geometry["solve_indent_mm"])

    def test_calibration_spec_fills_two_point_five_mmhg_grid(self) -> None:
        spec = json.loads(CALIBRATION_SPEC.read_text(encoding="utf-8"))
        expected = [index * 2.5 for index in range(21)]
        self.assertEqual(spec["pressure_step_mmhg"], 2.5)
        self.assertEqual(spec["final_pressure_grid_mmhg"], expected)
        self.assertEqual(spec["plotted_pressure_grid_mmhg"], expected)
        self.assertEqual(spec["new_solver_pressures_mmhg"], expected[1::2])
        self.assertEqual(spec["reused_pressure_grid"]["pressures_mmhg"], expected[::2])
        self.assertEqual(spec["solver"]["maximum_parallel_cases"], 2)
        self.assertTrue(all(len(wave) == 2 for wave in spec["solver"]["execution_order"]))

    def test_calibration_result_contains_all_actual_fe_points(self) -> None:
        result = json.loads(CALIBRATION_RESULT.read_text(encoding="utf-8"))
        self.assertTrue(result["campaign_pass"])
        self.assertTrue(all(result["qc"].values()))
        rows = [row for row in result["rows"] if row["state"] == "primary_0p26"]
        expected = [index * 2.5 for index in range(21)]
        self.assertEqual([row["input_iop_mmhg"] for row in rows], expected)
        readings = [row["delta_probe_pressure_mmhg"] for row in rows]
        self.assertTrue(all(right > left for left, right in zip(readings, readings[1:])))
        self.assertTrue(math.isclose(readings[1], 0.21312253920016047, abs_tol=1e-12))
        self.assertTrue(math.isclose(readings[-2], 9.65902083101028, abs_tol=1e-12))
        self.assertEqual(
            [row["source_kind"] for row in rows[1::2]],
            ["new_supplemental_solver"] * 10,
        )

    def test_historical_step5_result_remains_reproducible_input_evidence(self) -> None:
        result = json.loads(STEP5_RESULT.read_text(encoding="utf-8"))
        self.assertTrue(result["campaign_pass"])
        self.assertTrue(all(result["qc"].values()))
        rows = [
            row
            for row in result["rows"]
            if row["state"] == "primary_0p26" and row["input_iop_mmhg"] > 0
        ]
        self.assertEqual(
            [row["input_iop_mmhg"] for row in rows],
            [float(value) for value in range(5, 51, 5)],
        )
        readings = [row["delta_probe_pressure_mmhg"] for row in rows]
        self.assertTrue(all(right > left for left, right in zip(readings, readings[1:])))


if __name__ == "__main__":
    unittest.main()
