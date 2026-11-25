#!/usr/bin/env python3
"""Contract test for corpus/balances.md (issue #45).

Every number in the balance table is recomputed from the `balances` array of the matching
account.json, so a re-capture that changes a count fails here until the document is updated.
"""

from __future__ import annotations

import json
import re
import sys
import unittest
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import validate  # noqa: E402

DOC_PATH = REPO_ROOT / "corpus" / "balances.md"
FIXTURES_DIR = REPO_ROOT / "fixtures"
EM_DASH = chr(0x2014)
ASSET_TYPES = {"native", "credit_alphanum4", "credit_alphanum12"}
ROW = re.compile(r"^\| `([a-z0-9-]+)` \|")


def balances_of(fixture_id: str) -> list[dict[str, object]]:
    path = FIXTURES_DIR / fixture_id / "account.json"
    account = json.loads(path.read_text(encoding="utf-8"))
    return list(account["balances"])


class CorpusBalancesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(DOC_PATH.is_file(), f"{DOC_PATH} does not exist")
        self.content = DOC_PATH.read_text(encoding="utf-8")
        # The balance table has nine columns; the asset-type table below it has four.
        self.rows = {
            match.group(1): cells
            for line in self.content.splitlines()
            if (match := ROW.match(line))
            and len(cells := [cell.strip() for cell in line.split("|")[1:-1]]) == 9
        }

    def test_zero_em_dashes(self) -> None:
        self.assertNotIn(EM_DASH, self.content)

    def test_one_row_per_fixture(self) -> None:
        on_disk = {p.name for p in FIXTURES_DIR.iterdir() if p.is_dir()}
        self.assertEqual(set(self.rows), on_disk)

    def test_row_counts_match_the_balances_arrays(self) -> None:
        for fixture_id, cells in self.rows.items():
            balances = balances_of(fixture_id)
            kinds = Counter(str(b["asset_type"]) for b in balances)
            issuers = {b["asset_issuer"] for b in balances if "asset_issuer" in b}

            self.assertEqual(int(cells[2]), len(balances), fixture_id)
            self.assertEqual(int(cells[3]), kinds["native"], fixture_id)
            self.assertEqual(int(cells[4]), kinds["credit_alphanum4"], fixture_id)
            self.assertEqual(int(cells[5]), kinds["credit_alphanum12"], fixture_id)
            self.assertEqual(int(cells[6]), len(balances) - kinds["native"], fixture_id)
            self.assertEqual(int(cells[7]), len(issuers), fixture_id)

    def test_trustlines_are_total_minus_native(self) -> None:
        for fixture_id, cells in self.rows.items():
            self.assertEqual(int(cells[6]), int(cells[2]) - int(cells[3]), fixture_id)

    def test_many_balances_column_matches_the_validator(self) -> None:
        for fixture_id, cells in self.rows.items():
            account = json.loads((FIXTURES_DIR / fixture_id / "account.json").read_text("utf-8"))
            derived = "many_balances" in validate.shapes_of(account)
            self.assertEqual(cells[8] == "yes", derived, fixture_id)
            self.assertIn(cells[8], {"yes", "no"})

    def test_totals_row(self) -> None:
        total = next(line for line in self.content.splitlines() if line.startswith("| **All "))
        cells = [cell.strip().strip("*") for cell in total.split("|")[1:-1]]
        every = [b for fixture_id in self.rows for b in balances_of(fixture_id)]
        kinds = Counter(str(b["asset_type"]) for b in every)
        self.assertEqual(int(cells[2]), len(every))
        self.assertEqual(int(cells[3]), kinds["native"])
        self.assertEqual(int(cells[4]), kinds["credit_alphanum4"])
        self.assertEqual(int(cells[5]), kinds["credit_alphanum12"])
        self.assertEqual(int(cells[6]), len(every) - kinds["native"])
        flagged = sum(1 for row in self.rows.values() if row[8] == "yes")
        self.assertEqual(cells[8], f"{flagged} of {len(self.rows)}")

    def test_the_boundary_fixture_holds_exactly_ten_balances(self) -> None:
        self.assertEqual(len(balances_of("ten-balances-boundary")), 10)
        self.assertEqual(self.rows["ten-balances-boundary"][8], "yes")
        self.assertIn("`ten-balances-boundary` (exactly 10)", self.content)
        # The document says nothing sits at 9, so check that is still true.
        sizes = [len(balances_of(fixture_id)) for fixture_id in self.rows]
        self.assertNotIn(9, sizes)
        self.assertNotIn(11, sizes)

    def test_only_the_three_documented_asset_types_appear(self) -> None:
        seen = {str(b["asset_type"]) for f in self.rows for b in balances_of(f)}
        self.assertEqual(seen, ASSET_TYPES)
        for name in ASSET_TYPES:
            self.assertIn(f"`{name}`", self.content)

    def test_asset_type_table_counts(self) -> None:
        every = [b for fixture_id in self.rows for b in balances_of(fixture_id)]
        kinds = Counter(str(b["asset_type"]) for b in every)
        for name, count in kinds.items():
            pattern = rf"^\| `{name}` \|.*\| {count} \|"
            self.assertRegex(self.content, re.compile(pattern, re.MULTILINE), name)

    def test_native_entry_is_single_last_and_has_no_issuer_keys(self) -> None:
        for fixture_id in self.rows:
            balances = balances_of(fixture_id)
            natives = [b for b in balances if b["asset_type"] == "native"]
            self.assertEqual(len(natives), 1, fixture_id)
            self.assertIs(balances[-1], natives[0], fixture_id)
            for key in ("asset_code", "asset_issuer", "limit"):
                self.assertNotIn(key, natives[0], f"{fixture_id}: native entry has {key}")
            for b in balances:
                if b["asset_type"] != "native":
                    for key in ("asset_code", "asset_issuer", "limit"):
                        self.assertIn(key, b, fixture_id)

    def test_boundary_documents_the_rule_the_validator_applies(self) -> None:
        self.assertIn("many_balances", self.content)
        self.assertIn("10 or more entries", self.content)
        schema = (REPO_ROOT / "SCHEMA.md").read_text(encoding="utf-8")
        self.assertIn("| `many_balances` | `balances` has 10 or more entries |", schema)
        with_labels = [validate.shapes_of({"balances": [{}] * n}) for n in (0, 1, 9, 10, 11)]
        flags = ["many_balances" in labels for labels in with_labels]
        self.assertEqual(flags, [False, False, False, True, True])
        self.assertIn("no_balances", with_labels[0])

    def test_relative_links_resolve(self) -> None:
        for target in re.findall(r"\]\((?!https?:)([^)#]+)(?:#[^)]*)?\)", self.content):
            self.assertTrue((DOC_PATH.parent / target).exists(), f"broken link: {target}")


if __name__ == "__main__":
    unittest.main()
