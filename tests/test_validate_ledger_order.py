#!/usr/bin/env python3
"""Reject a sidecar ledger below the account's ``last_modified_ledger``.

``check_captured`` in ``validate.py`` already refused a ledger that was not a positive
integer. It did not compare that number with the height inside ``account.json``, so a
sidecar could claim a capture taken at ledger 90 of a state Horizon only reports from
ledger 100 onward. That is not a redundant check: the query height may be above
``last_modified_ledger``, never below it. The tests below drive both sides of the
comparison, the boundary that must still pass, and the nine shipped fixtures.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import validate  # noqa: E402

FIXTURE_ID = "plain"
WHERE = f"fixtures/{FIXTURE_ID}"

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"


def valid_account_id() -> str:
    body = bytes([validate.VERSION_ACCOUNT]) + bytes(range(32))
    raw = body + validate.crc16_xmodm(body).to_bytes(2, "little")
    bits = int.from_bytes(raw, "big")
    return "".join(ALPHABET[(bits >> (5 * (55 - index))) & 0x1F] for index in range(56))


def write_root_public(corpus_dir: Path) -> None:
    """Write the public root document and the sha256 sidecar validate.py requires."""
    document = json.dumps({"network_passphrase": validate.NETWORKS["public"][1]}) + "\n"
    path = corpus_dir / "root-public.json"
    path.write_text(document, encoding="utf-8")
    digest = hashlib.sha256(document.encode("utf-8")).hexdigest()
    (corpus_dir / "root-public.toml").write_text(
        'url = "https://horizon.stellar.org/"\n'
        'captured_at = "2026-11-25T00:00:00Z"\n'
        f'sha256 = "{digest}"\n',
        encoding="utf-8",
    )


class ValidateLedgerOrderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.stage = tempfile.TemporaryDirectory(prefix="ledger-order-test-")
        self.addCleanup(self.stage.cleanup)
        self.root = Path(self.stage.name)
        self.account_id = valid_account_id()
        self.account: dict[str, object] = {
            "account_id": self.account_id,
            "sequence": "1",
            "balances": [],
            "signers": [{"key": self.account_id, "weight": 1}],
            "thresholds": {"low_threshold": 0, "med_threshold": 0, "high_threshold": 0},
            "flags": {},
            "last_modified_ledger": 100,
        }
        self.fixture_dir = self.root / "fixtures" / FIXTURE_ID
        self.fixture_dir.mkdir(parents=True)
        self.body = (json.dumps(self.account, indent=2, sort_keys=True) + "\n").encode("utf-8")
        (self.fixture_dir / "account.json").write_bytes(self.body)
        (self.root / "corpus").mkdir()
        write_root_public(self.root / "corpus")

    def write_sidecar(self, ledger: int) -> Path:
        labels = "".join(f'  "{label}",\n' for label in sorted(validate.shapes_of(self.account)))
        manifest = self.fixture_dir / "fixture.toml"
        manifest.write_text(
            "schema_version = 1\n"
            f'id = "{FIXTURE_ID}"\n'
            'kind = "captured"\n'
            'scenario = "a capture used to pin the ledger ordering rule"\n'
            f'account_id = "{self.account_id}"\n'
            'network = "public"\n'
            'source_url = "https://horizon.stellar.org/accounts/' + self.account_id + '"\n'
            'captured_at = "2026-01-02T03:04:05Z"\n'
            f"ledger = {ledger}\n"
            'horizon_version = "30.0.0"\n'
            f'sha256 = "{hashlib.sha256(self.body).hexdigest()}"\n'
            "shape = [\n"
            f"{labels}"
            "]\n",
            encoding="utf-8",
        )
        return manifest

    def test_a_sidecar_below_last_modified_ledger_is_rejected(self) -> None:
        self.write_sidecar(99)

        problems, _ = validate.validate(self.root)

        expected = f"{WHERE}: sidecar ledger 99 predates last_modified_ledger 100"
        self.assertIn(expected, problems)
        self.assertEqual(len(problems), 1, problems)

    def test_the_message_names_both_ledgers(self) -> None:
        self.write_sidecar(7)

        problems, _ = validate.validate(self.root)

        self.assertTrue(problems)
        self.assertIn("sidecar ledger 7", problems[0])
        self.assertIn("last_modified_ledger 100", problems[0])

    def test_a_sidecar_at_last_modified_ledger_is_accepted(self) -> None:
        self.write_sidecar(100)

        problems, _ = validate.validate(self.root)

        self.assertEqual(problems, [], problems)

    def test_a_sidecar_above_last_modified_ledger_is_accepted(self) -> None:
        self.write_sidecar(101)

        problems, _ = validate.validate(self.root)

        self.assertEqual(problems, [], problems)

    def test_an_account_without_last_modified_ledger_is_unchanged(self) -> None:
        del self.account["last_modified_ledger"]
        self.body = (json.dumps(self.account, indent=2, sort_keys=True) + "\n").encode("utf-8")
        (self.fixture_dir / "account.json").write_bytes(self.body)
        self.write_sidecar(1)

        problems, _ = validate.validate(self.root)

        self.assertEqual(problems, [], problems)

    def test_the_shipped_corpus_still_validates(self) -> None:
        problems, _ = validate.validate(REPO_ROOT)

        self.assertEqual(problems, [], problems)


if __name__ == "__main__":
    unittest.main()
