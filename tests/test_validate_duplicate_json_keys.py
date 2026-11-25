#!/usr/bin/env python3
"""Document how account.json duplicate object keys are parsed by validate.py.

The validator hashes the original bytes but parses account.json with the standard
library's json.loads. JSON permits implementations to differ on duplicate names;
Python keeps the last value. This test pins that existing behavior and does not
claim that the validator enforces key uniqueness in account.json.
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


class ValidateDuplicateJsonKeysTest(unittest.TestCase):
    def test_account_json_duplicate_keys_use_last_value_for_shape_derivation(self) -> None:
        account_id = valid_account_id()
        account_bytes = (
            "{\n"
            f'  "account_id": "{account_id}",\n'
            '  "signers": [{"key": "' + account_id + '", "weight": 1}],\n'
            '  "thresholds": {"low_threshold": 0, "med_threshold": 0, "high_threshold": 0},\n'
            '  "flags": {},\n'
            '  "home_domain": "first.example",\n'
            '  "home_domain": "   "\n'
            "}\n"
        ).encode("utf-8")

        with tempfile.TemporaryDirectory(prefix="duplicate-json-keys-test-") as temp_dir:
            root = Path(temp_dir)
            fixture_dir = root / "fixtures" / "duplicate-home-domain"
            fixture_dir.mkdir(parents=True)
            (root / "corpus").mkdir()
            write_root_public(root / "corpus")

            account_path = fixture_dir / "account.json"
            account_path.write_bytes(account_bytes)
            parsed_account = json.loads(account_bytes)
            self.assertEqual(parsed_account["home_domain"], "   ")

            sidecar = (
                "schema_version = 1\n"
                'id = "duplicate-home-domain"\n'
                'kind = "captured"\n'
                'scenario = "duplicate home_domain keys document Python last-wins parsing"\n'
                f'account_id = "{account_id}"\n'
                'network = "public"\n'
                f'source_url = "{validate.NETWORKS["public"][0]}/accounts/{account_id}"\n'
                'captured_at = "2026-01-01T00:00:00Z"\n'
                "ledger = 1\n"
                'horizon_version = "30.0.0"\n'
                f'sha256 = "{hashlib.sha256(account_bytes).hexdigest()}"\n'
                "shape = [\n"
                + "\n".join(f'  "{shape}",' for shape in sorted(validate.shapes_of(parsed_account)))
                + "\n]\n"
            )
            (fixture_dir / "fixture.toml").write_text(sidecar, encoding="utf-8")

            problems, report = validate.validate(root, report=True)

        self.assertEqual(problems, [])
        self.assertEqual(len(report), 1)
        reported_shapes = set(report[0].split(": ", 1)[1].split(", "))
        self.assertIn("blank_home_domain", reported_shapes)
        self.assertNotIn("has_home_domain", reported_shapes)


if __name__ == "__main__":
    unittest.main()
