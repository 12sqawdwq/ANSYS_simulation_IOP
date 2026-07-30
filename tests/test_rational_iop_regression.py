from __future__ import annotations

import importlib.util
import json
import math
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_ROOT = REPO_ROOT / "high_iop_mechanical_transfer_t1p25_c0p60"
SCRIPT = EXPERIMENT_ROOT / "fit_rational_piop_vs_pprobe.py"
SOURCE = EXPERIMENT_ROOT / "results" / "20260730_290d0544_iop_0_to_50_step2p5_summary.json"
RESULT = EXPERIMENT_ROOT / "results" / "20260730_rational_regression_0_to_50_step2p5.json"
FIGURE = EXPERIMENT_ROOT / "figures" / "piop_vs_delta_pprobe_rational_regression_0_to_50_step2p5.png"


def load_module():
    spec = importlib.util.spec_from_file_location("rational_iop_regression", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RationalIopRegressionTests(unittest.TestCase):
    def test_profile_fit_reproduces_frozen_parameters(self) -> None:
        module = load_module()
        rows = module.load_points(SOURCE)
        a, b = module.fit_rational(rows)
        self.assertTrue(math.isclose(a, 0.06531173069023494, rel_tol=0.0, abs_tol=1e-9))
        self.assertTrue(math.isclose(b, 1.8273148619678283, rel_tol=0.0, abs_tol=1e-9))

    def test_result_metrics_and_denominator_are_valid(self) -> None:
        result = json.loads(RESULT.read_text(encoding="utf-8"))
        parameters = result["parameters"]
        metrics = result["metrics"]
        self.assertEqual(metrics["point_count_including_origin"], 21)
        self.assertTrue(math.isclose(metrics["r_squared_iop_space"], 0.9960280905251944, rel_tol=0.0, abs_tol=1e-12))
        self.assertTrue(math.isclose(metrics["mae_all_points_mmhg"], 0.7658358446494337, rel_tol=0.0, abs_tol=1e-12))
        self.assertGreater(metrics["minimum_denominator_on_observed_grid"], 0.3)
        self.assertGreater(parameters["a_per_mmhg"], 0.0)
        self.assertGreater(parameters["b_dimensionless"], 0.0)
        self.assertTrue(result["interpretation"]["new_midpoint_holdout_consumed_by_this_fit"])
        self.assertGreater(FIGURE.stat().st_size, 90_000)


if __name__ == "__main__":
    unittest.main()
