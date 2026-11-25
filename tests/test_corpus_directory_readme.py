#!/usr/bin/env python3
"""Contract test for corpus/README.md (issue #38).

The guide states which passphrase belongs to which network root file and where the
validator enforces it. This test reads those statements back against the root documents
and against validate.py and tools/capture.py, so the table cannot drift from the files.
"""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools"))

import capture  # noqa: E402

import validate  # noqa: E402

CORPUS_DIR = REPO_ROOT / "corpus"
GUIDE_PATH = CORPUS_DIR / "README.md"
EM_DASH = chr(0x2014)
ROW = re.compile(r"^\| `(public|testnet)` \| \[`(root-[a-z]+\.json)`\]\(([^)]+)\) \| ")


class CorpusDirectoryReadmeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(GUIDE_PATH.is_file(), f"{GUIDE_PATH} does not exist")
        self.content = GUIDE_PATH.read_text(encoding="utf-8")
        self.rows = [
            (match, [cell.strip() for cell in line.split("|")[1:-1]])
            for line in self.content.splitlines()
            if (match := ROW.match(line))
        ]

    def test_zero_em_dashes(self) -> None:
        self.assertNotIn(EM_DASH, self.content)

    def test_one_row_per_validator_network(self) -> None:
        self.assertEqual(sorted(m.group(1) for m, _ in self.rows), sorted(validate.NETWORKS))

    def test_each_row_matches_the_root_document_and_the_validator(self) -> None:
        for match, cells in self.rows:
            network, filename, target = match.groups()
            self.assertEqual(filename, f"root-{network}.json")
            self.assertEqual(target, filename)

            path = CORPUS_DIR / filename
            self.assertTrue(path.is_file(), filename)
            root = json.loads(path.read_text(encoding="utf-8"))

            base_url, passphrase = validate.NETWORKS[network]
            self.assertEqual(cells[2].strip("`"), base_url)
            self.assertEqual(cells[3].strip("`"), passphrase)
            self.assertEqual(root["network_passphrase"], passphrase)

            # The cited line really is the passphrase line of the root file.
            cited_match = re.search(r"line (\d+)", cells[4])
            self.assertIsNotNone(cited_match, cells[4])
            cited = int(cited_match.group(1)) if cited_match else 0
            line = path.read_text(encoding="utf-8").splitlines()[cited - 1]
            self.assertIn(passphrase, line, f"{filename} line {cited}")

    def test_capture_tool_agrees_with_the_validator_on_each_network(self) -> None:
        self.assertEqual(sorted(capture.ENDPOINTS), sorted(validate.NETWORKS))
        self.assertEqual(sorted(capture.PASSPHRASES), sorted(validate.NETWORKS))
        for network, (base_url, passphrase) in validate.NETWORKS.items():
            self.assertEqual(capture.ENDPOINTS[network], base_url)
            self.assertEqual(capture.PASSPHRASES[network], passphrase)

    def test_names_the_enforcement_points_that_exist(self) -> None:
        self.assertIn("SCHEMA.md", self.content)
        self.assertIn("check_root", self.content)
        self.assertIn("NETWORKS", self.content)
        self.assertTrue(callable(validate.check_root))
        schema = (REPO_ROOT / "SCHEMA.md").read_text(encoding="utf-8")
        self.assertIn("## 6. Root documents", schema)

    def test_documents_the_four_conditions_the_validator_reports(self) -> None:
        for phrase in (
            "the file is missing",
            "the file is not JSON",
            "the JSON is not an object",
            "the passphrase does not match",
        ):
            self.assertIn(phrase, self.content)
        source = (REPO_ROOT / "validate.py").read_text(encoding="utf-8")
        self.assertIn("MISSING_ROOT", source)
        for message in ("not JSON", "not a JSON object", "is not the {network} passphrase"):
            self.assertIn(message, source)

    def test_third_network_steps_name_every_place_a_network_is_defined(self) -> None:
        for name in ("NETWORKS", "ENDPOINTS", "PASSPHRASES", "tools/capture.py"):
            self.assertIn(name, self.content)

    def test_relative_links_resolve(self) -> None:
        for target in re.findall(r"\]\((?!https?:)([^)#]+)(?:#[^)]*)?\)", self.content):
            self.assertTrue((CORPUS_DIR / target).exists(), f"broken link: {target}")


if __name__ == "__main__":
    unittest.main()
