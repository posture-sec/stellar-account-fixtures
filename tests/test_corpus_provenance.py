#!/usr/bin/env python3
"""Contract test for corpus/provenance.md (issue #42).

Verifies that corpus/provenance.md exists, contains zero em dashes, includes required
explanations of SHA-256 calculation against account.json bytes, and aggregates accurate
provenance metadata matching fixture.toml sidecars and on-disk SHA-256 digests.
"""

from __future__ import annotations

import hashlib
import sys
import tomllib
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

PROVENANCE_PATH = REPO_ROOT / "corpus" / "provenance.md"
FIXTURES_DIR = REPO_ROOT / "fixtures"


class CorpusProvenanceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(PROVENANCE_PATH.is_file(), f"{PROVENANCE_PATH} does not exist")
        self.content = PROVENANCE_PATH.read_text(encoding="utf-8")

    def test_zero_em_dashes(self) -> None:
        self.assertNotIn("\u2014", self.content)

    def test_explains_sha256_computation_and_contract(self) -> None:
        self.assertIn("SCHEMA.md:62", self.content)
        self.assertIn("validate.py:317", self.content)
        self.assertIn("sha256sum fixtures/*/account.json", self.content)

    def test_provenance_table_parity(self) -> None:
        lines = [
            line.strip() for line in self.content.splitlines() if line.strip().startswith("| `")
        ]
        self.assertEqual(len(lines), 9, "Expected exactly nine fixture rows in provenance table")

        for line in lines:
            parts = [p.strip().strip("`") for p in line.split("|")[1:-1]]
            self.assertEqual(len(parts), 7)
            (
                fixture_id,
                account_id,
                network,
                ledger_str,
                captured_at,
                horizon_ver,
                sha256_digest,
            ) = parts

            sidecar_path = FIXTURES_DIR / fixture_id / "fixture.toml"
            self.assertTrue(sidecar_path.is_file(), f"Missing sidecar {sidecar_path}")
            with open(sidecar_path, "rb") as f:
                sidecar = tomllib.load(f)

            self.assertEqual(account_id, sidecar["account_id"])
            self.assertEqual(network, sidecar["network"])
            self.assertEqual(int(ledger_str), sidecar["ledger"])
            self.assertEqual(captured_at, sidecar["captured_at"])
            self.assertEqual(horizon_ver, sidecar["horizon_version"])
            self.assertEqual(sha256_digest, sidecar["sha256"])

            # Verify sha256 against raw account.json bytes
            account_json = FIXTURES_DIR / fixture_id / "account.json"
            computed_digest = hashlib.sha256(account_json.read_bytes()).hexdigest()
            self.assertEqual(sha256_digest, computed_digest)


if __name__ == "__main__":
    unittest.main()
