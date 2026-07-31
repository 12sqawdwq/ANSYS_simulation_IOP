from __future__ import annotations

import importlib.util
import json
import math
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MACRO = REPO_ROOT / "models" / "apdl" / "post_contact_force_integrals.mac"
EXTRACTOR = REPO_ROOT / "src" / "postprocess" / "extract_contact_force_integrals.py"
POSTPROCESSOR = REPO_ROOT / "high_iop_mechanical_transfer_t1p25_c0p60" / "postprocess_interface_force_integrals.py"
SPEC = REPO_ROOT / "high_iop_mechanical_transfer_t1p25_c0p60" / "run_spec_interface_force_integrals.json"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class InterfaceForceIntegralTests(unittest.TestCase):
    def test_pressure_grid_and_source_partition_are_exact(self) -> None:
        spec = json.loads(SPEC.read_text(encoding="utf-8"))
        expected = [index * 2.5 for index in range(21)]
        self.assertEqual(spec["pressure_grid_mmhg"], expected)
        partition = []
        for values in spec["state_root_pressures_mmhg"].values():
            partition.extend(values)
        self.assertEqual(sorted(partition), expected)
        self.assertEqual(len(partition), len(set(partition)))
        self.assertEqual(spec["postprocessor"]["maximum_parallel_cases"], 1)

    def test_contact_etable_labels_do_not_collide_at_apdl_eight_character_limit(self) -> None:
        labels = []
        for line in MACRO.read_text(encoding="utf-8").splitlines():
            stripped = line.strip().lower()
            if stripped.startswith("etable,"):
                labels.append(stripped.split(",")[1])
        self.assertTrue(labels)
        self.assertTrue(all(len(label) <= 8 for label in labels))
        result_labels = [label for label in labels if label != "eras"]
        self.assertEqual(len(result_labels), len(set(result_labels)))

    def test_split_integral_files_parse_all_fields(self) -> None:
        module = load_module(EXTRACTOR, "extract_contact_force_integrals_test")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "contact_force_integrals_a.csv").write_text(
                ",".join(str(index + 1) for index in range(len(module.FIELDS_A))) + ",\n"
            )
            (root / "contact_force_integrals_b.csv").write_text(
                ",".join(str(index + 101) for index in range(len(module.FIELDS_B))) + ",\n"
            )
            values = module.parse_integrals(root)
        self.assertEqual(set(values), set(module.FIELDS_A + module.FIELDS_B))
        self.assertEqual(values["result_time"], 1.0)
        self.assertEqual(values["support_rf_z_n"], 113.0)

    def test_direct_rational_helpers(self) -> None:
        module = load_module(POSTPROCESSOR, "postprocess_interface_force_integrals_test")
        self.assertEqual(module.pressure_key(2.5), "2p5")
        self.assertTrue(math.isclose(module.rational(4.0, 0.05, 2.0), 10.0))
        fit = module.linear_fit([10.0, 20.0, 30.0], [2.0, 3.0, 4.0])
        self.assertTrue(math.isclose(fit["intercept"], 1.0))
        self.assertTrue(math.isclose(fit["slope_per_mmhg"], 0.1))


if __name__ == "__main__":
    unittest.main()
