#!/usr/bin/env python3
"""Keep documented capture command flags in sync with tools/capture.py."""

from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_PATHS = (
    REPO_ROOT / "CONTRIBUTING.md",
    REPO_ROOT / "README.md",
    REPO_ROOT / "docs" / "WAVE_SUBMISSION.md",
)
CODE_BLOCK = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)
CLI_FLAG = re.compile(r"(?<![\w-])--[a-z][a-z0-9-]*")


def argparse_options() -> set[str]:
    tree = ast.parse((REPO_ROOT / "tools" / "capture.py").read_text(encoding="utf-8"))
    options: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "add_argument":
            continue
        options.update(
            argument.value
            for argument in node.args
            if isinstance(argument, ast.Constant)
            and isinstance(argument.value, str)
            and argument.value.startswith("--")
        )
    return options


def documented_capture_options() -> set[str]:
    options: set[str] = set()
    for doc_path in DOC_PATHS:
        content = doc_path.read_text(encoding="utf-8")
        for block in CODE_BLOCK.findall(content):
            lines = block.splitlines()
            for index, line in enumerate(lines):
                if "tools/capture.py" not in line:
                    continue
                command = line
                while command.rstrip().endswith("\\") and index + 1 < len(lines):
                    index += 1
                    command += f" {lines[index].strip()}"
                options.update(CLI_FLAG.findall(command))
    return options


class DocsCaptureFlagsTest(unittest.TestCase):
    def test_documented_capture_flags_match_argparse(self) -> None:
        self.assertEqual(documented_capture_options(), argparse_options())

    def test_root_and_update_are_documented_in_contributing(self) -> None:
        content = (REPO_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        contributing_commands = {
            flag
            for block in CODE_BLOCK.findall(content)
            if "tools/capture.py" in block
            for flag in CLI_FLAG.findall(block)
        }

        self.assertIn("--root", contributing_commands)
        self.assertIn("--update", contributing_commands)


if __name__ == "__main__":
    unittest.main()
