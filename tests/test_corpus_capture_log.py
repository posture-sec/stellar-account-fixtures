#!/usr/bin/env python3
"""Contract test for corpus/capture-log.md."""

from __future__ import annotations

import sys
import tomllib
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

CAPTURE_LOG_PATH = REPO_ROOT / "corpus" / "capture-log.md"
FIXTURES_DIR = REPO_ROOT / "fixtures"


class CorpusCaptureLogTest(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(CAPTURE_LOG_PATH.is_file(), f"{CAPTURE_LOG_PATH} does not exist")
        self.content = CAPTURE_LOG_PATH.read_text(encoding="utf-8")

    def test_zero_em_dashes(self) -> None:
        self.assertNotIn("\u2014", self.content)

    def test_table_matches_sidecars_in_timestamp_order(self) -> None:
        rows = [
            line.strip() for line in self.content.splitlines() if line.strip().startswith("| `")
        ]
        self.assertEqual(len(rows), 9, "Expected exactly nine fixture rows")

        observed: list[tuple[str, str]] = []
        for line in rows:
            parts = [part.strip().strip("`") for part in line.split("|")[1:-1]]
            self.assertEqual(len(parts), 5)
            fixture_id, network, captured_at, ledger, horizon_version = parts

            sidecar_path = FIXTURES_DIR / fixture_id / "fixture.toml"
            self.assertTrue(sidecar_path.is_file(), f"Missing sidecar {sidecar_path}")
            with sidecar_path.open("rb") as sidecar_file:
                sidecar = tomllib.load(sidecar_file)

            self.assertEqual(network, sidecar["network"])
            self.assertEqual(captured_at, sidecar["captured_at"])
            self.assertEqual(int(ledger), sidecar["ledger"])
            self.assertEqual(horizon_version, sidecar["horizon_version"])
            observed.append((captured_at, fixture_id))

        self.assertEqual(observed, sorted(observed))

    def test_log_highlights_lag_and_source_references(self) -> None:
        self.assertIn("156148 ledgers below", self.content)
        self.assertIn("validate.py:279", self.content)
        self.assertIn("SCHEMA.md:61", self.content)
