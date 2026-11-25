#!/usr/bin/env python3
"""Every shipped capture is canonical JSON, and a whitespace edit is detected.

SCHEMA.md 2 defines the byte form: json.dumps with indent=2 and sort_keys=True plus a
trailing newline. The fixture digest is only meaningful while that form survives on
disk, so the test reads every production capture and then breaks one in a scratch copy.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import validate  # noqa: E402

FIXTURES = REPO_ROOT / "fixtures"
SPECIMEN = "default-plain"


def canonical(payload: object) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


class CanonicalJsonCorpus(unittest.TestCase):
    def fixtures(self) -> list[Path]:
        return sorted(p for p in FIXTURES.iterdir() if p.is_dir())

    def test_every_capture_is_byte_identical_to_canonical_json(self) -> None:
        fixtures = self.fixtures()
        self.assertGreaterEqual(len(fixtures), 9)
        for directory in fixtures:
            with self.subTest(fixture=directory.name):
                body = (directory / "account.json").read_bytes()
                self.assertEqual(body, canonical(json.loads(body)))

    def test_every_capture_uses_lf_and_ends_with_a_newline(self) -> None:
        for directory in self.fixtures():
            with self.subTest(fixture=directory.name):
                body = (directory / "account.json").read_bytes()
                self.assertNotIn(b"\r", body)
                self.assertTrue(body.endswith(b"\n"))

    def test_one_whitespace_byte_breaks_the_sidecar_digest(self) -> None:
        stage = tempfile.TemporaryDirectory()
        self.addCleanup(stage.cleanup)
        root = Path(stage.name)
        (root / "fixtures").mkdir()
        shutil.copytree(FIXTURES / SPECIMEN, root / "fixtures" / SPECIMEN)
        shutil.copytree(REPO_ROOT / "corpus", root / "corpus")

        body_path = root / "fixtures" / SPECIMEN / "account.json"
        body = body_path.read_bytes()
        changed = body.replace(b"{\n", b"{ \n", 1)
        self.assertNotEqual(changed, body)
        body_path.write_bytes(changed)

        self.assertNotEqual(changed, canonical(json.loads(changed)))
        problems = validate.validate(root)[0]
        self.assertTrue(any("sha256 does not match account.json" in p for p in problems), problems)


if __name__ == "__main__":
    unittest.main()
