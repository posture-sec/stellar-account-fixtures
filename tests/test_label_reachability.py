#!/usr/bin/env python3
"""Contract test for shape label reachability qualification (issue #52).

Asserts that SCHEMA.md Section 5 explicitly qualifies no_balances as synthetic only,
and verifies that corpus/label-reachability.md documents the protocol constraints.
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "SCHEMA.md"
REACHABILITY_DOC = REPO_ROOT / "corpus" / "label-reachability.md"


class LabelReachabilityTest(unittest.TestCase):
    def test_schema_qualifies_no_balances_as_synthetic(self) -> None:
        self.assertTrue(SCHEMA_PATH.is_file(), "SCHEMA.md must exist")
        content = SCHEMA_PATH.read_text(encoding="utf-8")
        self.assertIn("## 5. The shape vocabulary", content)
        # Verify table row qualifies no_balances
        self.assertRegex(
            content,
            r"\|\s*`no_balances`\s*\|\s*`balances` is an empty list.*synthetic",
        )

    def test_reachability_doc_exists_and_explains_protocol_rule(self) -> None:
        self.assertTrue(REACHABILITY_DOC.is_file(), "corpus/label-reachability.md must exist")
        text = REACHABILITY_DOC.read_text(encoding="utf-8")
        self.assertIn("Base Reserve", text)
        self.assertIn("native", text)
        self.assertIn("synthetic", text)

    def test_zero_em_dashes(self) -> None:
        test_content = Path(__file__).read_text(encoding="utf-8")
        self.assertNotIn("\u2014", test_content)
        doc_content = REACHABILITY_DOC.read_text(encoding="utf-8")
        self.assertNotIn("\u2014", doc_content)


if __name__ == "__main__":
    unittest.main()
