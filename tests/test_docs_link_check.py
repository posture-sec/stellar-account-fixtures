#!/usr/bin/env python3
"""Subprocess test suite for `scripts/check_docs_links.py`.

Exercises relative markdown path resolution, in-file and cross-file heading
anchors, fenced/inline code exclusion, external link skipping, and diagnostic
reporting over temporary documentation trees.

Run: python3 -m unittest tests/test_docs_link_check.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check_docs_links.py"


class DocsLinkCheckSubprocessTest(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory(prefix="docs-link-check-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def write_doc(self, rel_path: str, content: str) -> Path:
        target = self.root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        return target

    def run_checker(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )

    def test_zero_em_dashes_in_script_and_tests(self) -> None:
        for path in (SCRIPT, Path(__file__)):
            self.assertNotIn("\u2014", path.read_text(encoding="utf-8"), str(path))

    def test_repository_docs_resolve_cleanly(self) -> None:
        done = self.run_checker()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("checked 4 file(s)", done.stdout)
        self.assertIn("0 broken", done.stdout)
        self.assertEqual(done.stderr, "")

    def test_valid_relative_links_and_anchors_pass(self) -> None:
        self.write_doc(
            "README.md",
            "# Project Overview\n\n"
            "See [Schema](SCHEMA.md#2-accountjson), "
            "[Contributing](CONTRIBUTING.md#workflow), "
            "[Guide](docs/guide.md#repeated-heading-1), "
            "[Local](#project-overview), "
            "and [External](https://example.invalid/never-fetched).\n\n"
            "Inline `[ignored](missing.md)` should not be checked.\n\n"
            "```markdown\n"
            "# Not a Heading\n"
            "[fenced](also-missing.md)\n"
            "```\n",
        )
        self.write_doc(
            "CONTRIBUTING.md",
            "# Contributing\n\n## Workflow\n\nRead [README](README.md#project-overview).\n",
        )
        self.write_doc(
            "SCHEMA.md",
            "# Schema\n\n## 2. account.json\n\nDetails.\n",
        )
        self.write_doc(
            "docs/guide.md",
            "# Guide\n\n## Repeated Heading\n\nFirst.\n\n"
            "## Repeated Heading\n\nSecond.\n\n"
            "Back to [Root](../README.md#project-overview).\n",
        )

        done = self.run_checker("--root", str(self.root))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("checked 4 file(s), 6 relative link(s), 0 broken", done.stdout)
        self.assertEqual(done.stderr, "")

    def test_missing_relative_file_fails_with_location(self) -> None:
        self.write_doc(
            "README.md",
            "# Home\n\nSee [Missing](docs/nonexistent.md).\n",
        )

        done = self.run_checker("--root", str(self.root))
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn("README.md:3:", done.stderr)
        self.assertIn("docs/nonexistent.md", done.stderr)
        self.assertNotIn("Traceback (most recent call last)", done.stderr)

    def test_broken_in_file_anchor_fails(self) -> None:
        self.write_doc(
            "README.md",
            "# Home\n\nJump to [Nowhere](#missing-section).\n",
        )

        done = self.run_checker("--root", str(self.root))
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn("README.md:3:", done.stderr)
        self.assertIn("#missing-section", done.stderr)
        self.assertNotIn("Traceback (most recent call last)", done.stderr)

    def test_broken_cross_file_anchor_fails(self) -> None:
        self.write_doc(
            "CONTRIBUTING.md",
            "# Contributing\n\nSee [Bad Section](SCHEMA.md#renamed-section).\n",
        )
        self.write_doc(
            "SCHEMA.md",
            "# Schema\n\n## Current Section\n",
        )

        done = self.run_checker("--root", str(self.root))
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn("CONTRIBUTING.md:3:", done.stderr)
        self.assertIn("#renamed-section", done.stderr)
        self.assertIn("SCHEMA.md", done.stderr)

    def test_nested_docs_broken_relative_link_fails(self) -> None:
        self.write_doc("README.md", "# Home\n")
        self.write_doc(
            "docs/nested/notes.md",
            "# Notes\n\nBroken [Up](../missing.md).\n",
        )

        done = self.run_checker("--root", str(self.root))
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn("docs/nested/notes.md:3:", done.stderr)
        self.assertIn("../missing.md", done.stderr)

    def test_escaping_root_and_empty_target_fail_cleanly(self) -> None:
        self.write_doc(
            "README.md",
            "# Home\n\n[Escape](../../outside.md)\n[Empty]()\n",
        )

        done = self.run_checker("--root", str(self.root))
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn("escapes repository root", done.stderr)
        self.assertIn("empty or malformed", done.stderr)
        self.assertIn("2 broken link(s) found", done.stderr)
        self.assertNotIn("Traceback (most recent call last)", done.stderr)

    def test_empty_root_reports_missing_docs(self) -> None:
        done = self.run_checker("--root", str(self.root))
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn("no documentation files found", done.stderr)
        self.assertNotIn("Traceback (most recent call last)", done.stderr)


if __name__ == "__main__":
    unittest.main()
