#!/usr/bin/env python3
"""Ensure README sync fails rather than publishing test counts after discovery errors."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SYNC_README = REPO_ROOT / "scripts" / "sync_readme.py"


class ReadmeTestCountFallbackTest(unittest.TestCase):
    def run_sync_with_failure(
        self, *, failing_test_validate: bool
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory(prefix="readme-test-count-") as tmp_dir:
            root = Path(tmp_dir)
            scripts = root / "scripts"
            tests = root / "tests"
            data = root / "site" / "data"
            scripts.mkdir()
            tests.mkdir()
            data.mkdir(parents=True)
            shutil.copyfile(SYNC_README, scripts / "sync_readme.py")

            if failing_test_validate:
                (root / "test_validate.py").write_text(
                    'raise ImportError("broken test_validate dependency")\n', encoding="utf-8"
                )
            else:
                (root / "test_validate.py").write_text("import unittest\n", encoding="utf-8")
                (tests / "test_broken_import.py").write_text(
                    'raise ImportError("broken discovered test dependency")\n', encoding="utf-8"
                )

            readme = root / "README.md"
            readme.write_text("README must remain unchanged\n", encoding="utf-8")
            test_badge = data / "badge-tests.json"
            test_badge.write_text("badge must remain unchanged\n", encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(scripts / "sync_readme.py"), "--check"],
                capture_output=True,
                text=True,
                cwd=root,
                check=False,
            )

            self.assertEqual(readme.read_text(encoding="utf-8"), "README must remain unchanged\n")
            self.assertEqual(
                test_badge.read_text(encoding="utf-8"), "badge must remain unchanged\n"
            )
            return result

    def test_test_validate_import_error_fails_without_writing(self) -> None:
        result = self.run_sync_with_failure(failing_test_validate=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("broken test_validate dependency", result.stderr)

    def test_discovered_test_import_error_fails_without_writing(self) -> None:
        result = self.run_sync_with_failure(failing_test_validate=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("test discovery failed", result.stderr)
        self.assertIn("broken discovered test dependency", result.stderr)

    def test_zero_em_dashes(self) -> None:
        content = Path(__file__).read_text(encoding="utf-8")
        self.assertNotIn("\u2014", content)


if __name__ == "__main__":
    unittest.main()
