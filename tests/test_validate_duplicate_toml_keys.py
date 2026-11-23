#!/usr/bin/env python3
"""Pin how a duplicate key in ``fixture.toml`` reaches the caller.

TOML forbids the same key twice in one table, so ``tomllib.loads`` raises
``TOMLDecodeError`` rather than keeping one of the two values the way a JSON parser
would. ``load_manifest`` catches that at the parse boundary and records one structured
problem, ``sidecar is not valid TOML: ...``, naming the fixture directory. These tests
hold that path to its shape: a duplicate key is a report, not a traceback, and the
message names the directory and the duplicated key.
"""

from __future__ import annotations

import json
import sys
import tempfile
import tomllib
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


def sidecar_text(account_id: str, shape: list[str]) -> str:
    labels = "".join(f'  "{label}",\n' for label in shape)
    return (
        "schema_version = 1\n"
        f'id = "{FIXTURE_ID}"\n'
        'kind = "synthetic"\n'
        'scenario = "synthetic: two network keys in one table"\n'
        f'account_id = "{account_id}"\n'
        'network = "public"\n'
        "shape = [\n"
        f"{labels}"
        "]\n"
    )


class ValidateDuplicateTomlKeysTest(unittest.TestCase):
    def setUp(self) -> None:
        self.stage = tempfile.TemporaryDirectory(prefix="duplicate-toml-keys-test-")
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
        }
        self.fixture_dir = self.root / "fixtures" / FIXTURE_ID
        self.fixture_dir.mkdir(parents=True)
        (self.fixture_dir / "account.json").write_bytes(
            (json.dumps(self.account, indent=2, sort_keys=True) + "\n").encode("utf-8")
        )
        self.manifest = self.fixture_dir / "fixture.toml"
        self.manifest.write_text(
            sidecar_text(self.account_id, sorted(validate.shapes_of(self.account))),
            encoding="utf-8",
        )

    def test_tomllib_refuses_the_duplicate_the_fixture_carries(self) -> None:
        duplicated = self.manifest.read_text(encoding="utf-8").replace(
            'network = "public"\n', 'network = "public"\nnetwork = "testnet"\n', 1
        )

        with self.assertRaises(tomllib.TOMLDecodeError):
            tomllib.loads(duplicated)

    def test_load_manifest_reports_the_duplicate_as_a_structured_problem(self) -> None:
        self.manifest.write_text(
            self.manifest.read_text(encoding="utf-8").replace(
                'network = "public"\n', 'network = "public"\nnetwork = "testnet"\n', 1
            ),
            encoding="utf-8",
        )
        corpus = validate.Corpus(self.root)

        loaded = validate.load_manifest(corpus, self.manifest, WHERE)

        self.assertIsNone(loaded)
        self.assertEqual(len(corpus.problems), 1, corpus.problems)
        problem = corpus.problems[0]
        self.assertTrue(problem.startswith(f"{WHERE}: "), problem)
        self.assertIn("sidecar is not valid TOML", problem)
        self.assertIn("Cannot overwrite a value", problem)

    def test_a_full_validation_reports_instead_of_raising(self) -> None:
        self.manifest.write_text(
            self.manifest.read_text(encoding="utf-8").replace(
                'network = "public"\n', 'network = "public"\nnetwork = "public"\n', 1
            ),
            encoding="utf-8",
        )
        (self.root / "corpus").mkdir()
        (self.root / "corpus" / "root-public.json").write_text(
            json.dumps({"network_passphrase": validate.NETWORKS["public"][1]}) + "\n",
            encoding="utf-8",
        )

        problems, _ = validate.validate(self.root)

        self.assertTrue(
            any("sidecar is not valid TOML" in problem for problem in problems), problems
        )
        self.assertFalse(any("Traceback" in problem for problem in problems), problems)


if __name__ == "__main__":
    unittest.main()
