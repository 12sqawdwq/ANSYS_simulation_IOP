from __future__ import annotations

import importlib.util
import json
import math
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "high_iop_mechanical_transfer_t1p25_c0p60" / "derive_global_load_share_model.py"
RESULT = REPO_ROOT / "high_iop_mechanical_transfer_t1p25_c0p60" / "results" / "20260731_global_load_share_derivation.json"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GlobalLoadShareDerivationTests(unittest.TestCase):
    def test_helper_fit_and_rational_inverse(self) -> None:
        module = load_module(SCRIPT, "derive_global_load_share_model_test")
        fit = module.linear_fit([10.0, 20.0, 30.0], [2.0, 3.0, 4.0])
        self.assertTrue(math.isclose(fit["intercept"], 1.0))
        self.assertTrue(math.isclose(fit["slope_per_mmhg"], 0.1))
        self.assertTrue(math.isclose(fit["r_squared"], 1.0))
        self.assertTrue(math.isclose(module.rational(4.0, 0.05, 2.0), 10.0))

    def test_frozen_derivation_and_qc(self) -> None:
        result = json.loads(RESULT.read_text(encoding="utf-8"))
        self.assertTrue(result["derivation_pass"])
        qc = result["qc"]
        self.assertTrue(all(value for key, value in qc.items() if key != "maximum_chi_identity_error"))
        self.assertLess(qc["maximum_chi_identity_error"], 1.0e-6)
        self.assertEqual(len(result["rows"]), 21)
        fit = result["load_share_fit"]
        self.assertTrue(math.isclose(fit["c0_dimensionless"], 11.344814940200989, abs_tol=1e-12))
        self.assertTrue(math.isclose(fit["c1_per_mmhg"], 0.44949578329440343, abs_tol=1e-12))
        self.assertGreater(fit["r_squared"], 0.997)

    def test_parameter_map_uses_independent_geometric_projected_area(self) -> None:
        result = json.loads(RESULT.read_text(encoding="utf-8"))
        cfg = result["configuration"]
        fit = result["load_share_fit"]
        params = result["geometric_forward_parameters"]
        area = cfg["geometric_iop_projected_area_mm2"]
        probe_area = cfg["probe_area_mm2"]
        self.assertTrue(math.isclose(params["a_per_mmhg"], probe_area * fit["c1_per_mmhg"] / area, abs_tol=1e-14))
        self.assertTrue(math.isclose(params["b_dimensionless"], probe_area * fit["c0_dimensionless"] / area, abs_tol=1e-14))
        self.assertLess(abs(result["projected_area_validation"]["geometric_vs_stable_balance_relative_difference"]), 0.005)
        self.assertLess(abs(result["inverse_regression_reference"]["geometric_a_relative_difference"]), 0.05)
        self.assertLess(abs(result["inverse_regression_reference"]["geometric_b_relative_difference"]), 0.06)


if __name__ == "__main__":
    unittest.main()
