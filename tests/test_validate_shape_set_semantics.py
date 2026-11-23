#!/usr/bin/env python3
"""Pin set-based shape comparison semantics in validate.py."""

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


class ValidateShapeSetSemanticsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.stage = tempfile.TemporaryDirectory(prefix="shape-set-semantics-test-")
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

    def test_unsorted_shape_list_validates_cleanly_under_check_captured(self) -> None:
        derived = sorted(validate.shapes_of(self.account))
        unsorted_shapes = list(reversed(derived))
        self.assertNotEqual(derived, unsorted_shapes)

        sidecar = {
            "id": "plain",
            "kind": "captured",
            "shape": unsorted_shapes,
        }

        corpus = validate.Corpus(self.root)
        validate.check_captured(corpus, WHERE, sidecar, self.body_file, self.account)
        self.assertFalse(
            any("shape" in p for p in corpus.problems),
            f"Unexpected shape problems found: {corpus.problems}",
        )

    def test_duplicate_shape_labels_in_data_pass_check_captured_set_comparison(self) -> None:
        derived = sorted(validate.shapes_of(self.account))
        # Adding a duplicate label to the shape list
        duplicate_shapes = [*derived, derived[0]]
        self.assertEqual(len(duplicate_shapes), len(derived) + 1)

        sidecar = {
            "id": "plain",
            "kind": "captured",
            "shape": duplicate_shapes,
        }

        corpus = validate.Corpus(self.root)
        validate.check_captured(corpus, WHERE, sidecar, self.body_file, self.account)
        # Because check_captured converts data['shape'] into a set, no shape mismatch occurs
        self.assertFalse(
            any("shape" in p for p in corpus.problems),
            f"Unexpected shape problems found: {corpus.problems}",
        )


if __name__ == "__main__":
    unittest.main()
