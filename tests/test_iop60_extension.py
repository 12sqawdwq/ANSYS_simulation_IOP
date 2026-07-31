from __future__ import annotations

import importlib.util
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT = REPO_ROOT / "high_iop_mechanical_transfer_t1p25_c0p60"
SPEC = ROOT / "run_spec_iop_50_to_60_step2p5.json"
PLOTTER = ROOT / "plot_piop_vs_delta_pprobe_2p5.py"
DENSE_RESULT = ROOT / "results" / "20260730_290d0544_iop_0_to_50_step2p5_summary.json"
INVERSE_RESULT = ROOT / "results" / "20260730_rational_regression_0_to_50_step2p5.json"
LOAD_SHARE_RESULT = ROOT / "results" / "20260731_global_load_share_derivation.json"
EVALUATOR = ROOT / "evaluate_iop60_extrapolation.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Iop60ExtensionTests(unittest.TestCase):
    def test_spec_extends_exact_two_point_five_grid_without_resolving_old_points(self) -> None:
        spec = json.loads(SPEC.read_text(encoding="utf-8"))
        expected = [index * 2.5 for index in range(25)]
        self.assertEqual(spec["pressure_step_mmhg"], 2.5)
        self.assertEqual(spec["final_pressure_grid_mmhg"], expected)
        self.assertEqual(spec["plotted_pressure_grid_mmhg"], expected)
        self.assertEqual(spec["reused_pressure_grid"]["pressures_mmhg"], expected[:21])
        self.assertEqual(spec["new_solver_pressures_mmhg"], expected[21:])
        self.assertEqual(spec["solver"]["execution_order"][0], [60.0])
        self.assertEqual(spec["solver"]["maximum_parallel_cases"], 2)
        self.assertEqual(spec["geometry"]["solve_indent_mm"], 0.28)
        self.assertEqual(spec["geometry"]["expected_primary_result_indent_mm"], 0.259875)
        self.assertIn("do not refit", spec["interpretation"]["model_policy"])

    def test_frozen_extrapolation_parameters_match_prelaunch_results(self) -> None:
        spec = json.loads(SPEC.read_text(encoding="utf-8"))["frozen_rational_models_for_extrapolation_only"]
        inverse = json.loads(INVERSE_RESULT.read_text(encoding="utf-8"))["parameters"]
        load_share = json.loads(LOAD_SHARE_RESULT.read_text(encoding="utf-8"))["geometric_forward_parameters"]
        self.assertTrue(math.isclose(spec["inverse_regression_0_to_50"]["a_per_mmhg"], inverse["a_per_mmhg"], abs_tol=1e-15))
        self.assertTrue(math.isclose(spec["inverse_regression_0_to_50"]["b_dimensionless"], inverse["b_dimensionless"], abs_tol=1e-15))
        self.assertTrue(math.isclose(spec["load_share_reparameterization_10_to_50"]["a_per_mmhg"], load_share["a_per_mmhg"], abs_tol=1e-15))
        self.assertTrue(math.isclose(spec["load_share_reparameterization_10_to_50"]["b_dimensionless"], load_share["b_dimensionless"], abs_tol=1e-15))

    def test_generalized_plotter_still_accepts_frozen_dense_grid(self) -> None:
        module = load_module(PLOTTER, "plot_iop60_extension_test")
        points, step = module.load_points(DENSE_RESULT)
        self.assertEqual(step, 2.5)
        self.assertEqual(len(points), 21)
        self.assertEqual(points[0][0], 0.0)
        self.assertEqual(points[-1][0], 50.0)
        self.assertTrue(math.isclose(points[-1][1], 9.906446283258044, abs_tol=1e-12))

    def test_frozen_model_evaluator_round_trips_synthetic_unseen_points(self) -> None:
        spec = json.loads(SPEC.read_text(encoding="utf-8"))
        source = json.loads(DENSE_RESULT.read_text(encoding="utf-8"))
        inverse = spec["frozen_rational_models_for_extrapolation_only"]["inverse_regression_0_to_50"]
        rows = list(source["rows"])
        zero_force = next(
            row["probe_force_n"] for row in rows
            if row["state"] == "primary_0p26" and row["input_iop_mmhg"] == 0.0
        )
        factor = source["pressure_factor_mmhg_per_n"]
        for pressure in spec["new_solver_pressures_mmhg"]:
            q = pressure / (inverse["b_dimensionless"] + inverse["a_per_mmhg"] * pressure)
            rows.append({
                "state": "primary_0p26",
                "input_iop_mmhg": pressure,
                "actual_indent_mm": 0.259875,
                "probe_force_n": zero_force + q / factor,
                "delta_probe_pressure_mmhg": q,
                "source_kind": "new_supplemental_solver",
            })
        payload = {
            "campaign_pass": True,
            "rows": rows,
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "summary.json"
            output_json = root / "evaluation.json"
            input_path.write_text(json.dumps(payload), encoding="utf-8")
            completed = subprocess.run([
                sys.executable, str(EVALUATOR),
                "--input-summary", str(input_path),
                "--run-spec", str(SPEC),
                "--output-json", str(output_json),
                "--output-csv", str(root / "evaluation.csv"),
                "--output-figure", str(root / "evaluation.png"),
            ], capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "frozen_models_evaluated_without_refit")
            self.assertLess(
                result["metrics"]["inverse_regression_0_to_50"]["unseen_52p5_to_60"]["rmse_mmhg"],
                1e-12,
            )
            self.assertTrue((root / "evaluation.png").is_file())


if __name__ == "__main__":
    unittest.main()
