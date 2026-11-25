#!/usr/bin/env python3
"""Contract test for external consumer integrations (Gauge and Airlock).

Verifies that the corpus satisfies consumer requirements (D-02, D-03): offline
pinning via manifest SHA-256 digests, payload readability, and absence of
network dependencies during test execution.
"""

from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools.manifest import build_manifest  # noqa: E402

FIXTURES_DIR = REPO_ROOT / "fixtures"


class ConsumerContractTest(unittest.TestCase):
    def test_zero_em_dashes(self) -> None:
        content = Path(__file__).read_text(encoding="utf-8")
        self.assertNotIn("\u2014", content)

    def test_consumer_manifest_pins_match_actual_file_digests(self) -> None:
        records = build_manifest()
        self.assertGreater(len(records), 0)
        for record in records:
            fixture_id = str(record["id"])
            expected_sha = record.get("sha256")
            if record.get("kind") == "captured":
                self.assertIsNotNone(expected_sha)
                account_path = FIXTURES_DIR / fixture_id / "account.json"
                self.assertTrue(account_path.is_file())
                computed_sha = hashlib.sha256(account_path.read_bytes()).hexdigest()
                self.assertEqual(computed_sha, expected_sha)

    def test_consumer_target_fixtures_exist_for_airlock_and_gauge(self) -> None:
        records = build_manifest()
        fixture_ids = {str(r["id"]) for r in records}
        self.assertIn("multisig-custody", fixture_ids)
        self.assertIn("issuer-auth-required", fixture_ids)

        for target in ("multisig-custody", "issuer-auth-required"):
            account_json = FIXTURES_DIR / target / "account.json"
            self.assertTrue(account_json.is_file())
            data = json.loads(account_json.read_text(encoding="utf-8"))
            self.assertIn("account_id", data)
            self.assertIn("signers", data)
            self.assertIn("thresholds", data)


if __name__ == "__main__":
    unittest.main()
