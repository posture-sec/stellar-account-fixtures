#!/usr/bin/env python3
"""source_url must name the account resource on the network the sidecar declares."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import validate  # noqa: E402

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
WHERE = "fixtures/plain"


def account_id() -> str:
    body = bytes([48]) + bytes(range(32))
    raw = body + validate.crc16_xmodm(body).to_bytes(2, "little")
    bits = int.from_bytes(raw, "big")
    return "".join(ALPHABET[(bits >> (5 * (55 - index))) & 0x1F] for index in range(56))


ACCOUNT = account_id()
PUBLIC_ENDPOINT = validate.NETWORKS["public"][0]
TESTNET_ENDPOINT = validate.NETWORKS["testnet"][0]


class SourceHostAlignment(unittest.TestCase):
    def setUp(self) -> None:
        stage = tempfile.TemporaryDirectory(prefix="source-host-test-")
        self.addCleanup(stage.cleanup)
        self.root = Path(stage.name)
        (self.root / "corpus").mkdir()
        for network, (_, passphrase) in validate.NETWORKS.items():
            (self.root / "corpus" / f"root-{network}.json").write_text(
                json.dumps({"network_passphrase": passphrase}) + "\n", encoding="utf-8"
            )
        self.account: dict[str, object] = {"account_id": ACCOUNT}
        self.body = (json.dumps(self.account, indent=2, sort_keys=True) + "\n").encode()
        labels = ", ".join(f'"{label}"' for label in sorted(validate.shapes_of(self.account)))
        self.template = (
            "# Test sidecar.\n"
            "schema_version = 1\n"
            'id = "plain"\n'
            'kind = "captured"\n'
            'scenario = "a plain account used to test the source host invariant"\n'
            f'account_id = "{ACCOUNT}"\n'
            'network = "{network}"\n'
            'source_url = "{source}"\n'
            'captured_at = "2026-11-02T00:00:00Z"\n'
            "ledger = 1\n"
            'horizon_version = "30.0.0"\n'
            f'sha256 = "{hashlib.sha256(self.body).hexdigest()}"\n'
            f"shape = [{labels}]\n"
        )
        self.directory = self.root / "fixtures" / "plain"
        self.directory.mkdir(parents=True)
        (self.directory / "account.json").write_bytes(self.body)
        self.write("public", f"{PUBLIC_ENDPOINT}/accounts/{ACCOUNT}")

    def write(self, network: str, source: str) -> None:
        (self.directory / "fixture.toml").write_text(
            self.template.format(network=network, source=source), encoding="utf-8"
        )

    def problems(self) -> list[str]:
        return validate.validate(self.root)[0]

    def expected(self, network: str, account: str = ACCOUNT) -> str:
        return f"{validate.NETWORKS[network][0]}/accounts/{account}"

    def assert_source_problem(self, source: str, network: str) -> None:
        self.assertEqual(
            self.problems(),
            [f"{WHERE}: source_url {source!r} should be {self.expected(network)!r}"],
        )

    def test_matching_public_url_is_clean(self) -> None:
        self.assertEqual(self.problems(), [])

    def test_matching_testnet_url_is_clean(self) -> None:
        self.write("testnet", self.expected("testnet"))
        self.assertEqual(self.problems(), [])

    def test_public_network_with_testnet_url_is_rejected(self) -> None:
        source = f"{TESTNET_ENDPOINT}/accounts/{ACCOUNT}"
        self.write("public", source)
        self.assert_source_problem(source, "public")

    def test_testnet_network_with_public_url_is_rejected(self) -> None:
        source = f"{PUBLIC_ENDPOINT}/accounts/{ACCOUNT}"
        self.write("testnet", source)
        self.assert_source_problem(source, "testnet")

    def test_an_external_host_is_rejected(self) -> None:
        source = f"https://example.invalid/accounts/{ACCOUNT}"
        self.write("public", source)
        self.assert_source_problem(source, "public")

    def test_a_different_account_path_is_rejected(self) -> None:
        source = f"{PUBLIC_ENDPOINT}/accounts/{'G' * 56}"
        self.write("public", source)
        self.assert_source_problem(source, "public")

    def test_shipped_fixtures_satisfy_the_invariant(self) -> None:
        fixtures = sorted(path for path in (REPO_ROOT / "fixtures").iterdir() if path.is_dir())
        self.assertEqual(len(fixtures), 12)
        for directory in fixtures:
            with self.subTest(fixture=directory.name):
                data = tomllib.loads((directory / "fixture.toml").read_text(encoding="utf-8"))
                if data.get("kind") == "synthetic":
                    self.assertNotIn("source_url", data)
                    continue
                expected = self.expected(data["network"], data["account_id"])
                self.assertEqual(data["source_url"], expected)


if __name__ == "__main__":
    unittest.main()
