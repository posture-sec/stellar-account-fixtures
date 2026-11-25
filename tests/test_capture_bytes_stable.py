#!/usr/bin/env python3
"""account.json must be written as the same UTF-8 bytes that were digested.

Path.write_text translates newlines on hosts whose os.linesep is CRLF, which would
make the sidecar's sha256 disagree with the file on disk. The translation below is
forced over every write_text call, so a capture that still used it would fail these
tests on any platform, not only on Windows.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools"))

import capture  # noqa: E402

import validate  # noqa: E402

ACCOUNT_ID = "GAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAWHF"
FIXTURE_ID = "lf-only-account"
ROOT_DOCUMENT = {
    "network_passphrase": capture.PASSPHRASES["public"],
    "horizon_version": "test",
}


class FakeHorizon:
    """One fixed account and root document, served through capture.fetch."""

    def __call__(self, url: str, cap: int) -> bytes:
        if url.endswith("/"):
            return json.dumps(ROOT_DOCUMENT).encode("utf-8")
        return json.dumps({"account_id": ACCOUNT_ID, "last_modified_ledger": 7}).encode("utf-8")


def canonical(payload: object) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


class BytesStableCapture(unittest.TestCase):
    def setUp(self) -> None:
        stage = tempfile.TemporaryDirectory()
        self.addCleanup(stage.cleanup)
        self.root = Path(stage.name)

    def run_capture(self) -> Path:
        with mock.patch.object(capture, "fetch", FakeHorizon()):
            return capture.capture(FIXTURE_ID, ACCOUNT_ID, "lf only", "public", self.root, False)

    def test_account_json_is_the_exact_canonical_byte_string(self) -> None:
        directory = self.run_capture()
        body = (directory / "account.json").read_bytes()
        self.assertEqual(body, canonical(json.loads(body)))
        self.assertNotIn(b"\r", body)

    def test_the_sidecar_digests_the_bytes_on_disk(self) -> None:
        directory = self.run_capture()
        body = (directory / "account.json").read_bytes()
        data = tomllib.loads((directory / "fixture.toml").read_bytes().decode("utf-8"))
        self.assertEqual(data["sha256"], hashlib.sha256(body).hexdigest())
        self.assertEqual(validate.validate(self.root)[0], [])

    def test_forced_crlf_translation_does_not_reach_account_json(self) -> None:
        real_write_text = Path.write_text

        def translating_write_text(path: Path, data: str, *args: object, **kwargs: object) -> int:
            translated = data.replace("\n", "\r\n") if isinstance(data, str) else data
            return real_write_text(path, translated, *args, **kwargs)  # type: ignore[arg-type]

        with mock.patch.object(Path, "write_text", translating_write_text):
            directory = self.run_capture()
        body = (directory / "account.json").read_bytes()
        self.assertNotIn(b"\r", body)
        self.assertEqual(body, canonical(json.loads(body)))
        self.assertEqual(validate.validate(self.root)[0], [])


if __name__ == "__main__":
    unittest.main()
