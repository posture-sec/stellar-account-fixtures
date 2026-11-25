#!/usr/bin/env python3
"""Contract test for revoked master key and no_signers shape derivations.

Audits validate.py's shapes_of derivation for master_absent and no_signers,
verifies that weight-0 master signers retain master_is_signer, and asserts
that all shipped fixtures reflect the documented coverage gaps.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import validate  # noqa: E402

FIXTURES_DIR = REPO_ROOT / "fixtures"


class CorpusRevokedMasterTest(unittest.TestCase):
    def test_zero_em_dashes(self) -> None:
        content = Path(__file__).read_text(encoding="utf-8")
        self.assertNotIn("\u2014", content)

    def test_empty_signers_emits_no_signers_and_master_absent(self) -> None:
        account_id = "GAAZI4TCR3TY5OJHCTJC2A4QSY6CJWJH5IAJTGKIN2ER7LBNVKOCCWN7"
        payload = {
            "account_id": account_id,
            "signers": [],
            "thresholds": {"low_threshold": 0, "med_threshold": 0, "high_threshold": 0},
            "flags": {},
            "home_domain": None,
            "inflation_destination": None,
            "data": {},
            "num_sponsored": 0,
            "num_sponsoring": 0,
            "balances": [{"asset_type": "native", "balance": "100.0"}],
        }
        shapes = validate.shapes_of(payload)
        self.assertIn("no_signers", shapes)
        self.assertIn("master_absent", shapes)
        self.assertNotIn("master_is_signer", shapes)

    def test_other_signer_without_master_emits_master_absent(self) -> None:
        account_id = "GAAZI4TCR3TY5OJHCTJC2A4QSY6CJWJH5IAJTGKIN2ER7LBNVKOCCWN7"
        other_key = "GB3AJUM7TJSIPSEZ2XZYKOAPIW6YH4I6L7S4JRHJK2QZ3HX2CYHCOV4N"
        payload = {
            "account_id": account_id,
            "signers": [{"key": other_key, "weight": 1, "type": "ed25519_public_key"}],
            "thresholds": {"low_threshold": 1, "med_threshold": 1, "high_threshold": 1},
            "flags": {},
            "home_domain": None,
            "inflation_destination": None,
            "data": {},
            "num_sponsored": 0,
            "num_sponsoring": 0,
            "balances": [{"asset_type": "native", "balance": "100.0"}],
        }
        shapes = validate.shapes_of(payload)
        self.assertIn("master_absent", shapes)
        self.assertNotIn("no_signers", shapes)
        self.assertNotIn("master_is_signer", shapes)
        self.assertIn("single_signer", shapes)

    def test_master_at_weight_zero_retains_master_is_signer(self) -> None:
        account_id = "GAAZI4TCR3TY5OJHCTJC2A4QSY6CJWJH5IAJTGKIN2ER7LBNVKOCCWN7"
        payload = {
            "account_id": account_id,
            "signers": [{"key": account_id, "weight": 0, "type": "ed25519_public_key"}],
            "thresholds": {"low_threshold": 1, "med_threshold": 1, "high_threshold": 1},
            "flags": {},
            "home_domain": None,
            "inflation_destination": None,
            "data": {},
            "num_sponsored": 0,
            "num_sponsoring": 0,
            "balances": [{"asset_type": "native", "balance": "100.0"}],
        }
        shapes = validate.shapes_of(payload)
        self.assertIn("master_is_signer", shapes)
        self.assertNotIn("master_absent", shapes)

    def test_shipped_fixtures_do_not_emit_uncovered_shapes(self) -> None:
        self.assertTrue(FIXTURES_DIR.is_dir())
        for fixture_dir in FIXTURES_DIR.iterdir():
            account_json = fixture_dir / "account.json"
            if not account_json.is_file():
                continue
            with open(account_json, encoding="utf-8") as f:
                account = json.load(f)
            shapes = validate.shapes_of(account)
            self.assertNotIn(
                "master_absent",
                shapes,
                f"Fixture {fixture_dir.name} unexpectedly emitted master_absent",
            )
            self.assertNotIn(
                "no_signers",
                shapes,
                f"Fixture {fixture_dir.name} unexpectedly emitted no_signers",
            )


if __name__ == "__main__":
    unittest.main()
