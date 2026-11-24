#!/usr/bin/env python3
"""Contract test for issuer authorization flags derivation and isolation.

Audits validate.py's shapes_of derivation for auth_required, auth_revocable,
auth_immutable, and auth_clawback_enabled, ensuring that single-flag issuer
accounts emit exactly one auth label and verifying the co-occurrence constraint.
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


def make_issuer_account(flags: dict[str, bool]) -> dict:
    return {
        "account_id": "GD3ZN2T6QQMKLAGKKMWHHY4FITANVJBTREEJERHTWGWF2GSBPOSHGCLU",
        "signers": [
            {
                "key": "GD3ZN2T6QQMKLAGKKMWHHY4FITANVJBTREEJERHTWGWF2GSBPOSHGCLU",
                "weight": 1,
                "type": "ed25519_public_key",
            }
        ],
        "thresholds": {"low_threshold": 1, "med_threshold": 1, "high_threshold": 1},
        "flags": flags,
        "home_domain": None,
        "inflation_destination": None,
        "data": {},
        "num_sponsored": 0,
        "num_sponsoring": 0,
        "balances": [{"asset_type": "native", "balance": "100.0"}],
    }


class CorpusIssuerFlagsTest(unittest.TestCase):
    def test_zero_em_dashes(self) -> None:
        content = Path(__file__).read_text(encoding="utf-8")
        self.assertNotIn("\u2014", content)

    def test_auth_revocable_isolated(self) -> None:
        account = make_issuer_account(
            {
                "auth_required": False,
                "auth_revocable": True,
                "auth_immutable": False,
                "auth_clawback_enabled": False,
            }
        )
        shapes = validate.shapes_of(account)
        self.assertIn("auth_revocable", shapes)
        self.assertNotIn("auth_required", shapes)
        self.assertNotIn("auth_immutable", shapes)
        self.assertNotIn("auth_clawback_enabled", shapes)

    def test_auth_immutable_isolated(self) -> None:
        account = make_issuer_account(
            {
                "auth_required": False,
                "auth_revocable": False,
                "auth_immutable": True,
                "auth_clawback_enabled": False,
            }
        )
        shapes = validate.shapes_of(account)
        self.assertIn("auth_immutable", shapes)
        self.assertNotIn("auth_required", shapes)
        self.assertNotIn("auth_revocable", shapes)
        self.assertNotIn("auth_clawback_enabled", shapes)

    def test_auth_clawback_isolated(self) -> None:
        account = make_issuer_account(
            {
                "auth_required": False,
                "auth_revocable": False,
                "auth_immutable": False,
                "auth_clawback_enabled": True,
            }
        )
        shapes = validate.shapes_of(account)
        self.assertIn("auth_clawback_enabled", shapes)
        self.assertNotIn("auth_required", shapes)
        self.assertNotIn("auth_revocable", shapes)
        self.assertNotIn("auth_immutable", shapes)

    def test_co_occurrence_revocable_and_clawback(self) -> None:
        account = make_issuer_account(
            {
                "auth_required": True,
                "auth_revocable": True,
                "auth_immutable": False,
                "auth_clawback_enabled": True,
            }
        )
        shapes = validate.shapes_of(account)
        self.assertIn("auth_required", shapes)
        self.assertIn("auth_revocable", shapes)
        self.assertIn("auth_clawback_enabled", shapes)
        self.assertNotIn("auth_immutable", shapes)

    def test_shipped_issuer_fixture_isolates_auth_required(self) -> None:
        issuer_fixture = FIXTURES_DIR / "issuer-auth-required" / "account.json"
        self.assertTrue(issuer_fixture.is_file())
        with open(issuer_fixture, encoding="utf-8") as f:
            account = json.load(f)
        shapes = validate.shapes_of(account)
        self.assertIn("auth_required", shapes)
        self.assertNotIn("auth_revocable", shapes)
        self.assertNotIn("auth_immutable", shapes)
        self.assertNotIn("auth_clawback_enabled", shapes)


if __name__ == "__main__":
    unittest.main()
