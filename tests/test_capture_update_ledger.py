#!/usr/bin/env python3
"""An --update re-capture must not replace a newer observation with an older one.

The ledger in fixture.toml is the only record of how fresh a capture is, so capture()
reads it before fetching the replacement and refuses a strictly lower incoming ledger.
The tests here assert both numbers in the refusal and prove a refused update leaves the
fixture exactly as it was.
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import tomllib
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools"))

import capture  # noqa: E402

ACCOUNT_ID = "GAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAWHF"
FIXTURE_ID = "ledger-monotonicity"
OLD_LEDGER = 500
ROOT_DOCUMENT = {
    "network_passphrase": capture.PASSPHRASES["public"],
    "horizon_version": "test",
}


class FakeHorizon:
    """One account read whose ledger the test can move backwards or forwards."""

    def __init__(self, ledger: int) -> None:
        self.ledger = ledger
        self.calls: list[str] = []

    def __call__(self, url: str, cap: int) -> bytes:
        self.calls.append(url)
        if url.endswith("/"):
            return json.dumps(ROOT_DOCUMENT).encode("utf-8")
        return json.dumps({"account_id": ACCOUNT_ID, "last_modified_ledger": self.ledger}).encode(
            "utf-8"
        )


class UpdateLedgerMonotonicity(unittest.TestCase):
    def setUp(self) -> None:
        stage = tempfile.TemporaryDirectory()
        self.addCleanup(stage.cleanup)
        self.root = Path(stage.name)
        self.directory = self.capture(OLD_LEDGER, update=False)

    def capture(self, ledger: int, *, update: bool) -> Path:
        with mock.patch.object(capture, "fetch", FakeHorizon(ledger)):
            return capture.capture(
                FIXTURE_ID, ACCOUNT_ID, "ledger test", "public", self.root, update
            )

    def sidecar(self) -> dict:
        text = (self.directory / "fixture.toml").read_bytes().decode("utf-8")
        return tomllib.loads(text)

    def test_an_older_ledger_is_refused_with_both_values(self) -> None:
        with self.assertRaises(capture.Refused) as raised:
            self.capture(OLD_LEDGER - 1, update=True)
        message = str(raised.exception)
        self.assertIn(str(OLD_LEDGER), message)
        self.assertIn(str(OLD_LEDGER - 1), message)
        self.assertIn("older", message)

    def test_a_refused_update_leaves_the_fixture_intact(self) -> None:
        body_before = (self.directory / "account.json").read_bytes()
        sidecar_before = (self.directory / "fixture.toml").read_bytes()
        with self.assertRaises(capture.Refused):
            self.capture(OLD_LEDGER - 1, update=True)
        self.assertEqual((self.directory / "account.json").read_bytes(), body_before)
        self.assertEqual((self.directory / "fixture.toml").read_bytes(), sidecar_before)
        self.assertEqual(self.sidecar()["ledger"], OLD_LEDGER)

    def test_an_equal_ledger_is_accepted(self) -> None:
        self.capture(OLD_LEDGER, update=True)
        self.assertEqual(self.sidecar()["ledger"], OLD_LEDGER)

    def test_a_newer_ledger_is_accepted_and_recorded(self) -> None:
        self.capture(OLD_LEDGER + 10, update=True)
        self.assertEqual(self.sidecar()["ledger"], OLD_LEDGER + 10)

    def test_main_reports_exit_two_for_an_older_ledger(self) -> None:
        stderr = io.StringIO()
        with (
            mock.patch.object(capture, "fetch", FakeHorizon(OLD_LEDGER - 1)),
            redirect_stderr(stderr),
        ):
            code = capture.main(
                [
                    "--network",
                    "public",
                    "--account",
                    ACCOUNT_ID,
                    "--id",
                    FIXTURE_ID,
                    "--scenario",
                    "ledger test",
                    "--root",
                    str(self.root),
                    "--update",
                ]
            )
        self.assertEqual(code, 2)
        self.assertIn("capture refused", stderr.getvalue())
        self.assertIn(str(OLD_LEDGER), stderr.getvalue())

    def test_a_fixture_without_a_readable_ledger_is_refused(self) -> None:
        (self.directory / "fixture.toml").unlink()
        with self.assertRaises(capture.Refused) as raised:
            self.capture(OLD_LEDGER + 1, update=True)
        self.assertIn("cannot check that an update is newer", str(raised.exception))

    def test_a_fixture_without_a_ledger_key_is_refused(self) -> None:
        path = self.directory / "fixture.toml"
        text = path.read_text(encoding="utf-8")
        kept = [line for line in text.splitlines(keepends=True) if not line.startswith("ledger")]
        path.write_text("".join(kept), encoding="utf-8")
        with self.assertRaises(capture.Refused) as raised:
            self.capture(OLD_LEDGER + 1, update=True)
        self.assertIn("is not an integer", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
