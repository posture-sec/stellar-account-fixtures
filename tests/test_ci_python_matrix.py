#!/usr/bin/env python3
"""Assert ci.yml runs the test suites across Python 3.11 and 3.12.

`.github/workflows/ci.yml` pins the test runner to a single interpreter at
python-version: "3.11". Python 3.12 introduced standard library changes
(datetime.UTC, tomllib, typing semantics) so a change passing on 3.11 could fail
on 3.12. This suite parses ci.yml with standard library text and regex parsing
and fails if either supported version is missing from the matrix.

Run: python3 -m unittest discover -s tests -t tests
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORKFLOW = REPO / ".github" / "workflows" / "ci.yml"

MATRIX_RE = re.compile(r"python-version:\s*\[(?P<versions>[^\]]*)\]")


def read_workflow() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def versions_in_matrix(text: str) -> list[str]:
    match = MATRIX_RE.search(text)
    if match is None:
        return []
    raw = match.group("versions")
    return [v.strip().strip('"').strip("'") for v in raw.split(",")]


class PythonMatrix(unittest.TestCase):
    def test_workflow_exists(self) -> None:
        self.assertTrue(WORKFLOW.is_file())

    def test_matrix_includes_3_11(self) -> None:
        self.assertIn("3.11", versions_in_matrix(read_workflow()))

    def test_matrix_includes_3_12(self) -> None:
        self.assertIn("3.12", versions_in_matrix(read_workflow()))

    def test_matrix_has_both_versions(self) -> None:
        versions = versions_in_matrix(read_workflow())
        self.assertIn("3.11", versions)
        self.assertIn("3.12", versions)


if __name__ == "__main__":
    unittest.main(verbosity=2)
