#!/usr/bin/env python3
"""Self-test for the two scripts the `roadmap-check / gate` check runs (task 1.8).

That gate is the reason a pull request here cannot merge a change without updating
`ROADMAP.md` in the same breath, so the scripts behind it get the treatment the corpus
gives its own sidecars: run them, read what they say, and hold them to answering a
broken input with a sentence a person can act on rather than a traceback.

Nothing here reaches the real repository. The git cases build their own history in a
temporary directory with `HOME` and both config files pointed away from the machine
running them, and the progress cases pass their own roadmap path in every call so the
script never has a reason to open the one under version control. The scripts are read
from this checkout; the only paths they write are inside the temporary one.

Run: python3 -m unittest discover -s tests -t tests
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PROGRESS = REPO / "scripts" / "roadmap_progress.py"
TOUCHED = REPO / "scripts" / "check_roadmap_touched.sh"

START = "<!-- PROGRESS:START -->"
END = "<!-- PROGRESS:END -->"

IDENTITY = ["-c", "user.name=Scratch", "-c", "user.email=scratch@example.invalid"]

Phase = tuple[str, tuple[str, ...]]

DEFAULT_PHASES: tuple[Phase, ...] = (
    ("### Phase 0: Ground work", ("- [x] **0.1** First task.", "- [ ] **0.2** Second task.")),
    ("### Phase 1: Protection", ("- [x] **1.1** Third task.",)),
)
DEFAULT_GATES = ("- [x] **G1** CI is green.", "- [ ] **G2** Protection is on.")


def roadmap_text(
    *,
    last_updated: str = "Last updated: 2026-11-02T00:00Z (seed)",
    markers: bool = True,
    phases: tuple[Phase, ...] = DEFAULT_PHASES,
    gates: tuple[str, ...] = DEFAULT_GATES,
) -> str:
    """A roadmap small enough to count by hand, in the shape the two scripts expect."""
    lines = ["# ROADMAP: scratch", "", last_updated, ""]
    for heading, tasks in phases:
        lines += [heading, "", *tasks]
        lines.append("")
    lines += ["## Gates", "", *gates, ""]
    if markers:
        lines += [START, END, ""]
    return "\n".join(lines)


def git_env(home: Path) -> dict[str, str]:
    """The environment a git command runs with: this machine's PATH, none of its config.

    `GITHUB_BASE_REF` is dropped so a run inside Actions behaves like a run on a laptop,
    and the identity comes from the `-c` flags on each commit instead of a config file.
    """
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"GITHUB_BASE_REF", "GIT_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE"}
    }
    (home / "gitconfig").touch()
    env.update(
        HOME=str(home),
        GIT_CONFIG_GLOBAL=str(home / "gitconfig"),
        GIT_CONFIG_SYSTEM=os.devnull,
        GIT_TERMINAL_PROMPT="0",
    )
    return env


class Scratch(unittest.TestCase):
    """A temporary directory and the two ways of driving the scripts against it."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory(prefix="roadmap-gate-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.env = git_env(self.home)

    def write(self, text: str) -> Path:
        path = self.root / "ROADMAP.md"
        path.write_text(text, encoding="utf-8")
        return path

    def roadmap(
        self,
        *,
        markers: bool = True,
        phases: tuple[Phase, ...] = DEFAULT_PHASES,
        gates: tuple[str, ...] = DEFAULT_GATES,
    ) -> Path:
        return self.write(roadmap_text(markers=markers, phases=phases, gates=gates))

    def run_progress(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(PROGRESS), *args],
            capture_output=True,
            text=True,
            cwd=self.root,
            env=self.env,
        )

    def run_touched(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(TOUCHED), *args],
            capture_output=True,
            text=True,
            cwd=cwd or self.root,
            env=self.env,
        )

    def git(self, *args: str) -> str:
        done = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            cwd=self.root,
            env=self.env,
            check=True,
        )
        return done.stdout

    def assert_clean_error(self, done: subprocess.CompletedProcess[str], message: str) -> None:
        """Exit 1, the reason on stderr, and no traceback anywhere in the output.

        A gate that fails with a stack trace tells a contributor nothing about the line
        they wrote, so the readable sentence is the contract under test.
        """
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn(message, done.stderr)
        for stream in (done.stdout, done.stderr):
            self.assertNotIn("Traceback (most recent call last)", stream)


class ProgressTable(Scratch):
    """`scripts/roadmap_progress.py`: write mode, `--check`, and the broken inputs."""

    def test_write_mode_renders_the_table_and_check_then_passes(self) -> None:
        path = self.roadmap()
        written = self.run_progress(str(path))
        self.assertEqual(written.returncode, 0, written.stdout + written.stderr)
        text = path.read_text(encoding="utf-8")
        self.assertIn("| 0 | Ground work | 1 | 2 | 50% |", text)
        self.assertIn("| 1 | Protection | 1 | 1 | 100% |", text)
        self.assertIn("| **All phases** | **Readiness total** | **2** | **3** | **67%** |", text)
        self.assertIn("| Gates | G1 to G2 | 1 | 2 | 50% |", text)
        self.assertEqual(self.run_progress("--check", str(path)).returncode, 0)

    def test_write_mode_leaves_the_rest_of_the_file_alone(self) -> None:
        path = self.roadmap()
        self.run_progress(str(path))
        text = path.read_text(encoding="utf-8")
        self.assertIn("Last updated: 2026-11-02T00:00Z (seed)", text)
        self.assertIn("## Gates", text)
        self.assertEqual(text.count(START), 1)
        self.assertEqual(text.count(END), 1)

    def test_check_on_an_empty_table_prints_the_one_that_is_right(self) -> None:
        path = self.roadmap()
        done = self.run_progress("--check", str(path))
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn("disagrees with its own task lines", done.stderr)
        self.assertIn("run scripts/roadmap_progress.py without --check", done.stderr)
        self.assertIn("| 0 | Ground work | 1 | 2 | 50% |", done.stdout)

    def test_half_done_marker_counts_as_unfinished(self) -> None:
        path = self.roadmap(phases=(("### Phase 0: Ground work", ("- [~] **0.1** Half landed.",)),))
        self.run_progress(str(path))
        self.assertIn("| 0 | Ground work | 0 | 1 | 0% |", path.read_text(encoding="utf-8"))

    def test_gates_are_counted_apart_from_the_readiness_sum(self) -> None:
        path = self.roadmap(gates=("- [x] **G1** CI is green.",))
        self.run_progress(str(path))
        text = path.read_text(encoding="utf-8")
        self.assertIn("| Gates | G1 to G1 | 1 | 1 | 100% |", text)
        self.assertIn("| **All phases** | **Readiness total** | **2** | **3** | **67%** |", text)

    def test_a_roadmap_with_no_gate_lines_renders_instead_of_crashing(self) -> None:
        """Found by the suite, not by reading: an empty gates list divided by zero.

        The progress script is the gate, so a roadmap whose gates have not been written
        yet has to fail the build with a table rather than crash on a line of arithmetic.
        """
        path = self.roadmap(gates=())
        done = self.run_progress(str(path))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertNotIn("Traceback", done.stderr)
        text = path.read_text(encoding="utf-8")
        self.assertIn("| Gates | Gates | 0 | 0 | 0% |", text)
        self.assertIn("| **All phases** | **Readiness total** | **2** | **3** | **67%** |", text)

    def test_missing_progress_block_is_a_sentence_not_a_traceback(self) -> None:
        path = self.roadmap(markers=False)
        reason = f"the file has no {START} ... {END} block"
        for args in ([str(path)], ["--check", str(path)]):
            self.assert_clean_error(self.run_progress(*args), reason)

    def test_phase_heading_with_no_tasks_is_a_sentence_not_a_traceback(self) -> None:
        filled = ("### Phase 0: Ground work", ("- [x] **0.1** First task.",))
        empty = ("### Phase 2: Empty", ())
        path = self.roadmap(phases=(filled, empty))
        reason = "Phase 2 has a heading and no task lines"
        for args in ([str(path)], ["--check", str(path)]):
            self.assert_clean_error(self.run_progress(*args), reason)

    def test_tasks_under_no_heading_is_a_sentence_not_a_traceback(self) -> None:
        path = self.roadmap(phases=())
        done = self.run_progress("--check", str(path))
        self.assert_clean_error(done, "no `### Phase N:` heading to count tasks under")

    def test_the_default_path_is_this_repository_and_check_never_writes(self) -> None:
        """Run from anywhere with no argument and the script reads the tracked roadmap."""
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        before = (REPO / "ROADMAP.md").read_text(encoding="utf-8")
        done = subprocess.run(
            [sys.executable, str(PROGRESS), "--check"],
            capture_output=True,
            text=True,
            cwd=elsewhere,
            env=self.env,
        )
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(before, (REPO / "ROADMAP.md").read_text(encoding="utf-8"))


class TouchedGate(Scratch):
    """`scripts/check_roadmap_touched.sh` against a git repository built per case."""

    def setUp(self) -> None:
        super().setUp()
        self.roadmap()
        self.git("init", "-q", "-b", "main", ".")
        self.git("add", "ROADMAP.md")
        self.git(*IDENTITY, "commit", "-q", "-m", "seed main")

    def branch(self, name: str = "feat/gate-self-test") -> None:
        self.git("checkout", "-q", "-b", name)

    def edit_roadmap(self, *, touch_last_updated: bool = True) -> None:
        path = self.root / "ROADMAP.md"
        text = path.read_text(encoding="utf-8")
        text = text.replace("- [ ] **0.2** Second task.", "- [x] **0.2** Second task.", 1)
        if touch_last_updated:
            text = re.sub(
                r"^Last updated: .*$",
                "Last updated: 2026-11-03T00:00Z (0.2 done)",
                text,
                count=1,
                flags=re.MULTILINE,
            )
        path.write_text(text, encoding="utf-8")

    def commit(self, message: str) -> None:
        self.git("add", "--all")
        self.git(*IDENTITY, "commit", "-q", "-m", message)

    def test_a_branch_that_edits_the_roadmap_passes_the_gate_it_is_adding(self) -> None:
        self.branch()
        self.edit_roadmap()
        self.commit("docs: tick 0.2")
        done = self.run_touched("main")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("Last updated: 2026-11-03T00:00Z (0.2 done)", done.stdout)

    def test_passes_when_invoked_from_a_subdirectory_of_the_repository(self) -> None:
        self.branch()
        self.edit_roadmap()
        self.commit("docs: tick 0.2 from a subdirectory")
        nested = self.root / "corpus" / "account"
        nested.mkdir(parents=True)
        done = self.run_touched("main", cwd=nested)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_code_without_a_roadmap_edit_is_refused(self) -> None:
        self.branch()
        (self.root / "note.txt").write_text("a change that forgot the roadmap\n", encoding="utf-8")
        self.commit("feat: forgot")
        done = self.run_touched("main")
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn("ROADMAP.md must be updated in the same pull request", done.stderr)
        self.assertIn("note.txt", done.stderr)

    def test_roadmap_edited_but_the_date_left_alone_is_refused(self) -> None:
        self.branch()
        self.edit_roadmap(touch_last_updated=False)
        self.commit("docs: ticked without dating")
        done = self.run_touched("main")
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn("changed but 'Last updated' did not", done.stderr)

    def test_roadmap_with_no_last_updated_line_is_refused(self) -> None:
        self.branch()
        path = self.root / "ROADMAP.md"
        text = path.read_text(encoding="utf-8")
        stripped = re.sub(r"^Last updated: .*$", "", text, count=1, flags=re.MULTILINE)
        path.write_text(stripped, encoding="utf-8")
        self.commit("docs: deleted the date line")
        done = self.run_touched("main")
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn("has no 'Last updated' line", done.stderr)

    def test_a_base_that_was_never_fetched_is_reported_not_crashed(self) -> None:
        self.branch()
        self.edit_roadmap()
        self.commit("docs: against a base nobody fetched")
        done = self.run_touched("origin/nope")
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn("'origin/nope' is not available", done.stderr)
        self.assertNotIn("Traceback", done.stderr)

    def test_nothing_changed_against_the_base_has_nothing_to_enforce(self) -> None:
        done = self.run_touched("main")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("nothing changed against main", done.stdout)

    def test_the_base_default_is_read_from_the_workflow_environment(self) -> None:
        """No argument means `GITHUB_BASE_REF`, which is how the workflow invokes it."""
        self.branch()
        self.edit_roadmap()
        self.commit("docs: rely on the workflow's base ref")
        self.env["GITHUB_BASE_REF"] = "main"
        done = self.run_touched()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
