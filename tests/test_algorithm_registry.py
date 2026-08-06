from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "algorithms" / "algorithm_registry.json"


class AlgorithmRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))

    def test_two_generations_have_unambiguous_nonproduction_status(self) -> None:
        self.assertFalse(self.registry["production_algorithm_available"])
        generations = {item["id"]: item for item in self.registry["generations"]}
        self.assertEqual(
            set(generations),
            {"historical_empirical_ksensor", "current_mechanistic_area_transfer"},
        )
        self.assertEqual(
            generations["historical_empirical_ksensor"]["lifecycle_status"],
            "retired_diagnostic_only",
        )
        self.assertEqual(
            generations["current_mechanistic_area_transfer"]["lifecycle_status"],
            "current_research_framework_not_production",
        )

    def test_all_current_and_mixed_paths_exist(self) -> None:
        entries = [
            *self.registry["current_files"],
            *self.registry["mixed_compatibility_files"],
        ]
        for entry in entries:
            path = REPO_ROOT / entry["path"]
            self.assertTrue(path.is_file(), entry["path"])

    def test_registry_parameters_match_authoritative_files(self) -> None:
        generations = {item["id"]: item for item in self.registry["generations"]}
        old_parameters = generations["historical_empirical_ksensor"]["parameters"]
        calibration = json.loads(
            (
                REPO_ROOT
                / "high_iop_mechanical_transfer_t1p25_c0p60"
                / "config"
                / "calibration_0_to_50.json"
            ).read_text(encoding="utf-8")
        )["frozen_sensor_models_for_diagnostic_only"]
        self.assertEqual(old_parameters["primary_0p259875"], calibration["primary_0p26"])
        self.assertEqual(old_parameters["sensitivity_0p28"], calibration["sensitivity_0p28"])

        rational = json.loads(
            (
                REPO_ROOT
                / "high_iop_mechanical_transfer_t1p25_c0p60"
                / "results"
                / "20260730_rational_regression_0_to_50_step2p5.json"
            ).read_text(encoding="utf-8")
        )
        model = next(
            item
            for item in self.registry["diagnostic_models"]
            if item["id"] == "fixed_inverse_rational_0_to_50"
        )
        self.assertEqual(model["a_per_mmhg"], rational["parameters"]["a_per_mmhg"])
        self.assertEqual(model["b_dimensionless"], rational["parameters"]["b_dimensionless"])
        self.assertEqual(
            model["fit_rmse_mmhg"], rational["metrics"]["rmse_all_points_mmhg"]
        )

    def test_historical_git_blobs_when_full_history_is_available(self) -> None:
        first = self.registry["historical_files"][0]["commit"]
        available = subprocess.run(
            ["git", "cat-file", "-e", f"{first}^{{commit}}"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
        )
        if available.returncode != 0:
            self.skipTest("historical commits are unavailable in this checkout")

        for entry in self.registry["historical_files"]:
            actual = subprocess.run(
                ["git", "rev-parse", f'{entry["commit"]}:{entry["path"]}'],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            ).stdout.strip()
            self.assertEqual(actual, entry["git_blob"], entry["path"])


if __name__ == "__main__":
    unittest.main()
