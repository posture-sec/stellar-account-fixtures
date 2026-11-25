#!/usr/bin/env python3
"""Hold ``validate.py`` to a stdout, stderr and exit-code contract.

``main`` in ``validate.py`` prints report lines and the success sentence to stdout,
problem lines and the summary count to stderr, and exits 0, 1 or 2. That split is what
a consumer's wrapper reads: stdout is parsed, stderr is logged. The tests below drive
the real CLI as a subprocess over staged corpora, one per exit code, and assert the
streams rather than trusting the source to keep them apart.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import validate  # noqa: E402

VALIDATE = REPO_ROOT / "validate.py"
FIXTURE_ID = "plain"
WHERE = f"fixtures/{FIXTURE_ID}"
SUCCESS_LINE = "validate: corpus agrees with itself"

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"


def valid_account_id() -> str:
    body = bytes([validate.VERSION_ACCOUNT]) + bytes(range(32))
    raw = body + validate.crc16_xmodm(body).to_bytes(2, "little")
    bits = int.from_bytes(raw, "big")
    return "".join(ALPHABET[(bits >> (5 * (55 - index))) & 0x1F] for index in range(56))


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATE), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def write_root_public(corpus_dir: Path) -> None:
    """Write the public root document and the sha256 sidecar validate.py requires."""
    document = json.dumps({"network_passphrase": validate.NETWORKS["public"][1]}) + "\n"
    path = corpus_dir / "root-public.json"
    path.write_text(document, encoding="utf-8")
    digest = hashlib.sha256(document.encode("utf-8")).hexdigest()
    (corpus_dir / "root-public.toml").write_text(
        'url = "https://horizon.stellar.org/"\n'
        'captured_at = "2026-11-25T00:00:00Z"\n'
        f'sha256 = "{digest}"\n',
        encoding="utf-8",
    )


class ValidateCliContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.stage = tempfile.TemporaryDirectory(prefix="cli-contract-test-")
        self.addCleanup(self.stage.cleanup)
        self.root = Path(self.stage.name) / "corpus"
        self.account_id = valid_account_id()
        self.account: dict[str, object] = {
            "account_id": self.account_id,
            "sequence": "1",
            "balances": [],
            "signers": [{"key": self.account_id, "weight": 1}],
            "thresholds": {"low_threshold": 0, "med_threshold": 0, "high_threshold": 0},
            "flags": {},
        }
        self.fixture_dir = self.root / "fixtures" / FIXTURE_ID
        self.fixture_dir.mkdir(parents=True)
        (self.fixture_dir / "account.json").write_bytes(
            (json.dumps(self.account, indent=2, sort_keys=True) + "\n").encode("utf-8")
        )
        labels = "".join(f'  "{label}",\n' for label in sorted(validate.shapes_of(self.account)))
        (self.fixture_dir / "fixture.toml").write_text(
            "schema_version = 1\n"
            f'id = "{FIXTURE_ID}"\n'
            'kind = "synthetic"\n'
            'scenario = "synthetic: a fixture used to read the command line back"\n'
            f'account_id = "{self.account_id}"\n'
            'network = "public"\n'
            "shape = [\n"
            f"{labels}"
            "]\n",
            encoding="utf-8",
        )
        (self.root / "corpus").mkdir()
        write_root_public(self.root / "corpus")

    def assert_no_traceback(self, result: subprocess.CompletedProcess[str]) -> None:
        for stream, text in (("stdout", result.stdout), ("stderr", result.stderr)):
            self.assertNotIn("Traceback (most recent call last)", text, f"traceback on {stream}")

    def test_success_exits_zero_and_writes_only_stdout(self) -> None:
        result = run("--root", str(self.root))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, SUCCESS_LINE + "\n")
        self.assertEqual(result.stderr, "")
        self.assert_no_traceback(result)

    def test_report_lines_go_to_stdout_and_stderr_stays_empty(self) -> None:
        result = run("--root", str(self.root), "--report")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertTrue(result.stdout.startswith(f"{WHERE}: "), result.stdout)
        self.assertIn(SUCCESS_LINE, result.stdout)
        self.assert_no_traceback(result)

    def test_a_problem_exits_one_and_writes_only_stderr(self) -> None:
        (self.fixture_dir / "notes.txt").write_text("stray\n", encoding="utf-8")

        result = run("--root", str(self.root))

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn(f"{WHERE}: unexpected file(s): notes.txt", result.stderr)
        self.assertIn(f"validate: 1 problem(s) in {self.root.resolve()}", result.stderr)
        self.assertNotIn("unexpected file", result.stdout)
        self.assertNotIn("problem(s) in", result.stdout)
        self.assert_no_traceback(result)

    def test_a_report_and_a_problem_share_no_stream_content(self) -> None:
        (self.fixture_dir / "notes.txt").write_text("stray\n", encoding="utf-8")

        result = run("--root", str(self.root), "--report")

        self.assertEqual(result.returncode, 1)
        self.assertTrue(result.stdout.startswith(f"{WHERE}: "), result.stdout)
        self.assertNotIn("unexpected file", result.stdout)
        self.assertNotIn("problem(s)", result.stdout)
        self.assertIn("unexpected file", result.stderr)
        self.assertNotIn(SUCCESS_LINE, result.stderr)
        self.assert_no_traceback(result)

    def test_a_root_without_fixtures_exits_two(self) -> None:
        empty = Path(self.stage.name) / "empty"
        empty.mkdir()

        result = run("--root", str(empty))

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn(f"validate: no readable corpus at {empty.resolve()}", result.stderr)
        self.assert_no_traceback(result)

    def test_the_shipped_corpus_exits_zero_from_the_command_line(self) -> None:
        result = run()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, SUCCESS_LINE + "\n")
        self.assertEqual(result.stderr, "")
        self.assert_no_traceback(result)

    def test_a_missing_root_argument_directory_exits_two(self) -> None:
        absent = Path(self.stage.name) / "does-not-exist"

        result = run("--root", str(absent))

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assert_no_traceback(result)


if __name__ == "__main__":
    unittest.main()
