#!/usr/bin/env python3
"""Guard the phase 2 task list and the changelog against silently dropped work.

A merge that resolves ROADMAP.md in favour of the incoming branch can remove task
lines while the documents, tests and changelog rows they describe stay behind. That
happened twice here: tasks 2.43 to 2.52 vanished from the phase 2 list, and a later
merge left a second copy of the tail of the document holding tasks the head of the
file no longer had. These checks fail on both shapes:

- phase 2 task numbers are unique and increase in file order;
- the numbering has no gaps, so a block cannot be deleted from the middle or a tail
  copy cannot take the file's place;
- every task number named by a changelog row exists in the phase 2 list;
- when origin/main is available, every task it carries is still here, so the list
  only grows.
"""

from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ROADMAP = REPO_ROOT / "ROADMAP.md"

TASK = re.compile(r"^- \[[ x]\] \*\*2\.(\d+)\*\*", re.MULTILINE)
PHASE = re.compile(r"^### Phase (\d+):", re.MULTILINE)
# A changelog row's last column names the work it closes: "| 2.39 |", "| 2.43 to 2.46 |".
CHANGELOG_ROW = re.compile(r"^\| (\d{4}-\d{2}-\d{2}[^|]*)\|.*\|([^|]*)\|\s*$", re.MULTILINE)
ROW_TASK = re.compile(r"\b2\.(\d+)\b")
ROW_PROSE_TASK = re.compile(r"\bTasks? 2\.(\d+)\b")
# The tail copy that a bad merge appended starts with a heading the file already has.
SECTION = re.compile(r"^## \d+\.", re.MULTILINE)


def phase_section(text: str, phase: int) -> str:
    starts = [m for m in PHASE.finditer(text) if int(m.group(1)) == phase]
    if not starts:
        raise ValueError(f"no phase {phase} heading")
    after = [m.start() for m in PHASE.finditer(text) if m.start() > starts[0].start()]
    end = after[0] if after else len(text)
    return text[starts[0].start() : end]


def task_numbers(text: str) -> list[int]:
    return [int(n) for n in TASK.findall(phase_section(text, 2))]


def roadmap_at(rev: str) -> str | None:
    """The roadmap at a git revision, or None when this checkout cannot see it."""
    try:
        done = subprocess.run(
            ["git", "show", f"{rev}:ROADMAP.md"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return done.stdout


class RoadmapTaskGuardTest(unittest.TestCase):
    def setUp(self) -> None:
        self.text = ROADMAP.read_text(encoding="utf-8")
        self.tasks = task_numbers(self.text)

    def test_phase_two_has_tasks(self) -> None:
        self.assertGreater(len(self.tasks), 40, "the phase 2 task list is suspiciously short")

    def test_task_numbers_are_unique(self) -> None:
        duplicates = sorted({n for n in self.tasks if self.tasks.count(n) > 1})
        self.assertEqual(duplicates, [], f"phase 2 reuses task numbers: {duplicates}")

    def test_task_numbers_increase_in_file_order(self) -> None:
        self.assertEqual(self.tasks, sorted(self.tasks), "phase 2 tasks are out of order")

    def test_task_numbering_has_no_gaps(self) -> None:
        self.assertEqual(
            self.tasks,
            list(range(1, len(self.tasks) + 1)),
            "phase 2 numbering has a gap or a tail copy: a block of tasks was dropped",
        )

    def test_every_changelog_task_reference_exists(self) -> None:
        named: set[int] = set()
        for _, tail in CHANGELOG_ROW.findall(self.text):
            named.update(int(n) for n in ROW_TASK.findall(tail))
        for row in self.text.splitlines():
            named.update(int(n) for n in ROW_PROSE_TASK.findall(row))
        unknown = sorted(n for n in named if n not in set(self.tasks))
        self.assertEqual(
            unknown,
            [],
            "changelog rows name phase 2 tasks the list does not contain: "
            + ", ".join(f"2.{n}" for n in unknown),
        )

    def test_the_task_list_only_grows_against_origin_main(self) -> None:
        base = roadmap_at("origin/main")
        if base is None:
            self.skipTest("origin/main is not available in this checkout")
        try:
            theirs = set(task_numbers(base))
        except ValueError:
            self.skipTest("origin/main has no phase 2 section")
        lost = sorted(theirs - set(self.tasks))
        self.assertEqual(
            lost,
            [],
            "this branch drops phase 2 tasks present on origin/main: "
            + ", ".join(f"2.{n}" for n in lost),
        )


if __name__ == "__main__":
    unittest.main()
