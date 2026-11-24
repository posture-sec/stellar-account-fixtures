#!/usr/bin/env python3
"""Contract test for corpus/network-conformance.md (issue #55).

Verifies that corpus/network-conformance.md exists, contains zero em dashes,
documents network-to-root conformance across captured fixtures, explains validate.py
isolation checks, and ensures exact passphrase agreement with root documents.
"""

from __future__ import annotations

import json
import sys
import tomllib
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import validate  # noqa: E402

DOC_PATH = REPO_ROOT / "corpus" / "network-conformance.md"
FIXTURES_DIR = REPO_ROOT / "fixtures"
ROOT_PUBLIC = REPO_ROOT / "corpus" / "root-public.json"
ROOT_TESTNET = REPO_ROOT / "corpus" / "root-testnet.json"


class CorpusNetworkConformanceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(DOC_PATH.is_file(), f"{DOC_PATH} does not exist")
        self.content = DOC_PATH.read_text(encoding="utf-8")

    def test_zero_em_dashes(self) -> None:
        self.assertNotIn("\u2014", self.content)
        self.assertNotIn("\u2013", self.content)

    def test_explains_check_root_and_validator_enforcement(self) -> None:
        self.assertIn("validate.py:370", self.content)
        self.assertIn("check_root", self.content)
        self.assertIn("corpus/root-public.json:103", self.content)
        self.assertIn("corpus/root-testnet.json:107", self.content)

    def test_passphrases_match_root_files(self) -> None:
        with open(ROOT_PUBLIC, encoding="utf-8") as f:
            public_root = json.load(f)
        with open(ROOT_TESTNET, encoding="utf-8") as f:
            testnet_root = json.load(f)

        public_passphrase = public_root["network_passphrase"]
        testnet_passphrase = testnet_root["network_passphrase"]

        self.assertEqual(public_passphrase, "Public Global Stellar Network ; September 2015")
        self.assertEqual(testnet_passphrase, "Test SDF Network ; September 2015")
        self.assertIn(public_passphrase, self.content)
        self.assertIn(testnet_passphrase, self.content)

    def test_all_captured_fixtures_are_audited(self) -> None:
        lines = [
            line.strip() for line in self.content.splitlines() if line.strip().startswith("| `")
        ]
        table_fixtures = {line.split("|")[1].strip().strip("`"): line for line in lines}

        for fixture_dir in FIXTURES_DIR.iterdir():
            if not fixture_dir.is_dir():
                continue
            sidecar_path = fixture_dir / "fixture.toml"
            if not sidecar_path.is_file():
                continue
            with open(sidecar_path, "rb") as f:
                data = tomllib.load(f)
            if data.get("kind") != "captured":
                continue

            fixture_id = data["id"]
            self.assertIn(
                fixture_id,
                table_fixtures,
                f"Captured fixture {fixture_id} missing from network conformance table",
            )

            row = table_fixtures[fixture_id]
            parts = [p.strip() for p in row.split("|")[1:-1]]
            net = parts[1].strip("`")
            source_url = parts[2].strip("`")
            root_file = parts[3].strip("`")
            passphrase = parts[4].strip("`")

            self.assertEqual(net, data["network"])
            self.assertEqual(source_url, data["source_url"])
            self.assertEqual(root_file, f"corpus/root-{net}.json")
            self.assertEqual(passphrase, validate.NETWORKS[net][1])


if __name__ == "__main__":
    unittest.main()
