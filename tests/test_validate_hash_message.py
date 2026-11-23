#!/usr/bin/env python3
"""Pin the 12-character hex digest prefix formatting in sha256 mismatch messages."""

from __future__ import annotations

import hashlib
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import validate  # noqa: E402

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
WHERE = "fixtures/plain"


def make_account_id() -> str:
    body = bytes([48]) + bytes(range(32))
    raw = body + validate.crc16_xmodm(body).to_bytes(2, "little")
    bits = int.from_bytes(raw, "big")
    return "".join(ALPHABET[(bits >> (5 * (55 - index))) & 0x1F] for index in range(56))


class ValidateHashMessageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.stage = tempfile.TemporaryDirectory(prefix="hash-message-test-")
        self.addCleanup(self.stage.cleanup)
        self.root = Path(self.stage.name)
        (self.root / "corpus").mkdir()
        (self.root / "corpus" / "root-public.json").write_text(
            json.dumps({"network_passphrase": validate.NETWORKS["public"][1]}) + "\n",
            encoding="utf-8",
        )
        self.account_id = make_account_id()
        self.account: dict[str, object] = {
            "account_id": self.account_id,
            "sequence": "100",
            "balances": [],
            "signers": [{"key": self.account_id, "weight": 1}],
            "thresholds": {"low_threshold": 0, "med_threshold": 0, "high_threshold": 0},
            "flags": {},
        }
        self.body_bytes = (json.dumps(self.account, indent=2, sort_keys=True) + "\n").encode()
        self.real_digest = hashlib.sha256(self.body_bytes).hexdigest()

        self.directory = self.root / "fixtures" / "plain"
        self.directory.mkdir(parents=True)
        self.body_file = self.directory / "account.json"
        self.body_file.write_bytes(self.body_bytes)

        self.sidecar = {
            "schema_version": 1,
            "id": "plain",
            "kind": "captured",
            "scenario": "a plain account used to test sha256 mismatch message format",
            "account_id": self.account_id,
            "network": "public",
            "source_url": f"https://horizon.stellar.org/accounts/{self.account_id}",
            "captured_at": "2026-01-01T00:00:00Z",
            "ledger": 123456,
            "horizon_version": "30.0.0",
            "sha256": self.real_digest,
            "shape": sorted(validate.shapes_of(self.account)),
        }

    def test_single_byte_mutation_reports_12_character_hex_prefix(self) -> None:
        # Introduce a single-byte mutation to account.json
        mutated_bytes = self.body_bytes[:-2] + b"x\n"
        self.body_file.write_bytes(mutated_bytes)
        mutated_digest = hashlib.sha256(mutated_bytes).hexdigest()
        self.assertNotEqual(mutated_digest, self.real_digest)

        corpus = validate.Corpus(self.root)
        validate.check_captured(
            corpus,
            WHERE,
            self.sidecar,
            self.body_file,
            self.account,
        )

        self.assertEqual(len(corpus.problems), 1)
        problem = corpus.problems[0]

        # The message pins the 12-character hex prefix followed by an ellipsis
        prefix = mutated_digest[:12]
        self.assertIn(f"{prefix}...", problem)

        pattern = re.compile(r"(?:bytes say|hashes to) [0-9a-f]{12}\.\.\.")
        self.assertRegex(problem, pattern)

        # Requirement check: matches re.compile(r'hashes to [0-9a-f]{12}\.\.\.') format
        hex_pattern = re.compile(r"[0-9a-f]{12}\.\.\.")
        self.assertRegex(problem, hex_pattern)


if __name__ == "__main__":
    unittest.main()
