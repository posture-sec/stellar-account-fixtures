#!/usr/bin/env python3
"""Contract tests for the generated uncovered-shape list in README.md."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scripts.sync_readme as sync_readme

REPO_ROOT = Path(__file__).resolve().parents[1]
README_PATH = REPO_ROOT / "README.md"


class ReadmeGapListTest(unittest.TestCase):
    def test_derives_uncovered_labels_from_schema_and_sidecars(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            schema = root / "SCHEMA.md"
            fixtures = root / "fixtures"
            schema.write_text(
                "## 5. The shape vocabulary\n"
                "| Label | Derived when |\n"
                "|---|---|\n"
                "| `covered` | example |\n"
                "| `missing_z` | example |\n"
                "| `missing_a` | example |\n"
                "## 6. Root documents\n",
                encoding="utf-8",
            )
            for fixture_id, shapes in (
                ("first", 'shape = ["covered"]\n'),
                ("second", 'shape = ["covered"]\n'),
            ):
                fixture_dir = fixtures / fixture_id
                fixture_dir.mkdir(parents=True)
                (fixture_dir / "fixture.toml").write_text(shapes, encoding="utf-8")

            with (
                patch.object(sync_readme, "SCHEMA_PATH", schema),
                patch.object(sync_readme, "FIXTURES_DIR", fixtures),
            ):
                block = sync_readme.generate_shape_gaps_block()

        self.assertEqual(
            block,
            "\n".join(
                [
                    sync_readme.SHAPE_GAPS_START,
                    "1 of 3 shape labels have a fixture. These 2 do not:",
                    "",
                    "- `missing_a`",
                    "- `missing_z`",
                    sync_readme.SHAPE_GAPS_END,
                ]
            ),
        )

    def test_check_mode_detects_readme_gap_list_drift_without_writing(self) -> None:
        original = README_PATH.read_text(encoding="utf-8")
        stale = original.replace("- `auth_clawback_enabled`", "- `covered_in_error`", 1)
        self.assertNotEqual(stale, original)

        with tempfile.TemporaryDirectory() as tmp_dir:
            readme = Path(tmp_dir) / "README.md"
            readme.write_text(stale, encoding="utf-8")
            with patch.object(sync_readme, "README_PATH", readme):
                self.assertFalse(sync_readme.sync(check=True))
            self.assertEqual(readme.read_text(encoding="utf-8"), stale)

    def test_readme_gap_markers_and_sync(self) -> None:
        content = README_PATH.read_text(encoding="utf-8")
        self.assertIn(sync_readme.SHAPE_GAPS_START, content)
        self.assertIn(sync_readme.SHAPE_GAPS_END, content)
        self.assertTrue(sync_readme.sync(check=True))

    def test_zero_em_dashes(self) -> None:
        self.assertNotIn("\u2014", Path(__file__).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
