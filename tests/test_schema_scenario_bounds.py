#!/usr/bin/env python3
"""Scenario prose is one printable line of at most 200 characters."""

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
sys.path.insert(0, str(REPO_ROOT / "tools"))

import capture  # noqa: E402

import validate  # noqa: E402

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
WHERE = "fixtures/plain"
CONTROL_PROBLEM = "scenario must be a single printable line with no control characters"
LENGTH_PROBLEM = "scenario must be at most 200 characters"


def account_id() -> str:
    body = bytes([48]) + bytes(range(32))
    raw = body + validate.crc16_xmodm(body).to_bytes(2, "little")
    bits = int.from_bytes(raw, "big")
    return "".join(ALPHABET[(bits >> (5 * (55 - index))) & 0x1F] for index in range(56))


ACCOUNT = account_id()


class ScenarioBounds(unittest.TestCase):
    """A scratch captured fixture, plus an unfetchable capture seam."""

    def setUp(self) -> None:
        stage = tempfile.TemporaryDirectory(prefix="scenario-bounds-test-")
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
        labels = ", ".join(f'"{label}"' for label in sorted(validate.shapes_of(self.account)))
        self.template = (
            "# Test sidecar.\n"
            "schema_version = 1\n"
            'id = "plain"\n'
            'kind = "captured"\n'
            'scenario = "{scenario}"\n'
            f'account_id = "{ACCOUNT}"\n'
            'network = "public"\n'
            f'source_url = "{validate.NETWORKS["public"][0]}/accounts/{ACCOUNT}"\n'
            'captured_at = "2026-11-02T00:00:00Z"\n'
            "ledger = 1\n"
            'horizon_version = "30.0.0"\n'
            f'sha256 = "{hashlib.sha256(self.body).hexdigest()}"\n'
            f"shape = [{labels}]\n"
        )
        self.directory = self.root / "fixtures" / "plain"
        self.directory.mkdir(parents=True)
        (self.directory / "account.json").write_bytes(self.body)
        self.write("a plain account used to test scenario bounds")
        self.real_fetch = capture.fetch
        capture.fetch = self.no_fetch  # type: ignore[assignment]
        self.addCleanup(self.restore_fetch)

    def restore_fetch(self) -> None:
        capture.fetch = self.real_fetch  # type: ignore[assignment]

    def no_fetch(self, url: str, size: int) -> bytes:
        raise AssertionError(f"a refused scenario must not fetch {url}")

    def write(self, scenario_literal: str) -> None:
        (self.directory / "fixture.toml").write_text(
            self.template.format(scenario=scenario_literal), encoding="utf-8"
        )

    def problems(self) -> list[str]:
        return validate.validate(self.root)[0]

    def test_clean_scenario_validates(self) -> None:
        self.assertEqual(self.problems(), [])

    def test_two_hundred_characters_are_accepted(self) -> None:
        self.write("a" * validate.SCENARIO_MAX)
        self.assertEqual(self.problems(), [])

    def test_two_hundred_and_one_characters_are_rejected(self) -> None:
        self.write("a" * (validate.SCENARIO_MAX + 1))
        self.assertEqual(self.problems(), [f"{WHERE}: {LENGTH_PROBLEM}"])

    def test_a_newline_is_rejected(self) -> None:
        self.write("a\\nb")
        self.assertEqual(self.problems(), [f"{WHERE}: {CONTROL_PROBLEM}"])

    def test_a_control_character_is_rejected(self) -> None:
        self.write("a\\u0001b")
        self.assertEqual(self.problems(), [f"{WHERE}: {CONTROL_PROBLEM}"])

    def test_a_tab_is_rejected(self) -> None:
        self.write("a\\tb")
        self.assertEqual(self.problems(), [f"{WHERE}: {CONTROL_PROBLEM}"])

    def test_printable_unicode_prose_is_accepted(self) -> None:
        scenario = "an account with café and 、 punctuation in plain words"
        self.write(scenario)
        self.assertEqual(self.problems(), [])
        data = tomllib.loads((self.directory / "fixture.toml").read_text(encoding="utf-8"))
        self.assertEqual(data["scenario"], scenario)

    def test_capture_refuses_an_overlong_scenario_before_a_request(self) -> None:
        with self.assertRaises(capture.Refused) as caught:
            capture.capture("fresh", ACCOUNT, "a" * 201, "public", self.root, False)
        self.assertIn(LENGTH_PROBLEM, str(caught.exception))

    def test_capture_refuses_control_characters_before_a_request(self) -> None:
        for scenario in ("a\nb", "a\rb", "a\x01b", "a\tb"):
            with self.subTest(scenario=scenario), self.assertRaises(capture.Refused) as caught:
                capture.capture("fresh", ACCOUNT, scenario, "public", self.root, False)
            self.assertIn(CONTROL_PROBLEM, str(caught.exception))

    def test_sidecar_writer_refuses_an_unsafe_scenario(self) -> None:
        with self.assertRaises(capture.Refused):
            capture.sidecar(
                fixture_id="fresh",
                account_id=ACCOUNT,
                network="public",
                scenario="a\nb",
                source=f"{validate.NETWORKS['public'][0]}/accounts/{ACCOUNT}",
                digest="0" * 64,
                ledger=1,
                captured="2026-11-02T00:00:00Z",
                core="30.0.0",
                shape=[],
            )

    def test_schema_documents_the_bound(self) -> None:
        schema = (REPO_ROOT / "SCHEMA.md").read_text(encoding="utf-8")
        self.assertIn("at most 200 characters", schema)
        self.assertIn("no control characters or newlines", schema)

    def test_shipped_scenarios_are_printable_single_lines_within_the_bound(self) -> None:
        for directory in sorted(
            path for path in (REPO_ROOT / "fixtures").iterdir() if path.is_dir()
        ):
            with self.subTest(fixture=directory.name):
                data = tomllib.loads((directory / "fixture.toml").read_text(encoding="utf-8"))
                scenario = data["scenario"]
                self.assertLessEqual(len(scenario), validate.SCENARIO_MAX)
                self.assertTrue(scenario.isprintable())


if __name__ == "__main__":
    unittest.main()
