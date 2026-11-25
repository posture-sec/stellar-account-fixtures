#!/usr/bin/env python3
"""Contract test for corpus/account-links.md (issue #40).

The document makes checkable statements about `_links`: which relations every capture
carries, that the links differ between captures only by host and account id, and that the
public and testnet examples are what the files say. This test reads each one back from the
fixtures, and pins the evidence the document points at in the sidecar.
"""

from __future__ import annotations

import json
import re
import sys
import tomllib
import unittest
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import validate  # noqa: E402

DOC_PATH = REPO_ROOT / "corpus" / "account-links.md"
FIXTURES_DIR = REPO_ROOT / "fixtures"
EM_DASH = chr(0x2014)
RELATION_ROW = re.compile(r"^\| `([a-z]+)` \| `([^`]+)` \| (yes|no) \|$")


def all_fixture_ids() -> list[str]:
    return sorted(p.name for p in FIXTURES_DIR.iterdir() if p.is_dir())


def fixture_kind(fixture_id: str) -> str:
    sidecar = tomllib.loads((FIXTURES_DIR / fixture_id / "fixture.toml").read_text("utf-8"))
    return str(sidecar["kind"])


def fixture_ids() -> list[str]:
    """The captured fixtures: the ones with a source_url and the links Horizon wrote."""
    return [name for name in all_fixture_ids() if fixture_kind(name) == "captured"]


def load(fixture_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    account = json.loads((FIXTURES_DIR / fixture_id / "account.json").read_text("utf-8"))
    sidecar = tomllib.loads((FIXTURES_DIR / fixture_id / "fixture.toml").read_text("utf-8"))
    return account, sidecar


def normalised(fixture_id: str) -> dict[str, tuple[str, object]]:
    account, sidecar = load(fixture_id)
    host = str(sidecar["source_url"]).split("/accounts/")[0]
    links = account["_links"]
    return {
        name: (
            str(link["href"]).replace(host, "HOST").replace(str(account["id"]), "ID"),
            link.get("templated"),
        )
        for name, link in links.items()
    }


class CorpusAccountLinksTest(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(DOC_PATH.is_file(), f"{DOC_PATH} does not exist")
        self.content = DOC_PATH.read_text(encoding="utf-8")

    def test_zero_em_dashes(self) -> None:
        self.assertNotIn(EM_DASH, self.content)

    def test_capture_count_in_the_text_matches_the_corpus(self) -> None:
        words = {10: "ten", 11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen"}
        captured = len(fixture_ids())
        self.assertIn(f"All {words[captured]} captures carry", self.content)
        self.assertIn(f"all {words[captured]} captured files", self.content)

    def test_synthetic_fixtures_carry_no_links(self) -> None:
        synthetic = [name for name in all_fixture_ids() if fixture_kind(name) == "synthetic"]
        self.assertIn("null-home-domain", synthetic)
        for fixture_id in synthetic:
            account, _ = load(fixture_id)
            self.assertNotIn("_links", account, fixture_id)
        self.assertIn("`null-home-domain`, is synthetic", self.content)

    def test_relation_table_matches_every_capture(self) -> None:
        documented = {}
        for line in self.content.splitlines():
            match = RELATION_ROW.match(line)
            if match:
                documented[match.group(1)] = (match.group(2), match.group(3) == "yes")
        self.assertEqual(len(documented), 8)

        for fixture_id in fixture_ids():
            links = normalised(fixture_id)
            self.assertEqual(set(links), set(documented), fixture_id)
            for name, (href, templated) in links.items():
                pattern, doc_templated = documented[name]
                self.assertEqual(href, "HOST" + pattern.replace("<account-id>", "ID"), name)
                self.assertEqual(bool(templated), doc_templated, f"{fixture_id}: {name}")

    def test_links_are_identical_across_captures_apart_from_host_and_id(self) -> None:
        reference = normalised(fixture_ids()[0])
        for fixture_id in fixture_ids():
            self.assertEqual(normalised(fixture_id), reference, fixture_id)

    def test_every_href_uses_the_host_in_source_url(self) -> None:
        for fixture_id in fixture_ids():
            account, sidecar = load(fixture_id)
            host = str(sidecar["source_url"]).split("/accounts/")[0]
            links = account["_links"]
            for name, link in links.items():
                self.assertTrue(str(link["href"]).startswith(host + "/"), f"{fixture_id}: {name}")

    def test_self_link_equals_source_url(self) -> None:
        for fixture_id in fixture_ids():
            account, sidecar = load(fixture_id)
            links = account["_links"]
            self.assertEqual(links["self"]["href"], sidecar["source_url"], fixture_id)

    def test_public_and_testnet_examples_match_the_files(self) -> None:
        for fixture_id, network in (("default-plain", "public"), ("testnet-multisig", "testnet")):
            account, sidecar = load(fixture_id)
            self.assertEqual(sidecar["network"], network)
            self.assertIn(f"`{sidecar['source_url']}`", self.content, fixture_id)
            self.assertIn(f"`{sidecar['network']}`", self.content, fixture_id)

            host = str(sidecar["source_url"]).split("/accounts/")[0]
            short = str(account["id"])[:4] + "..."
            self.assertIn(
                f"`{host}/accounts/{short}/transactions{{?cursor,limit,order}}`", self.content
            )

    def test_cited_sidecar_line_is_the_source_url(self) -> None:
        self.assertIn("`fixture.toml` line 8", self.content)
        path = FIXTURES_DIR / "testnet-multisig" / "fixture.toml"
        line = path.read_text(encoding="utf-8").splitlines()[7]
        self.assertTrue(line.startswith("source_url = "), line)

    def test_states_that_the_validator_checks_the_sidecar_not_links(self) -> None:
        # The claim in the document is about this commit. If validate.py ever starts to
        # read `_links`, this test is the reminder to rewrite section 2 of the document.
        source = (REPO_ROOT / "validate.py").read_text(encoding="utf-8")
        capture_source = (REPO_ROOT / "tools" / "capture.py").read_text(encoding="utf-8")
        self.assertNotIn("_links", source)
        self.assertNotIn("_links", capture_source)
        self.assertIn("is not checked by the validator", self.content)
        self.assertTrue(callable(validate.validate))

    def test_names_the_evidence_it_points_to(self) -> None:
        for name in (
            "source_url",
            "network_passphrase",
            "sha256",
            "captured_at",
            "horizon_version",
        ):
            self.assertIn(name, self.content)
        schema = (REPO_ROOT / "SCHEMA.md").read_text(encoding="utf-8")
        self.assertIn("## 2. account.json", schema)
        self.assertIn("## 3. fixture.toml", schema)

    def test_relative_links_resolve(self) -> None:
        for target in re.findall(r"\]\((?!https?:)([^)#]+)(?:#[^)]*)?\)", self.content):
            self.assertTrue((DOC_PATH.parent / target).exists(), f"broken link: {target}")


if __name__ == "__main__":
    unittest.main()
