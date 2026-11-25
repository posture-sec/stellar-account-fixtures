#!/usr/bin/env python3
"""Sidecar shape labels must be unique, for captured and synthetic fixtures alike."""

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


class DuplicateShapeLabels(unittest.TestCase):
    def setUp(self) -> None:
        stage = tempfile.TemporaryDirectory(prefix="shape-duplicates-test-")
        self.addCleanup(stage.cleanup)
        self.root = Path(stage.name)
        (self.root / "corpus").mkdir()
        endpoint, passphrase = validate.NETWORKS["public"]
        root_body = (json.dumps({"network_passphrase": passphrase}) + "\n").encode()
        (self.root / "corpus" / "root-public.json").write_bytes(root_body)
        (self.root / "corpus" / "root-public.toml").write_text(
            "# Test root sidecar.\n"
            f'url = "{endpoint}/"\n'
            'captured_at = "2026-11-02T00:00:00Z"\n'
            f'sha256 = "{hashlib.sha256(root_body).hexdigest()}"\n',
            encoding="utf-8",
        )
        self.account: dict[str, object] = {"account_id": ACCOUNT}
        self.body = (json.dumps(self.account, indent=2, sort_keys=True) + "\n").encode()
        self.labels = sorted(validate.shapes_of(self.account))
        self.directory = self.root / "fixtures" / "plain"
        self.directory.mkdir(parents=True)
        (self.directory / "account.json").write_bytes(self.body)
        self.write(shape=self.labels)

    def write(self, shape: list[str], *, kind: str = "captured") -> None:
        scenario = "a plain account used to test shape label uniqueness"
        if kind == "synthetic":
            scenario = "synthetic: a plain account used to test shape label uniqueness"
        lines = [
            "# Test sidecar.",
            "schema_version = 1",
            'id = "plain"',
            f'kind = "{kind}"',
            f'scenario = "{scenario}"',
            f'account_id = "{ACCOUNT}"',
            'network = "public"',
        ]
        if kind == "captured":
            endpoint = validate.NETWORKS["public"][0]
            lines.extend(
                [
                    f'source_url = "{endpoint}/accounts/{ACCOUNT}"',
                    'captured_at = "2026-11-02T00:00:00Z"',
                    "ledger = 1",
                    'horizon_version = "30.0.0"',
                    f'sha256 = "{hashlib.sha256(self.body).hexdigest()}"',
                ]
            )
        labels = ", ".join(f'"{label}"' for label in shape)
        lines.append(f"shape = [{labels}]")
        (self.directory / "fixture.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def problems(self) -> list[str]:
        return validate.validate(self.root)[0]

    def test_unique_shape_is_clean(self) -> None:
        self.assertEqual(self.problems(), [])

    def test_a_repeated_label_is_reported_by_name(self) -> None:
        label = self.labels[0]
        self.write(shape=[*self.labels, label])
        self.assertEqual(self.problems(), [f"{WHERE}: shape lists duplicate label {label!r}"])

    def test_each_repeated_label_is_reported_once(self) -> None:
        first, second = self.labels[0], self.labels[1]
        self.write(shape=[*self.labels, first, first, second, second])
        self.assertEqual(
            self.problems(),
            [
                f"{WHERE}: shape lists duplicate label {first!r}",
                f"{WHERE}: shape lists duplicate label {second!r}",
            ],
        )

    def test_one_label_repeated_three_times_gets_one_error(self) -> None:
        label = self.labels[0]
        self.write(shape=[*self.labels, label, label])
        self.assertEqual(self.problems(), [f"{WHERE}: shape lists duplicate label {label!r}"])

    def test_a_synthetic_fixture_is_checked_too(self) -> None:
        label = self.labels[0]
        self.write(shape=[*self.labels, label], kind="synthetic")
        self.assertEqual(self.problems(), [f"{WHERE}: shape lists duplicate label {label!r}"])

    def test_shipped_fixtures_have_unique_shape_labels(self) -> None:
        for directory in sorted(
            path for path in (REPO_ROOT / "fixtures").iterdir() if path.is_dir()
        ):
            with self.subTest(fixture=directory.name):
                data = tomllib.loads((directory / "fixture.toml").read_text(encoding="utf-8"))
                shape = data["shape"]
                self.assertEqual(len(shape), len(set(shape)))


if __name__ == "__main__":
    unittest.main()
