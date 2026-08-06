from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_ROOT = REPO_ROOT / "high_iop_mechanical_transfer_t1p25_c0p60"
DOCS = EXPERIMENT_ROOT / "docs"
RECORD = DOCS / "EXPERIMENT_RECORD.md"
MANIFEST = DOCS / "SOURCE_DOCUMENT_MANIFEST.json"


class HighIopDocumentArchiveTests(unittest.TestCase):
    def test_all_fourteen_source_documents_have_hash_verified_sections(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        record = RECORD.read_text(encoding="utf-8")
        self.assertEqual(manifest["source_count"], 14)
        self.assertEqual(len(manifest["sources"]), 14)
        for source in manifest["sources"]:
            filename = Path(source["source_path"]).name
            begin = f'<!-- BEGIN-SOURCE {filename} {source["merged_section_sha256"]} -->\n'
            end = f"<!-- END-SOURCE {filename} -->"
            self.assertEqual(record.count(begin), 1, filename)
            self.assertEqual(record.count(end), 1, filename)
            section = record.split(begin, 1)[1].split(end, 1)[0]
            actual = hashlib.sha256(section.encode("utf-8")).hexdigest()
            self.assertEqual(actual, source["merged_section_sha256"], filename)
            self.assertEqual(len(source["source_sha256"]), 64)
            self.assertEqual(len(source["source_git_blob"]), 40)
            self.assertGreater(source["source_line_count"], 0)

    def test_current_document_set_and_navigation_exist(self) -> None:
        required = (
            EXPERIMENT_ROOT / "README.md",
            DOCS / "MAIN_CONCLUSIONS.md",
            DOCS / "SYSTEM_ENGINEERING.md",
            DOCS / "SCRIPT_INDEX.md",
            DOCS / "CHANGELOG.md",
            DOCS / "intermediate" / "README.md",
            DOCS / "intermediate" / "MECHANICAL_TRANSFER_PATH.md",
        )
        for path in required:
            self.assertTrue(path.is_file(), path)
            self.assertGreater(path.stat().st_size, 100, path)


if __name__ == "__main__":
    unittest.main()
