#!/usr/bin/env python3
"""Contract tests for validate.py CLI exit codes (issue #62).

Pins the three documented exit codes:
- 0: clean validation against a valid corpus
- 1: validation problems encountered (including unknown sidecar keys)
- 2: unreadable corpus root or missing fixtures directory
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import validate  # noqa: E402


class ValidateExitCodesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.root = Path(self.temp_dir)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_exit_0_on_clean_corpus(self) -> None:
        exit_code = validate.main(["--root", str(REPO_ROOT)])
        self.assertEqual(exit_code, 0)

    def test_exit_2_on_nonexistent_directory(self) -> None:
        nonexistent = self.root / "does_not_exist"
        exit_code = validate.main(["--root", str(nonexistent)])
        self.assertEqual(exit_code, 2)

    def test_exit_2_on_missing_fixtures_directory(self) -> None:
        empty_dir = self.root / "empty_corpus"
        empty_dir.mkdir(parents=True)
        exit_code = validate.main(["--root", str(empty_dir)])
        self.assertEqual(exit_code, 2)

    def test_exit_1_on_validation_problem(self) -> None:
        fixtures_dir = self.root / "fixtures"
        fixture_subdir = fixtures_dir / "broken-fixture"
        fixture_subdir.mkdir(parents=True)

        (fixture_subdir / "account.json").write_text("{}", encoding="utf-8")
        (fixture_subdir / "fixture.toml").write_text("invalid toml syntax [[", encoding="utf-8")

        exit_code = validate.main(["--root", str(self.root)])
        self.assertEqual(exit_code, 1)

    def test_exit_1_on_unknown_sidecar_keys(self) -> None:
        # Note on docstring divergence: the module docstring mentions exit 2 for
        # unreadable corpus, while unknown sidecar keys are handled in check_captured
        # or check_common as standard corpus problems, returning exit 1.
        corpus_dir = self.root / "corpus"
        corpus_dir.mkdir(parents=True)
        for net, (_, passphrase) in validate.NETWORKS.items():
            (corpus_dir / f"root-{net}.json").write_text(
                json.dumps({"network_passphrase": passphrase}) + "\n",
                encoding="utf-8",
            )

        fixtures_dir = self.root / "fixtures"
        fixture_subdir = fixtures_dir / "unknown-key-specimen"
        fixture_subdir.mkdir(parents=True)

        acc_id = "GA7DTK7GPOEQGXHI7MLA2OAIEL4365VG6PXUAVREMDVLC4MJIJ62KR75"
        account_data = {
            "account_id": acc_id,
            "signers": [{"key": acc_id, "weight": 1}],
            "thresholds": {"low_threshold": 0, "med_threshold": 0, "high_threshold": 0},
            "balances": [{"asset_type": "native", "balance": "100.0"}],
        }
        body = json.dumps(account_data, indent=2, sort_keys=True) + "\n"
        (fixture_subdir / "account.json").write_text(body, encoding="utf-8")

        sidecar_text = (
            "schema_version = 1\n"
            'id = "unknown-key-specimen"\n'
            'kind = "synthetic"\n'
            'scenario = "synthetic: specimen with unexpected sidecar field"\n'
            f'account_id = "{acc_id}"\n'
            'network = "public"\n'
            'shape = ["master_is_signer", "no_data", "no_home_domain", '
            '"no_inflation", "not_sponsored", "not_sponsoring", '
            '"single_signer", "thresholds_zero"]\n'
            'unexpected_custom_key = "forbidden"\n'
        )
        (fixture_subdir / "fixture.toml").write_text(sidecar_text, encoding="utf-8")

        exit_code = validate.main(["--root", str(self.root)])
        self.assertEqual(exit_code, 1)

    def test_zero_em_dashes(self) -> None:
        content = Path(__file__).read_text(encoding="utf-8")
        self.assertNotIn("\u2014", content)
        self.assertNotIn("\u2013", content)


if __name__ == "__main__":
    unittest.main()
