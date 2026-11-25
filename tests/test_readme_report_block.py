#!/usr/bin/env python3
"""Contract test for the illustrative README report block (issue #106)."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
README_PATH = REPO_ROOT / "README.md"
REPORT_COMMAND = "$ python3 validate.py --report"


class ReadmeReportBlockTest(unittest.TestCase):
    def report_note(self) -> str:
        readme = README_PATH.read_text(encoding="utf-8")
        command = readme.index(REPORT_COMMAND)
        closing_fence = readme.index("\n```", command)
        note = readme[closing_fence + len("\n```") :].lstrip("\n")
        return note.split("\n\n", maxsplit=1)[0]

    def test_report_note_explains_the_illustrative_baseline(self) -> None:
        note = self.report_note()
        self.assertIn("illustrates", note)
        self.assertIn("nine baseline specimens", note)
        self.assertIn("`python3 validate.py --report`", note)

    def test_report_note_has_no_hardcoded_execution_date(self) -> None:
        self.assertNotRegex(self.report_note(), re.compile(r"\b\d{4}-\d{2}-\d{2}\b"))

    def test_zero_em_dashes(self) -> None:
        content = Path(__file__).read_text(encoding="utf-8")
        self.assertNotIn("\u2014", content)


if __name__ == "__main__":
    unittest.main()
