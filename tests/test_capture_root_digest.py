#!/usr/bin/env python3
"""Every captured root document has a digest that catches edits to it on disk.

A root document is the evidence for a network passphrase. Without a recorded digest,
validate.py can read passphrase and provenance from a file that was changed after the
capture, so this suite drives both the capture side and the validator side of that
contract.
"""

from __future__ import annotations

import hashlib
import json
import re
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
FIXTURE_ID = "root-digest"
ENDPOINT = "https://horizon.stellar.org"
ROOT_DOCUMENT = {
    "network_passphrase": capture.PASSPHRASES["public"],
    "horizon_version": "30.0.0",
}


class FakeHorizon:
    """A fixed root document and account, served through capture.fetch."""

    def __call__(self, url: str, cap: int) -> bytes:
        if url.endswith("/"):
            return json.dumps(ROOT_DOCUMENT).encode("utf-8")
        return json.dumps({"account_id": ACCOUNT_ID, "last_modified_ledger": 11}).encode("utf-8")


class RootDigestCapture(unittest.TestCase):
    def setUp(self) -> None:
        stage = tempfile.TemporaryDirectory()
        self.addCleanup(stage.cleanup)
        self.root = Path(stage.name)
        with mock.patch.object(capture, "fetch", FakeHorizon()):
            capture.capture(FIXTURE_ID, ACCOUNT_ID, "root digest", "public", self.root, False)
        self.document = self.root / "corpus" / "root-public.json"
        self.sidecar = self.root / "corpus" / "root-public.toml"

    def metadata(self) -> dict:
        return tomllib.loads(self.sidecar.read_bytes().decode("utf-8"))

    def test_capture_writes_url_captured_at_and_sha256(self) -> None:
        data = self.metadata()
        self.assertEqual(set(data), {"url", "captured_at", "sha256"})
        self.assertEqual(data["url"], ENDPOINT + "/")
        self.assertIsNotNone(re.match(validate.TIMESTAMP_SHAPE, str(data["captured_at"])))
        self.assertEqual(data["sha256"], hashlib.sha256(self.document.read_bytes()).hexdigest())

    def test_sidecar_is_flat_lf_toml(self) -> None:
        raw = self.sidecar.read_bytes()
        self.assertNotIn(b"\r", raw)
        self.assertTrue(raw.endswith(b"\n"))
        self.assertNotIn(b"[", raw)

    def test_a_clean_capture_validates(self) -> None:
        self.assertEqual(validate.validate(self.root)[0], [])

    def test_a_changed_root_document_is_caught(self) -> None:
        changed = self.document.read_bytes().replace(b"30.0.0", b"31.0.0")
        self.assertNotEqual(changed, self.document.read_bytes())
        self.document.write_bytes(changed)
        problems = validate.validate(self.root)[0]
        self.assertTrue(any("sha256 does not match root document" in p for p in problems))

    def test_a_wrong_recorded_digest_is_caught(self) -> None:
        text = self.sidecar.read_text(encoding="utf-8")
        self.sidecar.write_text(
            re.sub(r"sha256 = .*", f'sha256 = "{"0" * 64}"', text), encoding="utf-8"
        )
        problems = validate.validate(self.root)[0]
        self.assertTrue(any("sha256 does not match root document" in p for p in problems))

    def test_a_missing_sidecar_is_caught(self) -> None:
        self.sidecar.unlink()
        problems = validate.validate(self.root)[0]
        self.assertIn("corpus/root-public.toml: " + validate.ROOT_SIDECAR_MISSING, problems)


class ShippedRootDigests(unittest.TestCase):
    def test_each_shipped_root_document_has_a_matching_sidecar(self) -> None:
        for network in validate.NETWORKS:
            with self.subTest(network=network):
                document = REPO_ROOT / "corpus" / f"root-{network}.json"
                sidecar = REPO_ROOT / "corpus" / f"root-{network}.toml"
                self.assertTrue(document.is_file())
                self.assertTrue(sidecar.is_file())
                data = tomllib.loads(sidecar.read_bytes().decode("utf-8"))
                self.assertEqual(data["sha256"], hashlib.sha256(document.read_bytes()).hexdigest())
                self.assertEqual(data["url"], validate.NETWORKS[network][0] + "/")

    def test_the_shipped_corpus_still_validates(self) -> None:
        self.assertEqual(validate.validate(REPO_ROOT)[0], [])


if __name__ == "__main__":
    unittest.main()
