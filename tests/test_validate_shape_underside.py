#!/usr/bin/env python3
"""Report shape labels that the account bytes show but the sidecar omits."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import validate  # noqa: E402

WHERE = "fixtures/plain"


class ValidateShapeUndersideTest(unittest.TestCase):
    def setUp(self) -> None:
        self.stage = tempfile.TemporaryDirectory(prefix="shape-underside-test-")
        self.addCleanup(self.stage.cleanup)
        self.root = Path(self.stage.name)
        self.account_id = "G" + "A" * 55
        self.account: dict[str, object] = {
            "account_id": self.account_id,
            "sequence": "1",
            "balances": [],
            "signers": [{"key": self.account_id, "weight": 1}],
            "thresholds": {"low_threshold": 0, "med_threshold": 0, "high_threshold": 0},
            "flags": {},
        }
        self.body_bytes = (json.dumps(self.account, indent=2, sort_keys=True) + "\n").encode()
        self.body_file = self.root / "account.json"
        self.body_file.write_bytes(self.body_bytes)

    def test_captured_omitted_shape_reports_exact_message(self) -> None:
        derived = sorted(validate.shapes_of(self.account))
        self.assertIn("no_data", derived)
        omitted = [s for s in derived if s != "no_data"]

        sidecar = {
            "id": "plain",
            "kind": "captured",
            "shape": omitted,
        }

        corpus = validate.Corpus(self.root)
        validate.check_captured(corpus, WHERE, sidecar, self.body_file, self.account)

        expected = "account.json shows shape 'no_data' which sidecar omits"
        self.assertTrue(
            any(expected in p for p in corpus.problems),
            f"Expected error message {expected!r} not found in {corpus.problems}",
        )

    def test_synthetic_omitted_shape_reports_exact_message(self) -> None:
        derived = sorted(validate.shapes_of(self.account))
        self.assertIn("no_balances", derived)
        omitted = [s for s in derived if s != "no_balances"]

        sidecar = {
            "id": "plain",
            "kind": "synthetic",
            "shape": omitted,
        }

        corpus = validate.Corpus(self.root)
        validate.check_synthetic(corpus, WHERE, sidecar, self.account)

        expected = "account.json shows shape 'no_balances' which sidecar omits"
        self.assertTrue(
            any(expected in p for p in corpus.problems),
            f"Expected error message {expected!r} not found in {corpus.problems}",
        )

    def test_exact_shapes_produce_no_underside_error(self) -> None:
        derived = sorted(validate.shapes_of(self.account))
        sidecar = {
            "id": "plain",
            "kind": "captured",
            "shape": derived,
        }

        corpus = validate.Corpus(self.root)
        validate.check_captured(corpus, WHERE, sidecar, self.body_file, self.account)
        self.assertFalse(any("which sidecar omits" in p for p in corpus.problems))


if __name__ == "__main__":
    unittest.main()
