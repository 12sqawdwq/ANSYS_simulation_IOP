from __future__ import annotations

import importlib.util
import json
import math
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_ROOT = REPO_ROOT / "high_iop_mechanical_transfer_t1p25_c0p60"
SCRIPT = EXPERIMENT_ROOT / "derive_forward_rational_parameters.py"
SOURCE = EXPERIMENT_ROOT / "results" / "20260730_290d0544_iop_0_to_50_step2p5_summary.json"
INVERSE = EXPERIMENT_ROOT / "results" / "20260730_rational_regression_0_to_50_step2p5.json"
RESULT = EXPERIMENT_ROOT / "results" / "20260731_forward_rational_parameters_ac5_proxy.json"
FIGURE = EXPERIMENT_ROOT / "figures" / "forward_vs_inverse_rational_iop_0_to_50_step2p5.png"


def load_module():
    spec = importlib.util.spec_from_file_location("forward_rational_derivation", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ForwardRationalDerivationTests(unittest.TestCase):
    def test_area_and_transfer_submodels_reproduce_frozen_result(self) -> None:
        module = load_module()
        rows = module.load_rows(SOURCE)
        inverse = json.loads(INVERSE.read_text(encoding="utf-8"))
        payload, output_rows = module.derive(rows, inverse)
        area = payload["area_model"]
        transfer = payload["transfer_model"]
        forward = payload["forward_local_linearization"]
        self.assertEqual(len(output_rows), 21)
        self.assertTrue(math.isclose(area["c0"], 2.7983326638052395, rel_tol=0.0, abs_tol=1e-10))
        self.assertTrue(math.isclose(area["c1_per_mmhg"], 0.010436501169572865, rel_tol=0.0, abs_tol=1e-10))
        self.assertTrue(math.isclose(transfer["eta0"], 0.6619537699039207, rel_tol=0.0, abs_tol=1e-10))
        self.assertTrue(math.isclose(transfer["eta1_per_mmhg"], 0.01798457244228301, rel_tol=0.0, abs_tol=1e-10))
        self.assertTrue(math.isclose(forward["a_per_mmhg"], 0.06662009837002528, rel_tol=0.0, abs_tol=1e-10))
        self.assertTrue(math.isclose(forward["b_dimensionless"], 1.7350568491710625, rel_tol=0.0, abs_tol=1e-10))

    def test_forward_proxy_is_close_but_not_identical_to_inverse_fit(self) -> None:
        result = json.loads(RESULT.read_text(encoding="utf-8"))
        forward = result["forward_local_linearization"]
        constant_eta = result["constant_eta_diagnostic"]
        self.assertLess(abs(forward["a_difference_from_inverse_percent"]), 3.0)
        self.assertLess(abs(forward["b_difference_from_inverse_percent"]), 6.0)
        self.assertLess(forward["metrics_all_0_to_50"]["rmse_mmhg"], 1.25)
        self.assertGreater(abs(constant_eta["a_per_mmhg"] - forward["a_per_mmhg"]), 0.05)
        self.assertIn("circularity_warning", result["transfer_model"])
        self.assertGreater(FIGURE.stat().st_size, 90_000)


if __name__ == "__main__":
    unittest.main()
