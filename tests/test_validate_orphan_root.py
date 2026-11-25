#!/usr/bin/env python3
"""Show that check_root reads only the root documents networks declare.

A fixture's sidecar is the only source of the network set handed to check_root. An extra
root document in corpus/ is therefore invisible to this tool, even when its bytes are
malformed. That is the design implication for network cleanups: retiring the last fixture
that declares a network stops the validator from opening that network's root document,
while removing the stale root file itself is housekeeping rather than validation.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import validate  # noqa: E402

ORPHAN_NAME = "root-orphan.json"
ORPHAN_BYTES = b'{"network_passphrase": ' + b"\xff\xfe" + b"\n"
STALE_BYTES = b"[this is not JSON]\n"


class OrphanRootDocument(unittest.TestCase):
    def setUp(self) -> None:
        stage = tempfile.TemporaryDirectory(prefix="orphan-root-")
        self.addCleanup(stage.cleanup)
        self.root = Path(stage.name)
        shutil.copytree(REPO_ROOT / "fixtures", self.root / "fixtures")
        shutil.copytree(REPO_ROOT / "corpus", self.root / "corpus")
        self.corpus = self.root / "corpus"
        self.orphan = self.corpus / ORPHAN_NAME
        self.orphan.write_bytes(ORPHAN_BYTES)

    def validate_with_root_read_trace(
        self,
    ) -> tuple[list[str], list[str], list[Path]]:
        reads: list[Path] = []

        def traced(method: str):
            original = getattr(Path, method)

            def read(path: Path, *args: object, **kwargs: object) -> object:
                if path.name.startswith("root-"):
                    reads.append(path)
                    if path == self.orphan:
                        raise AssertionError(f"an unreferenced root document was read: {path}")
                return original(path, *args, **kwargs)

            return read

        with (
            mock.patch.object(Path, "read_bytes", traced("read_bytes")),
            mock.patch.object(Path, "read_text", traced("read_text")),
        ):
            problems, report = validate.validate(self.root)
        return problems, report, reads

    def test_an_unparseable_orphan_root_is_not_a_problem(self) -> None:
        problems, report = validate.validate(self.root)

        self.assertEqual(problems, [])
        self.assertEqual(report, [])
        self.assertEqual(self.orphan.read_bytes(), ORPHAN_BYTES)

    def test_only_declared_network_roots_are_opened(self) -> None:
        problems, report, reads = self.validate_with_root_read_trace()

        self.assertEqual(problems, [])
        self.assertEqual(report, [])
        self.assertNotIn(self.orphan, reads)
        for network in sorted(validate.NETWORKS):
            self.assertIn(self.corpus / f"root-{network}.json", reads)
            self.assertIn(self.corpus / f"root-{network}.toml", reads)

    def test_retiring_a_network_stops_inspection_of_its_stale_root(self) -> None:
        for fixture in (self.root / "fixtures").iterdir():
            if not fixture.is_dir():
                continue
            sidecar = fixture / "fixture.toml"
            data = tomllib.loads(sidecar.read_text(encoding="utf-8"))
            if data.get("network") == "testnet":
                shutil.rmtree(fixture)
        stale = self.corpus / "root-testnet.json"
        stale.write_bytes(STALE_BYTES)

        problems, report = validate.validate(self.root)

        self.assertEqual(problems, [])
        self.assertEqual(report, [])
        self.assertEqual(stale.read_bytes(), STALE_BYTES)
