#!/usr/bin/env python3
"""Contract test for corpus/signers.md (issue #43).

Verifies that corpus/signers.md exists, contains zero em dashes, clarifies that master_is_signer
evaluates key presence rather than nonzero authority, cites validate.py and SCHEMA.md:94,
and accurately tabulates signer counts, master weights, and threshold configurations.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

SIGNERS_PATH = REPO_ROOT / "corpus" / "signers.md"
FIXTURES_DIR = REPO_ROOT / "fixtures"


class CorpusSignersTest(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(SIGNERS_PATH.is_file(), f"{SIGNERS_PATH} does not exist")
        self.content = SIGNERS_PATH.read_text(encoding="utf-8")

    def test_zero_em_dashes(self) -> None:
        self.assertNotIn("\u2014", self.content)

    def test_cites_spec_and_validator(self) -> None:
        self.assertIn("SCHEMA.md:94", self.content)
        self.assertIn("validate.py:158", self.content)

    def test_presence_distinct_from_authority(self) -> None:
        self.assertIn("master_is_signer", self.content)
        self.assertIn("signing authority", self.content)
        self.assertIn("weight: 0", self.content)

    def test_signers_table_data(self) -> None:
        lines = [
            line.strip() for line in self.content.splitlines() if line.strip().startswith("| `")
        ]
        self.assertEqual(len(lines), 9, "Expected exactly nine fixture rows in signers table")

        for line in lines:
            parts = [p.strip() for p in line.split("|")[1:-1]]
            fixture_id = parts[0].strip("`")
            total_signers = int(parts[1])
            master_weight = int(parts[2])
            master_present = parts[3]
            thresh_str = parts[5]

            account_json = FIXTURES_DIR / fixture_id / "account.json"
            self.assertTrue(account_json.is_file())
            with open(account_json, encoding="utf-8") as f:
                account = json.load(f)

            signers = account.get("signers", [])
            self.assertEqual(total_signers, len(signers))

            aid = account.get("account_id") or account.get("id")
            master_entry = [s for s in signers if s.get("key") == aid]
            self.assertTrue(bool(master_entry))
            self.assertEqual(master_present, "Yes")
            self.assertEqual(master_weight, master_entry[0].get("weight"))

            thresholds = account.get("thresholds", {})
            low_val = thresholds.get("low_threshold", 0)
            med_val = thresholds.get("med_threshold", 0)
            high_val = thresholds.get("high_threshold", 0)
            self.assertEqual(thresh_str, f"{low_val}/{med_val}/{high_val}")


if __name__ == "__main__":
    unittest.main()
