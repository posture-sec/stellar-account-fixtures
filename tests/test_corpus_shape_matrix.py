#!/usr/bin/env python3
"""Contract test for corpus/shape-matrix.md (issue #41).

Verifies that corpus/shape-matrix.md exists, contains zero em dashes, includes the
explicit convenience snapshot disclaimer, tabulates all nine fixtures against all 24
canonical shape labels, and that every matrix cell agrees with validate.py shapes_of.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import validate  # noqa: E402

CANONICAL_SHAPES: frozenset[str] = frozenset(
    {
        "no_signers",
        "single_signer",
        "multi_signer",
        "master_is_signer",
        "master_absent",
        "thresholds_zero",
        "thresholds_nonzero",
        "auth_required",
        "auth_revocable",
        "auth_immutable",
        "auth_clawback_enabled",
        "no_home_domain",
        "blank_home_domain",
        "has_home_domain",
        "has_inflation",
        "no_inflation",
        "has_data",
        "no_data",
        "sponsored",
        "not_sponsored",
        "sponsoring",
        "not_sponsoring",
        "no_balances",
        "many_balances",
    }
)

MATRIX_PATH = REPO_ROOT / "corpus" / "shape-matrix.md"
FIXTURES_DIR = REPO_ROOT / "fixtures"


class CorpusShapeMatrixTest(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(MATRIX_PATH.is_file(), f"{MATRIX_PATH} does not exist")
        self.content = MATRIX_PATH.read_text(encoding="utf-8")

    def test_zero_em_dashes(self) -> None:
        self.assertNotIn("\u2014", self.content)

    def test_header_convenience_view_disclaimer(self) -> None:
        self.assertIn("static convenience view", self.content)
        self.assertIn("authoritative source of truth", self.content)

    def test_shape_matrix_table_alignment_and_parity(self) -> None:
        lines = [
            line.strip() for line in self.content.splitlines() if line.strip().startswith("| `")
        ]
        self.assertEqual(len(lines), 9, "Expected exactly nine fixture rows in matrix")

        # Parse table header
        table_lines = [
            line.strip() for line in self.content.splitlines() if line.strip().startswith("|")
        ]
        header_line = table_lines[0]
        columns = [c.strip().strip("`") for c in header_line.split("|")[1:-1]]
        self.assertEqual(columns[0], "Fixture")
        labels = columns[1:]
        self.assertEqual(len(labels), 24)
        self.assertEqual(set(labels), CANONICAL_SHAPES)

        for line in lines:
            parts = [p.strip() for p in line.split("|")[1:-1]]
            fixture_id = parts[0].strip("`")
            cells = parts[1:]

            fixture_json = FIXTURES_DIR / fixture_id / "account.json"
            self.assertTrue(fixture_json.is_file(), f"Missing account.json for {fixture_id}")
            with open(fixture_json, encoding="utf-8") as f:
                account = json.load(f)
            derived = validate.shapes_of(account)

            for label, cell in zip(labels, cells, strict=True):
                self.assertIn(cell, ("Yes", "No"))
                if label in derived:
                    self.assertEqual(
                        cell,
                        "Yes",
                        f"Fixture {fixture_id} should have Yes for label {label}",
                    )
                else:
                    self.assertEqual(
                        cell,
                        "No",
                        f"Fixture {fixture_id} should have No for label {label}",
                    )


if __name__ == "__main__":
    unittest.main()
