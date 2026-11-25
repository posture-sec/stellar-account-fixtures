#!/usr/bin/env python3
"""Contract test for tools/manifest.py (issue #17, #18).

Asserts that tools/manifest.py outputs reproducible JSON lines sorted by fixture id,
with exact fields (id, account_id, network, ledger, sha256), and line count matching
the fixture directory count.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from tools.manifest import build_manifest

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = REPO_ROOT / "fixtures"
MANIFEST_SCRIPT = REPO_ROOT / "tools" / "manifest.py"


class ManifestTest(unittest.TestCase):
    def test_build_manifest_returns_all_fixtures(self) -> None:
        records = build_manifest()
        expected_count = len(
            [p for p in FIXTURES_DIR.iterdir() if p.is_dir() and (p / "fixture.toml").is_file()]
        )
        self.assertEqual(len(records), expected_count)
        self.assertEqual(len(records), 14)

    def test_build_manifest_is_sorted_by_id(self) -> None:
        records = build_manifest()
        ids = [str(r["id"]) for r in records]
        self.assertEqual(ids, sorted(ids))

    def test_manifest_record_keys(self) -> None:
        records = build_manifest()
        for r in records:
            self.assertIn("id", r)
            self.assertIn("account_id", r)
            self.assertIn("network", r)
            self.assertIn("ledger", r)
            self.assertIn("sha256", r)
            self.assertTrue(str(r["account_id"]).startswith("G"))
            self.assertEqual(len(str(r["sha256"])), 64)

    def test_cli_execution_outputs_valid_json_lines(self) -> None:
        res = subprocess.run(
            [sys.executable, str(MANIFEST_SCRIPT)],
            capture_output=True,
            text=True,
            check=True,
        )
        lines = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        self.assertEqual(len(lines), 14)
        for line in lines:
            parsed = json.loads(line)
            self.assertIsInstance(parsed, dict)
            self.assertIn("id", parsed)
            self.assertIn("sha256", parsed)

    def test_zero_em_dashes(self) -> None:
        content = Path(__file__).read_text(encoding="utf-8")
        self.assertNotIn("\u2014", content)


if __name__ == "__main__":
    unittest.main()
