#!/usr/bin/env python3
"""Audit identity and network bindings across every shipped capture."""

from __future__ import annotations

import json
import sys
import tomllib
import unittest
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import validate  # noqa: E402

FIXTURES_DIR = REPO_ROOT / "fixtures"
EXPECTED_FIXTURE_COUNT = 12


def shipped_fixtures() -> list[Path]:
    fixtures = sorted(path for path in FIXTURES_DIR.iterdir() if path.is_dir())
    if len(fixtures) != EXPECTED_FIXTURE_COUNT:
        raise AssertionError(
            f"Expected {EXPECTED_FIXTURE_COUNT} shipped captures, found {len(fixtures)}"
        )
    return fixtures


def read_sidecar(directory: Path) -> dict[str, object]:
    with (directory / "fixture.toml").open("rb") as sidecar_file:
        return tomllib.load(sidecar_file)


class ValidateCorpusIdentityTest(unittest.TestCase):
    def test_sidecar_ids_match_fixture_directory_names(self) -> None:
        for directory in shipped_fixtures():
            with self.subTest(fixture=directory.name):
                sidecar = read_sidecar(directory)
                self.assertEqual(sidecar.get("id"), directory.name)

    def test_sidecar_account_ids_match_account_bytes(self) -> None:
        for directory in shipped_fixtures():
            with self.subTest(fixture=directory.name):
                sidecar = read_sidecar(directory)
                account = json.loads((directory / "account.json").read_text(encoding="utf-8"))
                self.assertIsInstance(account, dict)
                self.assertEqual(sidecar.get("account_id"), account.get("account_id"))

    def test_source_url_hosts_match_declared_network_endpoints(self) -> None:
        for directory in shipped_fixtures():
            with self.subTest(fixture=directory.name):
                sidecar = read_sidecar(directory)
                if sidecar.get("kind") == "synthetic":
                    self.assertNotIn("source_url", sidecar)
                    continue
                network = sidecar.get("network")
                self.assertIn(network, validate.NETWORKS)
                source_url = sidecar.get("source_url")
                self.assertIsInstance(source_url, str)
                endpoint, _ = validate.NETWORKS[network]
                self.assertEqual(
                    urlparse(source_url).hostname,
                    urlparse(endpoint).hostname,
                )


if __name__ == "__main__":
    unittest.main()
