from __future__ import annotations

import csv
import hashlib
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = REPO_ROOT / "analysis"
sys.path.insert(0, str(ANALYSIS_DIR))

import discover_data  # noqa: E402


class AnalysisPipelineIntegrityTests(unittest.TestCase):
    def test_inventory_uses_git_visible_files(self) -> None:
        paths = {
            path.relative_to(REPO_ROOT).as_posix()
            for path in discover_data.repository_visible_files()
            if path.is_file()
        }
        self.assertIn("analysis/config.yaml", paths)
        self.assertNotIn(
            "data/raw/dryad_z8w9ghx9f/Tangent_(Et)_vs_stress_curve (1).xlsx",
            paths,
        )
        self.assertFalse(any(path.startswith("sponge_compression") for path in paths))

    def test_output_manifest_matches_every_listed_artifact(self) -> None:
        output = ANALYSIS_DIR / "outputs"
        with (output / "output_manifest.csv").open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertGreaterEqual(len(rows), 40)
        self.assertIn("run_manifest.json", {row["relative_path"] for row in rows})
        for row in rows:
            path = output / row["relative_path"]
            self.assertTrue(path.is_file(), path)
            self.assertEqual(path.stat().st_size, int(row["size_bytes"]), path)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), row["sha256"], path)


if __name__ == "__main__":
    unittest.main()
