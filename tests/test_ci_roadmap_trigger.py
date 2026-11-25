#!/usr/bin/env python3
"""Assert the roadmap gate workflow triggers on pull_request and push to main.

`.github/workflows/roadmap-check.yml` is the required gate that prevents changes
from merging without updating `ROADMAP.md`. Nothing currently inspects its
trigger block, so a contributor could add a `paths:` filter and let a roadmap
touching change bypass the gate entirely. This suite parses the workflow file
with standard library text and regex parsing only, and fails if path-based
skipping is introduced.

Run: python3 -m unittest discover -s tests -t tests
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORKFLOW = REPO / ".github" / "workflows" / "roadmap-check.yml"

TRIGGER_BLOCK = re.compile(r"^on:\n(?P<body>(?:  .*\n)*)", re.MULTILINE)
PATH_FILTER = re.compile(r"^\s+paths(?:-ignore)?:")


def read_workflow() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


class RoadmapTrigger(unittest.TestCase):
    def test_workflow_exists(self) -> None:
        self.assertTrue(WORKFLOW.is_file())

    def test_pull_request_trigger_is_present(self) -> None:
        text = read_workflow()
        self.assertIn("pull_request:", text)

    def test_push_to_main_trigger_is_present(self) -> None:
        text = read_workflow()
        self.assertIn("push:", text)
        self.assertIn("branches: [main]", text)

    def test_no_path_filters_on_the_gate_workflow(self) -> None:
        text = read_workflow()
        match = TRIGGER_BLOCK.search(text)
        self.assertIsNotNone(match)
        self.assertNotRegex(match.group("body"), PATH_FILTER)


if __name__ == "__main__":
    unittest.main(verbosity=2)
