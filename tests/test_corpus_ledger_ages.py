#!/usr/bin/env python3
"""Contract test for corpus/ledger-ages.md (issue #61).

Verifies that corpus/ledger-ages.md exists, contains zero em dashes, includes references
to validate.py:279 and SCHEMA.md:60, tabulates captures against root document heads,
and accurately reports the delta for fixtures/sponsored-trustlines.
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = REPO_ROOT / "corpus" / "ledger-ages.md"


class CorpusLedgerAgesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(DOC_PATH.is_file(), f"{DOC_PATH} does not exist")
        self.content = DOC_PATH.read_text(encoding="utf-8")

    def test_zero_em_dashes(self) -> None:
        self.assertNotIn("\u2014", self.content)
        self.assertNotIn("\u2013", self.content)

    def test_schema_and_validator_references(self) -> None:
        self.assertIn("SCHEMA.md:60", self.content)
        self.assertIn("validate.py:279", self.content)

    def test_sponsored_trustlines_lag_analysis(self) -> None:
        self.assertIn("65110665", self.content)
        self.assertIn("172015", self.content)
        self.assertIn("sponsored-trustlines", self.content)

    def test_tabulates_baseline_captures(self) -> None:
        expected = [
            "asset-heavy-exchange",
            "coordinator-data-entry",
            "default-plain",
            "domain-and-inflation",
            "issuer-auth-required",
            "multisig-custody",
            "sponsored-trustlines",
            "testnet-multisig",
            "whitespace-home-domain",
        ]
        for fixture_id in expected:
            self.assertIn(f"`{fixture_id}`", self.content)


if __name__ == "__main__":
    unittest.main()
