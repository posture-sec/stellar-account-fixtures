#!/usr/bin/env python3
"""Contract test for fixtures/README.md (issue #37).

The index is prose about the fixtures, so it can drift from them. This test reads every
row back against the sidecar and the bytes: the directory exists, the network and ledger
match the sidecar, the label list equals both the sidecar and what the validator derives
from account.json, and the file does not disturb validation.
"""

from __future__ import annotations

import json
import re
import sys
import tomllib
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import validate  # noqa: E402

FIXTURES_DIR = REPO_ROOT / "fixtures"
INDEX_PATH = FIXTURES_DIR / "README.md"
ROW = re.compile(r"^\| \[`([a-z0-9-]+)`\]\(([^)]+)\) \|")


class FixturesIndexTest(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(INDEX_PATH.is_file(), f"{INDEX_PATH} does not exist")
        self.content = INDEX_PATH.read_text(encoding="utf-8")
        # Each row is (directory name, link target, remaining cells).
        self.rows: list[tuple[str, str, list[str]]] = []
        for line in self.content.splitlines():
            match = ROW.match(line)
            if match:
                cells = [cell.strip() for cell in line.split("|")[1:-1]]
                self.rows.append((match.group(1), match.group(2), cells[1:]))

    def test_zero_em_dashes(self) -> None:
        self.assertNotIn("\u2014", self.content)

    def test_one_row_per_fixture_directory(self) -> None:
        listed = sorted(name for name, _, _ in self.rows)
        on_disk = sorted(p.name for p in FIXTURES_DIR.iterdir() if p.is_dir())
        self.assertEqual(listed, on_disk)

    def test_fixture_count_in_the_text_matches_the_corpus(self) -> None:
        words = {10: "ten", 11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen"}
        count = len([p for p in FIXTURES_DIR.iterdir() if p.is_dir()])
        self.assertIn(f"## 1. The {words[count]} fixtures", self.content)
        self.assertIn(f"map of the {words[count]} fixtures", self.content)

    def test_each_row_links_to_its_directory(self) -> None:
        for name, target, _ in self.rows:
            self.assertEqual(target, f"{name}/")
            self.assertTrue((FIXTURES_DIR / target).is_dir(), target)

    def test_rows_match_sidecar_and_account_bytes(self) -> None:
        for name, _, cells in self.rows:
            network, ledger, labels, purpose = cells
            sidecar = tomllib.loads((FIXTURES_DIR / name / "fixture.toml").read_text("utf-8"))
            account = json.loads((FIXTURES_DIR / name / "account.json").read_text("utf-8"))

            self.assertEqual(network, sidecar["network"], name)
            if "ledger" in sidecar:
                self.assertEqual(int(ledger), sidecar["ledger"], name)
            else:
                # A synthetic fixture was not read from a ledger, so it has nothing to cite.
                self.assertEqual(sidecar["kind"], "synthetic", name)
                self.assertEqual(ledger, "none", name)

            listed = re.findall(r"`([a-z_]+)`", labels)
            self.assertEqual(sorted(listed), listed, f"{name}: labels are not in report order")
            self.assertEqual(set(listed), set(sidecar["shape"]), name)
            self.assertEqual(set(listed), validate.shapes_of(account), name)

            self.assertGreater(len(purpose), 0, f"{name}: purpose is empty")

    def test_links_to_the_schema_vocabulary_instead_of_repeating_it(self) -> None:
        self.assertIn("../SCHEMA.md#5-the-shape-vocabulary", self.content)
        schema = (REPO_ROOT / "SCHEMA.md").read_text(encoding="utf-8")
        self.assertIn("## 5. The shape vocabulary", schema)

    def test_relative_links_resolve(self) -> None:
        for target in re.findall(r"\]\((?!https?:)([^)#]+)(?:#[^)]*)?\)", self.content):
            self.assertTrue((FIXTURES_DIR / target).exists(), f"broken link: {target}")

    def test_index_file_does_not_disturb_validation(self) -> None:
        problems, _ = validate.validate(REPO_ROOT)
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
