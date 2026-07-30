from __future__ import annotations

import json
import math
import unittest
from pathlib import Path

from src.runners.run_indentation_sweep import PA_PER_MMHG, material_properties


REPO_ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_ROOT = REPO_ROOT / "high_iop_mechanical_transfer_t1p25_c0p60"
SPEC = EXPERIMENT_ROOT / "run_spec.json"
FULL_SPEC = EXPERIMENT_ROOT / "run_spec_full.json"
SUPPLEMENT_SPEC = EXPERIMENT_ROOT / "run_spec_iop_5_to_50.json"
DENSE_SUPPLEMENT_SPEC = EXPERIMENT_ROOT / "run_spec_iop_2p5.json"
SUPPLEMENT_RESULT = EXPERIMENT_ROOT / "results" / "20260730_440e44e5_iop_5_to_50_summary.json"


class HighIopPreflightTests(unittest.TestCase):
    def test_exact_pressure_conversion_is_frozen(self) -> None:
        spec = json.loads(SPEC.read_text(encoding="utf-8"))
        self.assertEqual(PA_PER_MMHG, spec["pressure"]["pa_per_mmhg"])
        self.assertTrue(math.isclose(
            spec["pressure"]["iop_pa"], 40.0 * PA_PER_MMHG, rel_tol=0.0, abs_tol=1e-12
        ))

    def test_absolute_material_properties_match_run_spec(self) -> None:
        spec = json.loads(SPEC.read_text(encoding="utf-8"))["absolute_material_parameters"]
        for tissue in ("eyelid", "cornea"):
            expected = material_properties(spec[tissue]["c10_mpa"], spec[tissue]["c01_mpa"])
            for field in (
                "c10_mpa",
                "c01_mpa",
                "d1_pa_inv",
                "initial_shear_modulus_mpa",
                "initial_bulk_modulus_mpa",
                "equivalent_initial_young_modulus_mpa",
                "equivalent_initial_poisson_ratio",
            ):
                self.assertTrue(math.isclose(
                    expected[field], spec[tissue][field], rel_tol=0.0, abs_tol=1e-14
                ), f"{tissue}.{field}")

    def test_primary_and_solve_indent_are_distinct(self) -> None:
        geometry = json.loads(SPEC.read_text(encoding="utf-8"))["geometry"]
        self.assertEqual(geometry["solve_indent_mm"], 0.28)
        self.assertEqual(geometry["primary_target_indent_mm"], 0.26)
        self.assertLess(geometry["primary_target_indent_mm"], geometry["solve_indent_mm"])

    def test_full_matrix_reuses_only_the_accepted_40_mmhg_case(self) -> None:
        spec = json.loads(FULL_SPEC.read_text(encoding="utf-8"))
        self.assertEqual(spec["pressure_matrix_mmhg"], [0.0, 20.0, 25.0, 30.0, 35.0, 40.0])
        self.assertEqual(spec["new_solver_pressures_mmhg"], [0.0, 20.0, 25.0, 30.0, 35.0])
        self.assertTrue(spec["reused_iop40_preflight"]["preflight_pass"])
        self.assertEqual(spec["solver"]["maximum_parallel_cases"], 2)
        self.assertEqual(spec["geometry"]["solve_indent_mm"], 0.28)
        self.assertEqual(spec["geometry"]["primary_target_indent_mm"], 0.26)

    def test_supplement_fills_exact_five_mmhg_grid_through_50(self) -> None:
        spec = json.loads(SUPPLEMENT_SPEC.read_text(encoding="utf-8"))
        self.assertEqual(spec["final_pressure_grid_mmhg"], [float(value) for value in range(0, 51, 5)])
        self.assertEqual(spec["plotted_pressure_grid_mmhg"], [float(value) for value in range(5, 51, 5)])
        self.assertEqual(spec["new_solver_pressures_mmhg"], [5.0, 10.0, 15.0, 45.0, 50.0])
        self.assertEqual(spec["solver"]["execution_order"][0], [50.0])
        self.assertEqual(spec["solver"]["maximum_parallel_cases"], 2)
        self.assertEqual(spec["geometry"]["solve_indent_mm"], 0.28)
        self.assertEqual(spec["geometry"]["primary_target_indent_mm"], 0.26)
        self.assertTrue(spec["reused_formal_matrix"]["campaign_pass"])

    def test_dense_supplement_fills_two_point_five_mmhg_grid(self) -> None:
        spec = json.loads(DENSE_SUPPLEMENT_SPEC.read_text(encoding="utf-8"))
        expected = [index * 2.5 for index in range(21)]
        self.assertEqual(spec["pressure_step_mmhg"], 2.5)
        self.assertEqual(spec["final_pressure_grid_mmhg"], expected)
        self.assertEqual(spec["plotted_pressure_grid_mmhg"], expected)
        self.assertEqual(spec["new_solver_pressures_mmhg"], expected[1::2])
        self.assertEqual(spec["reused_pressure_grid"]["pressures_mmhg"], expected[::2])
        self.assertEqual(spec["solver"]["maximum_parallel_cases"], 2)
        self.assertTrue(all(len(wave) == 2 for wave in spec["solver"]["execution_order"]))
        self.assertEqual(spec["geometry"]["solve_indent_mm"], 0.28)
        self.assertEqual(spec["geometry"]["primary_target_indent_mm"], 0.26)

    def test_supplement_result_contains_monotonic_actual_fe_scatter(self) -> None:
        result = json.loads(SUPPLEMENT_RESULT.read_text(encoding="utf-8"))
        self.assertTrue(result["campaign_pass"])
        self.assertTrue(all(result["qc"].values()))
        rows = [
            row for row in result["rows"]
            if row["state"] == "primary_0p26" and row["input_iop_mmhg"] > 0
        ]
        self.assertEqual([row["input_iop_mmhg"] for row in rows], [float(value) for value in range(5, 51, 5)])
        readings = [row["delta_probe_pressure_mmhg"] for row in rows]
        self.assertTrue(all(right > left for left, right in zip(readings, readings[1:])))
        self.assertTrue(math.isclose(readings[0], 1.420075281027457, rel_tol=0.0, abs_tol=1e-12))
        self.assertTrue(math.isclose(readings[-1], 9.906446283258044, rel_tol=0.0, abs_tol=1e-12))


if __name__ == "__main__":
    unittest.main()
