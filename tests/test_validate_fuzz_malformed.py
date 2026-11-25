#!/usr/bin/env python3
"""Seeded fuzzing of fixture.toml and account.json: validate() reports, it never crashes.

load_manifest and validate_fixture read the two files of every fixture. A corrupted disk, a
bad checkout or a hand edit can hand them anything, and an exception that escapes validate()
turns a structured problem list into a traceback for every CI job and consumer that runs it.

The cases below are generated from one fixed seed with the standard library's `random`, so
a failure names a case that reproduces on every run. Each case corrupts one file of a single
shipped fixture in a scratch corpus and asserts that validate() returns, that every problem is
a `fixtures/<id>: message` line, and, for every strategy that cannot leave the fixture valid,
that there is at least one. A digit flip can land somewhere harmless (a ledger digit, the
seconds of `captured_at`), so that strategy only asserts that nothing escapes.

Running this fuzzer found three escapes, now reported as problems: a deeply nested
account.json or fixture.toml raised RecursionError on Python 3.11 and 3.12, and a digit flip
that made `captured_at` an impossible date (month 19, day 32, year 0000) raised ValueError
out of strptime.
"""

from __future__ import annotations

import hashlib
import io
import random
import shutil
import sys
import tempfile
import unittest
from collections.abc import Callable
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import validate  # noqa: E402

SEED = 20261121
CASES_PER_STRATEGY = 25
FIXTURE_ID = "default-plain"
WHERE = f"fixtures/{FIXTURE_ID}: "
FILES = ("fixture.toml", "account.json")
# Deep enough for RecursionError everywhere it happens: the 3.12 C decoder needs about
# 8,000 levels, tomllib far fewer, and 3.15 no longer recurses for JSON at all.
DEPTH = 20_000

# Bytes that cannot appear anywhere in a valid sidecar: C0 controls other than tab and
# newline (TOML forbids them in keys, strings and comments; a CR is the CRLF problem), DEL,
# continuation bytes, and the bytes UTF-8 never uses. Lead bytes 0xC2 to 0xF4 are left out
# on purpose: two of these mutations side by side must not be able to spell a valid
# character, or a corrupted sidecar could still pass.
HOSTILE = bytes(
    [*range(0x00, 0x09), *range(0x0B, 0x20), 0x7F, *range(0x80, 0xC2), *range(0xF5, 0x100)]
)
INVALID_UTF8 = (
    b"\xff",
    b"\xfe\xff",
    b"\xc3(",
    b"\xe2\x28\xa1",
    b"\xed\xa0\x80",
    b"\xf0\x28\x8c\xbc",
    b"\xf8\x88\x80\x80\x80",
    b"\xc0\xaf",
)
SCALARS = (b"", b"\n", b"1\n", b"-0.5\n", b"null\n", b"true\n", b'"text"\n', b"[]\n", b"[1, 2]\n")
NESTED = (
    b"[" * DEPTH,
    b"[" * DEPTH + b"]" * DEPTH + b"\n",
    b'{"a":' * DEPTH,
    b"a = " + b"[" * DEPTH,
    b"a = " + b"[" * DEPTH + b"]" * DEPTH + b"\n",
    b"a = " + b"{b = " * DEPTH,
)


def hostile_bytes(rng: random.Random, original: bytes) -> bytes:
    mutated = bytearray(original)
    for _ in range(rng.randint(1, 4)):
        mutated[rng.randrange(len(mutated))] = rng.choice(HOSTILE)
    return bytes(mutated)


def invalid_utf8(rng: random.Random, original: bytes) -> bytes:
    at = rng.randrange(len(original) + 1)
    return original[:at] + rng.choice(INVALID_UTF8) + original[at:]


def truncated(rng: random.Random, original: bytes) -> bytes:
    return original[: rng.randrange(len(original))]


def digit_flip(rng: random.Random, original: bytes) -> bytes:
    digits = [i for i, byte in enumerate(original) if 0x30 <= byte <= 0x39]
    mutated = bytearray(original)
    for at in rng.sample(digits, rng.randint(1, 2)):
        mutated[at] = rng.choice([d for d in b"0123456789" if d != mutated[at]])
    return bytes(mutated)


Strategy = Callable[[random.Random, bytes], bytes]
# (name, mutator, whether every output must produce at least one problem)
STRATEGIES: tuple[tuple[str, Strategy, bool], ...] = (
    ("hostile bytes", hostile_bytes, True),
    ("invalid UTF-8", invalid_utf8, True),
    ("truncated", truncated, True),
    ("digit flip", digit_flip, False),
)
# Whole-file replacements are a short fixed list, so each one runs once per file instead of
# being drawn at random; they need no seed and every one of them must be refused.
REPLACEMENTS: tuple[tuple[str, tuple[bytes, ...]], ...] = (
    ("scalar document", SCALARS),
    ("deeply nested", NESTED),
)


def generate(originals: dict[str, bytes]) -> list[tuple[str, str, int, bytes, bool]]:
    """Every case as (file, strategy, index, bytes, must_fail), from SEED alone."""
    rng = random.Random(SEED)
    cases = []
    for name in FILES:
        for label, mutate, must_fail in STRATEGIES:
            for index in range(CASES_PER_STRATEGY):
                data = mutate(rng, originals[name])
                cases.append((name, label, index, data, must_fail and data != originals[name]))
        for label, documents in REPLACEMENTS:
            for index, data in enumerate(documents):
                cases.append((name, label, index, data, True))
    return cases


class FuzzMalformedCorpusFiles(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        # One fixture and its root document keep each validate() call small enough for
        # hundreds of cases to run in well under two seconds.
        shutil.copytree(REPO_ROOT / "fixtures" / FIXTURE_ID, self.root / "fixtures" / FIXTURE_ID)
        (self.root / "corpus").mkdir()
        shutil.copy(REPO_ROOT / "corpus" / "root-public.json", self.root / "corpus")
        shutil.copy(REPO_ROOT / "corpus" / "root-public.toml", self.root / "corpus")
        self.directory = self.root / "fixtures" / FIXTURE_ID
        self.originals = {name: (self.directory / name).read_bytes() for name in FILES}

    def run_case(self, name: str, data: bytes) -> list[str]:
        (self.directory / name).write_bytes(data)
        try:
            problems, _ = validate.validate(self.root)
        finally:
            (self.directory / name).write_bytes(self.originals[name])
        return problems

    def assert_structured(self, problems: list[str]) -> None:
        for problem in problems:
            self.assertIsInstance(problem, str)
            self.assertTrue(problem.startswith(WHERE), problem)
            self.assertGreater(len(problem), len(WHERE), problem)

    def test_the_scratch_corpus_starts_clean(self) -> None:
        self.assertEqual(validate.validate(self.root)[0], [])
        # HOSTILE relies on this: with no lead byte in the sidecar, no mutation can complete
        # a multibyte character that was already there.
        self.assertTrue(self.originals["fixture.toml"].isascii())

    def test_cases_are_reproducible_from_the_seed(self) -> None:
        first = generate(self.originals)
        second = generate(self.originals)
        replacements = sum(len(documents) for _, documents in REPLACEMENTS)
        per_file = len(STRATEGIES) * CASES_PER_STRATEGY + replacements
        self.assertEqual(len(first), len(FILES) * per_file)
        digest = hashlib.sha256(b"".join(case[3] for case in first)).hexdigest()
        self.assertEqual(digest, hashlib.sha256(b"".join(case[3] for case in second)).hexdigest())

    def test_every_fuzzed_input_returns_structured_problems(self) -> None:
        date_problems = []
        for name, label, index, data, must_fail in generate(self.originals):
            with self.subTest(file=name, strategy=label, case=index):
                problems = self.run_case(name, data)
                self.assert_structured(problems)
                if must_fail:
                    self.assertNotEqual(problems, [], f"{name} {label} #{index} passed clean")
                date_problems += [p for p in problems if "is not a real UTC date and time" in p]
        # The seed has to keep exercising the strptime path this fuzzer once crashed on.
        self.assertNotEqual(date_problems, [])

    def test_impossible_captured_at_dates_are_problems(self) -> None:
        text = self.originals["fixture.toml"].decode()
        line = next(x for x in text.splitlines() if x.startswith("captured_at = "))
        for stamp in (
            "2026-19-02T11:48:46Z",
            "2026-02-30T00:00:00Z",
            "2026-11-32T00:00:00Z",
            "2026-11-02T24:00:00Z",
            "2026-11-02T11:60:00Z",
            "0000-11-02T11:48:46Z",
        ):
            with self.subTest(captured_at=stamp):
                data = text.replace(line, f'captured_at = "{stamp}"').encode()
                problems = self.run_case("fixture.toml", data)
                self.assertIn(
                    f"{WHERE}captured_at {stamp!r} is not a real UTC date and time", problems
                )

    def test_deep_nesting_is_reported_as_a_parse_failure(self) -> None:
        cases = (
            ("account.json", b"[" * DEPTH + b"]" * DEPTH + b"\n", "account.json is not"),
            ("fixture.toml", b"a = " + b"[" * DEPTH + b"]" * DEPTH + b"\n", "sidecar is not"),
        )
        for name, data, prefix in cases:
            with self.subTest(file=name):
                problems = self.run_case(name, data)
                self.assert_structured(problems)
                self.assertTrue(any(p.startswith(WHERE + prefix) for p in problems), problems)

    def test_main_exits_one_for_corrupted_files(self) -> None:
        for name in FILES:
            for data in (NESTED[0], INVALID_UTF8[0] + self.originals[name]):
                with self.subTest(file=name, head=data[:8]):
                    (self.directory / name).write_bytes(data)
                    stderr = io.StringIO()
                    with redirect_stdout(io.StringIO()), redirect_stderr(stderr):
                        code = validate.main(["--root", str(self.root)])
                    (self.directory / name).write_bytes(self.originals[name])
                    self.assertEqual(code, 1)
                    self.assertIn(WHERE, stderr.getvalue())
                    self.assertNotIn("Traceback", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
