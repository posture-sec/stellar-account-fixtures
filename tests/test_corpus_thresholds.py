#!/usr/bin/env python3
"""Contract test for corpus/thresholds.md (issue #44).

Verifies that corpus/thresholds.md exists, contains zero em dashes, explains derivation
logic in validate.py:162, documents exact threshold values matching account.json files,
and maps each fixture to its correct binary threshold label.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import validate  # noqa: E402

THRESHOLDS_PATH = REPO_ROOT / "corpus" / "thresholds.md"
FIXTURES_DIR = REPO_ROOT / "fixtures"


class CorpusThresholdsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(THRESHOLDS_PATH.is_file(), f"{THRESHOLDS_PATH} does not exist")
        self.content = THRESHOLDS_PATH.read_text(encoding="utf-8")

    def test_zero_em_dashes(self) -> None:
        self.assertNotIn("\u2014", self.content)

    def test_explains_derivation_logic(self) -> None:
        self.assertIn("validate.py:162", self.content)
        self.assertIn("thresholds_zero", self.content)
        self.assertIn("thresholds_nonzero", self.content)

    def test_thresholds_table_data(self) -> None:
        lines = [
            line.strip() for line in self.content.splitlines() if line.strip().startswith("| `")
        ]
        self.assertEqual(len(lines), 9, "Expected exactly nine fixture rows in thresholds table")

        for line in lines:
            parts = [p.strip() for p in line.split("|")[1:-1]]
            fixture_id = parts[0].strip("`")
            low = int(parts[1])
            med = int(parts[2])
            high = int(parts[3])
            triple = parts[4].strip("`")
            derived_label = parts[5].strip("`")

            self.assertEqual(triple, f"{low}/{med}/{high}")

            account_json = FIXTURES_DIR / fixture_id / "account.json"
            self.assertTrue(account_json.is_file())
            with open(account_json, encoding="utf-8") as f:
                account = json.load(f)

            thresholds = account.get("thresholds", {})
            self.assertEqual(low, thresholds.get("low_threshold", 0))
            self.assertEqual(med, thresholds.get("med_threshold", 0))
            self.assertEqual(high, thresholds.get("high_threshold", 0))

            shapes = validate.shapes_of(account)
            expected_label = "thresholds_nonzero" if (low or med or high) else "thresholds_zero"
            self.assertEqual(derived_label, expected_label)
            self.assertIn(derived_label, shapes)


if __name__ == "__main__":
    unittest.main()
