#!/usr/bin/env python3
"""Confirm every sidecar account id decodes at version 48 (ed25519 public key)."""

from __future__ import annotations

import sys
import tomllib
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import validate  # noqa: E402

FIXTURES_DIR = REPO_ROOT / "fixtures"


class ValidateAccountIdVersionTest(unittest.TestCase):
    def test_all_shipped_sidecars_decode_as_version_48_public_keys(self) -> None:
        fixture_dirs = sorted(p for p in FIXTURES_DIR.iterdir() if p.is_dir())
        self.assertEqual(len(fixture_dirs), 9, "Expected exactly nine production fixtures")

        for directory in fixture_dirs:
            sidecar_file = directory / "fixture.toml"
            self.assertTrue(
                sidecar_file.is_file(),
                f"Missing fixture.toml in {directory}",
            )

            with open(sidecar_file, "rb") as f:
                data = tomllib.load(f)

            account_id = data.get("account_id")
            self.assertIsInstance(
                account_id,
                str,
                f"Sidecar {directory.name} missing string account_id",
            )
            self.assertEqual(
                len(account_id),
                56,
                f"Sidecar {directory.name} account_id must be 56 characters",
            )

            version = validate.strkey_version(account_id)
            self.assertEqual(
                version,
                48,
                f"Sidecar {directory.name} account_id {account_id} must decode to version 48",
            )

            self.assertTrue(
                validate.is_valid_account_id(account_id),
                f"Sidecar {directory.name} account_id {account_id} failed checksum validation",
            )


if __name__ == "__main__":
    unittest.main()
