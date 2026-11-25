#!/usr/bin/env python3
"""Assert the pages workflow runs sync_readme --check before deploying.

`.github/workflows/pages.yml` uploads the site/ directory verbatim. If badge
files in site/data/badge-*.json were not regenerated, stale metrics deploy to
GitHub Pages. This suite parses pages.yml with standard library text and regex
parsing and fails if the `python3 scripts/sync_readme.py --check` preflight
step is missing or not placed before the artifact upload.

Run: python3 -m unittest discover -s tests -t tests
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORKFLOW = REPO / ".github" / "workflows" / "pages.yml"

SYNC_CHECK = "python3 scripts/sync_readme.py --check"
UPLOAD = "upload-pages-artifact"


def read_workflow() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


class BadgeFreshness(unittest.TestCase):
    def test_workflow_exists(self) -> None:
        self.assertTrue(WORKFLOW.is_file())

    def test_sync_readme_check_preflight_present(self) -> None:
        text = read_workflow()
        self.assertIn(SYNC_CHECK, text)

    def test_preflight_runs_before_artifact_upload(self) -> None:
        text = read_workflow()
        sync_index = text.find(SYNC_CHECK)
        upload_index = text.find(UPLOAD)
        self.assertNotEqual(sync_index, -1)
        self.assertNotEqual(upload_index, -1)
        self.assertLess(sync_index, upload_index)

    def test_python_setup_present(self) -> None:
        text = read_workflow()
        self.assertIn("setup-python", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
