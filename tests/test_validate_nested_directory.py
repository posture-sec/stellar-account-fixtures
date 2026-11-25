#!/usr/bin/env python3
"""Pin that a nested directory inside a fixture is ignored by the layout check.

``validate_fixture`` in ``validate.py`` builds its set of observed names with
``{p.name for p in directory.iterdir() if p.is_file()}``, so only files count and a
directory of any depth is invisible to it. That is the behavior this module pins, in
both directions: a nested directory carrying junk is not reported as an unexpected
file, and a real extra file beside ``account.json`` still is. Pinning the blind spot
rather than silently relying on it means a later change to that set is caught here.
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
    """A G... address whose version byte and CRC16 both verify."""
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
        'scenario = "synthetic: a nested directory must not count as a file"\n'
        f'account_id = "{account_id}"\n'
        'network = "public"\n'
        "shape = [\n"
        f"{labels}"
        "]\n"
    )


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


class ValidateNestedDirectoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.stage = tempfile.TemporaryDirectory(prefix="nested-directory-test-")
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
        (self.fixture_dir / "fixture.toml").write_text(
            sidecar_text(self.account_id, sorted(validate.shapes_of(self.account))),
            encoding="utf-8",
        )
        (self.root / "corpus").mkdir()
        write_root_public(self.root / "corpus")

    def test_nested_directory_is_not_reported_as_an_unexpected_file(self) -> None:
        nested = self.fixture_dir / "backup" / "2026" / "older"
        nested.mkdir(parents=True)
        (nested / "account.json.bak").write_text("{}\n", encoding="utf-8")
        (self.fixture_dir / "__pycache__").mkdir()
        (self.fixture_dir / "__pycache__" / "validate.cpython-311.pyc").write_bytes(b"\x00")

        problems, _ = validate.validate(self.root)

        self.assertEqual(problems, [], f"a nested directory must be invisible: {problems}")
        self.assertFalse(
            any("unexpected file" in problem for problem in problems),
            f"a nested directory was reported as an unexpected file: {problems}",
        )

    def test_validate_fixture_sees_only_files_beside_the_two_allowed_ones(self) -> None:
        (self.fixture_dir / "notes").mkdir()
        corpus = validate.Corpus(self.root, report=False)

        validate.validate_fixture(corpus, self.fixture_dir, {})

        self.assertEqual(corpus.problems, [], f"unexpected problems: {corpus.problems}")

    def test_a_real_extra_file_is_still_reported(self) -> None:
        (self.fixture_dir / "notes.txt").write_text("stray\n", encoding="utf-8")

        problems, _ = validate.validate(self.root)

        expected = f"{WHERE}: unexpected file(s): notes.txt"
        self.assertIn(expected, problems)

    def test_a_nested_directory_does_not_shadow_a_missing_file(self) -> None:
        (self.fixture_dir / "fixture.toml").unlink()
        (self.fixture_dir / "archive").mkdir()
        (self.fixture_dir / "archive" / "fixture.toml").write_text("", encoding="utf-8")

        problems, _ = validate.validate(self.root)

        expected = f"{WHERE}: missing file(s): fixture.toml"
        self.assertIn(expected, problems)


if __name__ == "__main__":
    unittest.main()
