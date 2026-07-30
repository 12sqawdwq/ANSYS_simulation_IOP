from __future__ import annotations

import json
import math
import unittest
from pathlib import Path

from src.runners.run_indentation_sweep import PA_PER_MMHG, material_properties


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = REPO_ROOT / "high_iop_mechanical_transfer_t1p25_c0p60" / "run_spec.json"


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


if __name__ == "__main__":
    unittest.main()
