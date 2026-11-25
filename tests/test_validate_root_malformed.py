#!/usr/bin/env python3
"""A malformed corpus/root-<network>.json is a problem on that file, never a traceback.

check_root reads each root document the corpus uses and parses it as JSON. These cases
corrupt one root document in a scratch copy of the shipped corpus and assert that
validate() still returns, that the only problem is a structured `corpus/root-<network>.json:`
line, and that main() exits 1 with that line rather than crashing. json.loads words its
errors differently across Python versions, so a parse failure is matched on the stable
`not JSON: ` prefix and never on the parser's own text.
"""

from __future__ import annotations

import io
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import validate  # noqa: E402

NOT_JSON = "not JSON: "
NOT_OBJECT = "not a JSON object"

# Each row is (label, bytes written as the root document, the problem it must produce).
# NOT_JSON rows match on the prefix only; the others match the whole message.
BYTE_CASES: list[tuple[str, bytes, str]] = [
    ("empty file", b"", NOT_JSON),
    ("whitespace only", b" \n\t\n", NOT_JSON),
    ("truncated object", b'{"network_passphrase": "Public Glo', NOT_JSON),
    ("trailing garbage", b'{"network_passphrase": "x"} }\n', NOT_JSON),
    ("invalid UTF-8 start byte", b"\xff\xfe{}\n", NOT_JSON),
    ("truncated multibyte sequence", b'{"network_passphrase": "\xc3"}\n', NOT_JSON),
    ("lone continuation byte", b'{"horizon_version": "\x80"}\n', NOT_JSON),
    ("deeply nested arrays", b"[" * 100_000, NOT_JSON),
    ("deeply nested objects", b'{"a":' * 100_000, NOT_JSON),
    ("JSON array", b"[]\n", NOT_OBJECT),
    ("array holding the object", b'[{"network_passphrase": "x"}]\n', NOT_OBJECT),
    ("JSON integer", b"7\n", NOT_OBJECT),
    ("JSON float", b"1.5\n", NOT_OBJECT),
    ("JSON string", b'"Public Global Stellar Network ; September 2015"\n', NOT_OBJECT),
    ("JSON null", b"null\n", NOT_OBJECT),
    ("JSON boolean", b"true\n", NOT_OBJECT),
]


class MalformedRootDocument(unittest.TestCase):
    """Every row runs against both networks the shipped corpus uses."""

    networks = ("public", "testnet")

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        shutil.copytree(REPO_ROOT / "fixtures", self.root / "fixtures")
        shutil.copytree(REPO_ROOT / "corpus", self.root / "corpus")

    def root_path(self, network: str) -> Path:
        return self.root / "corpus" / f"root-{network}.json"

    def problems(self) -> list[str]:
        # The point of this suite: anything raised here fails the test with its traceback.
        problems, _ = validate.validate(self.root)
        return problems

    def assert_only_problem(self, network: str, expected: str) -> str:
        problems = self.problems()
        self.assertEqual(len(problems), 1, problems)
        where = f"corpus/root-{network}.json: "
        self.assertTrue(problems[0].startswith(where), problems[0])
        message = problems[0][len(where) :]
        if expected == NOT_JSON:
            self.assertTrue(message.startswith(NOT_JSON), message)
            self.assertNotIn("Traceback", message)
        else:
            self.assertEqual(message, expected)
        return problems[0]

    def test_the_scratch_corpus_starts_clean(self) -> None:
        self.assertEqual(self.problems(), [])
        for network in self.networks:
            self.assertTrue(self.root_path(network).is_file(), network)

    def test_malformed_bytes_are_structured_problems(self) -> None:
        for network in self.networks:
            original = self.root_path(network).read_bytes()
            for label, data, expected in BYTE_CASES:
                with self.subTest(network=network, case=label):
                    self.root_path(network).write_bytes(data)
                    self.assert_only_problem(network, expected)
            self.root_path(network).write_bytes(original)

    def test_a_directory_named_like_the_root_document_is_missing(self) -> None:
        for network in self.networks:
            with self.subTest(network=network):
                path = self.root_path(network)
                original = path.read_bytes()
                path.unlink()
                path.mkdir()
                (path / "network_passphrase").write_text("decoy\n", encoding="utf-8")
                self.assert_only_problem(network, validate.MISSING_ROOT)
                shutil.rmtree(path)
                path.write_bytes(original)

    def test_main_exits_one_with_the_problem_line(self) -> None:
        for label, data, _ in BYTE_CASES:
            with self.subTest(case=label):
                self.root_path("public").write_bytes(data)
                stdout, stderr = io.StringIO(), io.StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    code = validate.main(["--root", str(self.root)])
                self.assertEqual(code, 1)
                self.assertIn("corpus/root-public.json: ", stderr.getvalue())
                self.assertIn("validate: 1 problem(s)", stderr.getvalue())
                self.assertNotIn("Traceback", stderr.getvalue())

    def test_balanced_deep_nesting_does_not_escape(self) -> None:
        """Well-formed but deep: some Pythons raise RecursionError, newer ones parse a list.

        Either way the root is not an object, so the test pins that exactly one structured
        problem comes back and leaves which of the two wordings to the interpreter.
        """
        self.root_path("public").write_bytes(b"[" * 100_000 + b"]" * 100_000 + b"\n")
        problems = self.problems()
        self.assertEqual(len(problems), 1, problems)
        self.assertIn(
            problems[0],
            {
                f"corpus/root-public.json: {NOT_JSON}{validate.TOO_DEEP}",
                f"corpus/root-public.json: {NOT_OBJECT}",
            },
        )


if __name__ == "__main__":
    unittest.main()
