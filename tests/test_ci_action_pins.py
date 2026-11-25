#!/usr/bin/env python3
"""Subprocess suite for scripts/check_action_pins.py.

Runs the checker against scratch workflow directories and asserts that honest
pins pass and drifted, unpinned, or comment-less pins fail.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CHECKER = REPO / "scripts" / "check_action_pins.py"

STEPS = (
    "      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1\n"
    "      - uses: actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0 # v7.1.0\n"
)


def write_workflow(root: Path, name: str, body: str) -> None:
    (root / name).write_text(body, encoding="utf-8")


def run_checker(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKER), *args],
        capture_output=True,
        text=True,
    )


class ActionPins(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="action-pins-")
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name) / "workflows"
        self.dir.mkdir()

    def test_honest_pins_pass(self) -> None:
        body = (
            "name: ci\non:\n  pull_request:\njobs:\n  checks:\n    runs-on: ubuntu-latest\n"
            "    steps:\n" + STEPS
        )
        write_workflow(self.dir, "ci.yml", body)
        done = run_checker(str(self.dir))
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_missing_comment_fails(self) -> None:
        body = (
            "name: ci\non:\n  pull_request:\njobs:\n  checks:\n    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1\n"
        )
        write_workflow(self.dir, "ci.yml", body)
        done = run_checker(str(self.dir))
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("uses line is not", done.stderr)

    def test_short_sha_fails(self) -> None:
        body = (
            "name: ci\non:\n  pull_request:\njobs:\n  checks:\n    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - uses: actions/checkout@3d3c42e # v7.0.1\n"
        )
        write_workflow(self.dir, "ci.yml", body)
        done = run_checker(str(self.dir))
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("uses line is not", done.stderr)

    def test_drifted_sha_across_workflows_fails(self) -> None:
        write_workflow(
            self.dir,
            "ci.yml",
            "name: ci\non:\n  pull_request:\njobs:\n  checks:\n    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1\n",
        )
        write_workflow(
            self.dir,
            "roadmap.yml",
            "name: roadmap\non:\n  pull_request:\njobs:\n  roadmap:\n    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - uses: actions/checkout@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0 # v7.1.0\n",
        )
        done = run_checker(str(self.dir))
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("elsewhere", done.stderr)

    def test_real_workflows_pass(self) -> None:
        done = run_checker()
        self.assertEqual(done.returncode, 0, done.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
