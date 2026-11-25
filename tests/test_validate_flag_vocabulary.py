#!/usr/bin/env python3
"""Auth flags shape derivation in validate.py must adhere strictly to SCHEMA.md."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import validate  # noqa: E402


class ValidateFlagVocabularyTest(unittest.TestCase):
    def test_auth_flags_constant_defined(self) -> None:
        self.assertTrue(hasattr(validate, "AUTH_FLAGS"))
        self.assertEqual(
            validate.AUTH_FLAGS,
            (
                "auth_required",
                "auth_revocable",
                "auth_immutable",
                "auth_clawback_enabled",
            ),
        )

    def test_canonical_auth_flags_are_derived(self) -> None:
        account = {
            "account_id": "G" + "A" * 55,
            "flags": {
                "auth_required": True,
                "auth_revocable": True,
                "auth_immutable": True,
                "auth_clawback_enabled": True,
            },
        }
        derived = validate.shapes_of(account)
        for flag in validate.AUTH_FLAGS:
            self.assertIn(flag, derived)

    def test_arbitrary_or_deprecated_flags_are_ignored(self) -> None:
        account = {
            "account_id": "G" + "A" * 55,
            "flags": {
                "auth_required": True,
                "partner_reserve": True,
                "clawback_enabled_deprecated": True,
                "custom_flag": 1,
                "arbitrary_token": "yes",
            },
        }
        derived = validate.shapes_of(account)
        self.assertIn("auth_required", derived)
        self.assertNotIn("partner_reserve", derived)
        self.assertNotIn("clawback_enabled_deprecated", derived)
        self.assertNotIn("custom_flag", derived)
        self.assertNotIn("arbitrary_token", derived)

    def test_falsy_canonical_flags_are_not_derived(self) -> None:
        account = {
            "account_id": "G" + "A" * 55,
            "flags": {
                "auth_required": False,
                "auth_revocable": 0,
                "auth_immutable": None,
            },
        }
        derived = validate.shapes_of(account)
        self.assertNotIn("auth_required", derived)
        self.assertNotIn("auth_revocable", derived)
        self.assertNotIn("auth_immutable", derived)


if __name__ == "__main__":
    unittest.main()
