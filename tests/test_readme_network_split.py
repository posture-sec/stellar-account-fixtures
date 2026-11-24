#!/usr/bin/env python3
"""Contract test for dynamic network split derivation in scripts/sync_readme.py (issue #100).

Asserts that mainnet and testnet capture counts are dynamically derived from fixture sidecars
rather than hardcoded, and that the metrics table row interpolates the derived counts.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.sync_readme import count_networks, generate_metrics_table

REPO_ROOT = Path(__file__).resolve().parents[1]
README_PATH = REPO_ROOT / "README.md"


class ReadmeNetworkSplitTest(unittest.TestCase):
    def test_count_networks_on_real_corpus(self) -> None:
        mainnet, testnet = count_networks()
        self.assertEqual(mainnet, 10)
        self.assertEqual(testnet, 2)

    def test_generate_metrics_table_interpolates_split(self) -> None:
        table = generate_metrics_table(
            fixtures_count=10, test_count=126, mainnet_count=8, testnet_count=2
        )
        expected_row = "| Verified Captures | **10 accounts** (8 Mainnet, 2 Test) | `fixtures/` |"
        self.assertIn(expected_row, table)

    def test_count_networks_with_custom_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            # Create 2 public and 1 testnet fixtures
            for name, net in [("f1", "public"), ("f2", "public"), ("f3", "testnet")]:
                f_dir = tmp_path / name
                f_dir.mkdir()
                (f_dir / "account.json").write_text("{}", encoding="utf-8")
                (f_dir / "fixture.toml").write_text(f'network = "{net}"\n', encoding="utf-8")

            import scripts.sync_readme as sr

            orig_dir = sr.FIXTURES_DIR
            try:
                sr.FIXTURES_DIR = tmp_path
                m, t = sr.count_networks()
                self.assertEqual(m, 2)
                self.assertEqual(t, 1)
            finally:
                sr.FIXTURES_DIR = orig_dir

    def test_zero_em_dashes(self) -> None:
        content = Path(__file__).read_text(encoding="utf-8")
        self.assertNotIn("\u2014", content)


if __name__ == "__main__":
    unittest.main()
