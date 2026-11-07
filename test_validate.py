#!/usr/bin/env python3
"""Tests for validate.py, and for the capture path in tools/capture.py.

Stdlib unittest, no network: every corpus here is a temporary directory, and the
capture tests replace one seam (fetch) with a fake Horizon. The one run that
reads the shipped corpus is the one that proves those fixtures still agree with
their sidecars.

Every address in this file is base32-encoded from fixed bytes at import time and
the one seed-shaped string is encoded from thirty-two zero bytes, so no key
material appears in the source and a real seed cannot be committed by accident.

Run: python3 -m unittest -v test_validate
"""

from __future__ import annotations

import hashlib
import http.server
import json
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import tomllib
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import UTC, datetime, timedelta
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import capture  # noqa: E402

import validate  # noqa: E402
from validate import crc16_xmodm, shapes_of  # noqa: E402

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
ENDPOINT = "https://horizon.stellar.org"
TESTNET = "https://horizon-testnet.stellar.org"
PUBLIC_PASSPHRASE = "Public Global Stellar Network ; September 2015"
TESTNET_PASSPHRASE = "Test SDF Network ; September 2015"
CAPTURED_AT = "2026-11-02T00:00:00Z"
SIDECAR_ORDER = [
    "schema_version",
    "id",
    "kind",
    "scenario",
    "account_id",
    "network",
    "source_url",
    "captured_at",
    "ledger",
    "horizon_version",
    "sha256",
    "shape",
]
PLAIN_SHAPE = [
    "master_is_signer",
    "no_balances",
    "no_data",
    "no_home_domain",
    "no_inflation",
    "not_sponsored",
    "not_sponsoring",
    "single_signer",
    "thresholds_zero",
]


def encode_strkey(version_byte: int, key: bytes) -> str:
    """The mirror of validate.strkey_version: build a strkey from raw bytes."""
    body = bytes([version_byte]) + key
    raw = body + crc16_xmodm(body).to_bytes(2, "little")
    bits = int.from_bytes(raw, "big")
    return "".join(ALPHABET[(bits >> (5 * (55 - i))) & 0x1F] for i in range(56))


ACCOUNT = encode_strkey(48, bytes(range(32)))
PEER = encode_strkey(48, bytes(range(32, 64)))
MED25519 = encode_strkey(96, bytes(range(32)))
ZERO_SEED = encode_strkey(144, bytes(32))
SHAPE_ONLY_SEED = "S" + "Q" * 55


def account_json(**overrides) -> dict:
    """A minimal Horizon account resource: every optional field absent or empty."""
    data = {
        "account_id": ACCOUNT,
        "sequence": "2",
        "signers": [{"key": ACCOUNT, "type": "ed25519_public_key", "weight": 1}],
        "thresholds": {"low_threshold": 0, "med_threshold": 0, "high_threshold": 0},
        "flags": {
            "auth_required": False,
            "auth_revocable": False,
            "auth_immutable": False,
            "auth_clawback_enabled": False,
        },
        "balances": [],
        "data": {},
        "home_domain": None,
        "inflation_destination": None,
        "num_sponsored": 0,
        "num_sponsoring": 0,
        "last_modified_ledger": 65266813,
    }
    data.update(overrides)
    return data


def pretty(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def toml_value(value: object) -> str:
    if isinstance(value, list):
        return "[" + ", ".join(f'"{item}"' for item in value) + "]"
    if isinstance(value, str):
        return f'"{value}"'
    return str(value)


def render_sidecar(*, header: str, **fields) -> str:
    lines = [header]
    for key in SIDECAR_ORDER:
        if key in fields:
            lines.append(f"{key} = {toml_value(fields[key])}")
    for key, value in fields.items():
        if key not in SIDECAR_ORDER:
            lines.append(f"{key} = {toml_value(value)}")
    return "".join(line + "\n" for line in lines)


def root_document(**overrides) -> dict:
    document = {
        "coreversion": "22.2.1",
        "history_latest_ledger": 65266813,
        "horizon_version": "30.0.0",
        "network": "PUBLIC",
        "network_passphrase": PUBLIC_PASSPHRASE,
    }
    document.update(overrides)
    return document


class Fixture:
    """One fixture directory: the account bytes and the sidecar that describes them."""

    def __init__(self, root: Path, name: str) -> None:
        self.root = root
        self.name = name
        self.account = account_json()
        self.fields: dict[str, object] = {}
        self.header = "# Specimen sidecar."
        self._refresh()

    def _refresh(self) -> None:
        account_id = str(self.account["account_id"])
        body = pretty(self.account)
        self.fields = {
            "schema_version": 1,
            "id": self.name,
            "kind": "captured",
            "scenario": "an account whose optional fields are all absent",
            "account_id": account_id,
            "network": "public",
            "source_url": f"{ENDPOINT}/accounts/{account_id}",
            "captured_at": CAPTURED_AT,
            "ledger": int(self.account["last_modified_ledger"]),
            "horizon_version": "22.2.1",
            "sha256": hashlib.sha256(body.encode()).hexdigest(),
            "shape": sorted(shapes_of(self.account)),
        }

    @property
    def directory(self) -> Path:
        return self.root / "fixtures" / self.name

    @property
    def manifest(self) -> Path:
        return self.directory / "fixture.toml"

    @property
    def body(self) -> Path:
        return self.directory / "account.json"

    @property
    def shape(self) -> list[str]:
        """The declared shape labels, for assertions that mypy can follow."""
        value = self.fields["shape"]
        return [str(item) for item in value] if isinstance(value, list) else []

    def manifest_text(self) -> str:
        return render_sidecar(header=self.header, **self.fields)

    def write(self, *, keep=()) -> None:
        """Write the directory, optionally keeping sidecar values from before."""
        held = {key: self.fields[key] for key in keep}
        self._refresh()
        self.fields.update(held)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.body.write_text(pretty(self.account), encoding="utf-8")
        self.manifest.write_text(self.manifest_text(), encoding="utf-8")


class Scratch(unittest.TestCase):
    """A temporary corpus plus the text-level surgery each defect test needs."""

    def setUp(self) -> None:
        stage = tempfile.TemporaryDirectory(prefix="stellar-fixtures-test-")
        self.addCleanup(stage.cleanup)
        self.root = Path(stage.name)
        self.fixtures: dict[str, Fixture] = {}
        self.add_fixture("plain")
        (self.root / "corpus").mkdir()
        (self.root / "corpus" / "root-public.json").write_text(
            pretty(root_document()), encoding="utf-8"
        )

    def add_fixture(self, name: str, **account_overrides) -> Fixture:
        fixture = Fixture(self.root, name)
        fixture.account = account_json(**account_overrides)
        fixture.write()
        self.fixtures[name] = fixture
        return fixture

    def digest(self, name: str = "plain") -> str:
        return hashlib.sha256(self.fixtures[name].body.read_bytes()).hexdigest()

    def problems(self, *, report: bool = False) -> list[str]:
        return sorted(validate.validate(self.root, report)[0])

    def assert_problem(self, fragment: str) -> str:
        hits = [problem for problem in self.problems() if fragment in problem]
        if not hits:
            self.fail(f"nothing reported {fragment!r}; the validator said: {self.problems()}")
        return hits[0]

    def assert_clean(self) -> None:
        self.assertEqual(self.problems(), [])

    def manifest_text(self, name: str = "plain") -> str:
        return self.fixtures[name].manifest.read_text(encoding="utf-8")

    def write_manifest(self, text: str, name: str = "plain") -> None:
        self.fixtures[name].manifest.write_text(text, encoding="utf-8")

    def break_manifest(self, old: str, new: str, name: str = "plain") -> None:
        """Replace one exact fragment of a sidecar, failing if the fragment is absent."""
        text = self.manifest_text(name)
        if old not in text:
            self.fail(f"{name}'s sidecar does not contain {old!r}")
        self.write_manifest(text.replace(old, new, 1), name)

    def break_body(self, old: str, new: str, name: str = "plain") -> None:
        fixture = self.fixtures[name]
        text = fixture.body.read_text(encoding="utf-8")
        if old not in text:
            self.fail(f"{name}'s account.json does not contain {old!r}")
        fixture.body.write_text(text.replace(old, new, 1), encoding="utf-8")


class CleanCorpus(Scratch):
    def test_valid_corpus_has_no_problems(self) -> None:
        self.assert_clean()

    def test_valid_corpus_exits_zero(self) -> None:
        out = StringIO()
        with redirect_stdout(out):
            self.assertEqual(validate.main(["--root", str(self.root)]), 0)
        self.assertIn("corpus agrees with itself", out.getvalue())

    def test_report_lists_each_fixtures_derived_shape(self) -> None:
        _, report = validate.validate(self.root, report=True)
        self.assertEqual(report, [f"fixtures/plain: {', '.join(PLAIN_SHAPE)}"])

    def test_the_shipped_corpus_validates(self) -> None:
        problems, report = validate.validate(ROOT)
        self.assertEqual(problems, [])
        self.assertEqual(len(report), 0)


class UnreadableCorpus(Scratch):
    def test_missing_fixtures_directory_exits_two(self) -> None:
        shutil.rmtree(self.root / "fixtures")
        err = StringIO()
        with redirect_stderr(err):
            self.assertEqual(validate.main(["--root", str(self.root)]), 2)
        self.assertIn("no readable corpus", err.getvalue())

    def test_fixtures_being_a_file_exits_two(self) -> None:
        shutil.rmtree(self.root / "fixtures")
        (self.root / "fixtures").write_text("not a directory\n", encoding="utf-8")
        with redirect_stderr(StringIO()):
            self.assertEqual(validate.main(["--root", str(self.root)]), 2)

    def test_empty_fixtures_directory_is_a_problem(self) -> None:
        shutil.rmtree(self.root / "fixtures")
        (self.root / "fixtures").mkdir()
        self.assertIn("the corpus is empty", self.problems()[0])


class SidecarKeysAndTypes(Scratch):
    def test_unknown_key_is_named(self) -> None:
        self.break_manifest(f'sha256 = "{self.digest()}"\n', 'served_by = "hand"\n')
        self.assert_problem("unknown key(s) in sidecar: served_by")

    def test_missing_required_key_is_named(self) -> None:
        self.break_manifest('scenario = "an account whose optional fields are all absent"\n', "")
        self.assert_problem("missing key(s): scenario")

    def test_schema_version_from_the_future_is_refused(self) -> None:
        self.break_manifest("schema_version = 1", "schema_version = 2")
        self.assert_problem("schema_version 2, this tool reads 1")

    def test_schema_version_must_be_an_integer(self) -> None:
        self.break_manifest("schema_version = 1", 'schema_version = "one"')
        self.assert_problem("schema_version 'one' must be an integer")

    def test_schema_version_true_is_not_one(self) -> None:
        self.break_manifest("schema_version = 1", "schema_version = true")
        self.assert_problem("schema_version True must be an integer")

    def test_shape_must_be_a_list(self) -> None:
        self.break_manifest(f"shape = {toml_value(PLAIN_SHAPE)}", 'shape = "single_signer"')
        self.assert_problem("shape must be a list of strings")

    def test_kind_is_a_closed_set(self) -> None:
        self.break_manifest('kind = "captured"', 'kind = "remembered"')
        self.assert_problem("kind 'remembered' is not one of")

    def test_network_is_a_closed_set(self) -> None:
        self.break_manifest('network = "public"', 'network = "futurenet"')
        self.assert_problem("network 'futurenet' is not one of")

    def test_id_must_match_its_directory(self) -> None:
        self.break_manifest('id = "plain"', 'id = "plain-two"')
        self.assert_problem("does not match its directory name")

    def test_id_must_be_kebab_case(self) -> None:
        self.break_manifest('id = "plain"', 'id = "Plain_Key"')
        self.assert_problem("is not kebab-case")

    def test_account_id_must_be_a_valid_g_strkey(self) -> None:
        tampered = ACCOUNT[:20] + ("A" if ACCOUNT[20] != "A" else "B") + ACCOUNT[21:]
        self.fixtures["plain"].account = account_json(account_id=tampered)
        self.fixtures["plain"].write(keep=("source_url",))
        self.assert_problem("is not a valid G... strkey")

    def test_a_med25519_address_is_not_an_account_id(self) -> None:
        self.fixtures["plain"].account = account_json(account_id=MED25519)
        self.fixtures["plain"].write(keep=("source_url",))
        self.assert_problem(f"account_id {MED25519!r} is not a valid G... strkey")


class CapturedProvenance(Scratch):
    def test_tampered_body_breaks_the_hash(self) -> None:
        self.break_body('"sequence": "2"', '"sequence": "99999999999"')
        self.assert_problem("sha256 does not match account.json")

    def test_hash_must_be_lowercase_hex(self) -> None:
        self.break_manifest(f'sha256 = "{self.digest()}"', f'sha256 = "{self.digest().upper()}"')
        self.assert_problem("is not 64 lowercase hex characters")

    def test_hash_of_the_wrong_type_is_refused(self) -> None:
        self.break_manifest(f'sha256 = "{self.digest()}"', "sha256 = 42")
        self.assert_problem("sha256 42 is not 64 lowercase hex characters")

    def test_missing_hash_is_refused(self) -> None:
        self.break_manifest(f'sha256 = "{self.digest()}"\n', "")
        self.assert_problem("sha256 None is not 64 lowercase hex characters")

    def test_ledger_must_be_positive(self) -> None:
        self.break_manifest("ledger = 65266813", "ledger = 0")
        self.assert_problem("ledger 0 must be a positive integer")

    def test_ledger_must_be_an_integer(self) -> None:
        self.break_manifest("ledger = 65266813", 'ledger = "65266813"')
        self.assert_problem("ledger '65266813' must be a positive integer")

    def test_missing_ledger_is_refused(self) -> None:
        self.break_manifest("ledger = 65266813\n", "")
        self.assert_problem("ledger None must be a positive integer")

    def test_capture_time_must_be_a_utc_stamp(self) -> None:
        self.break_manifest(f'captured_at = "{CAPTURED_AT}"', 'captured_at = "yesterday"')
        self.assert_problem("must look like 2026-01-02T03:04:05Z")

    def test_capture_time_cannot_be_in_the_future(self) -> None:
        soon = (datetime.now(UTC) + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.break_manifest(f'captured_at = "{CAPTURED_AT}"', f'captured_at = "{soon}"')
        self.assert_problem(f"captured_at {soon} is in the future")

    def test_source_url_must_be_the_accounts_resource(self) -> None:
        self.break_manifest(
            f'source_url = "{ENDPOINT}/accounts/{ACCOUNT}"',
            f'source_url = "{ENDPOINT}/accounts/{ACCOUNT}/operations?limit=1"',
        )
        self.assert_problem("should be")

    def test_source_url_must_match_the_declared_network(self) -> None:
        self.break_manifest(
            f'source_url = "{ENDPOINT}/accounts/{ACCOUNT}"',
            f'source_url = "{TESTNET}/accounts/{ACCOUNT}"',
        )
        self.assert_problem("should be")

    def test_empty_horizon_version_is_refused(self) -> None:
        self.break_manifest('horizon_version = "22.2.1"', 'horizon_version = ""')
        self.assert_problem("horizon_version is empty")

    def test_body_must_describe_the_declared_account(self) -> None:
        fixture = self.fixtures["plain"]
        fixture.account = account_json(account_id=PEER)
        fixture.write(keep=("account_id", "source_url"))
        self.assert_problem("account.json describes")

    def test_unexpected_file_in_a_fixture_directory(self) -> None:
        (self.fixtures["plain"].directory / "notes.md").write_text("hi\n", encoding="utf-8")
        self.assert_problem("unexpected file(s): notes.md")

    def test_missing_files_in_a_fixture_directory(self) -> None:
        self.fixtures["plain"].body.unlink()
        self.assert_problem("missing file(s): account.json")

    def test_json_that_does_not_parse(self) -> None:
        self.break_body('"sequence": "2",', '"sequence": 2,,"x": 1,')
        self.assert_problem("is not JSON")

    def test_json_that_is_not_an_object(self) -> None:
        self.fixtures["plain"].body.write_text("[]\n", encoding="utf-8")
        self.assert_problem("is not an object")

    def test_body_must_end_with_a_newline(self) -> None:
        body = self.fixtures["plain"].body
        body.write_text(body.read_text(encoding="utf-8").rstrip("\n"), encoding="utf-8")
        self.assert_problem("account.json does not end with a newline")

    def test_body_with_crlf_line_endings(self) -> None:
        body = self.fixtures["plain"].body
        body.write_bytes(body.read_bytes().replace(b"\n", b"\r\n"))
        self.assert_problem("account.json has CRLF line endings")


class SidecarTextHygiene(Scratch):
    def test_crlf_sidecar(self) -> None:
        self.write_manifest(self.manifest_text().replace("\n", "\r\n"))
        self.assert_problem("sidecar has CRLF line endings")

    def test_sidecar_without_trailing_newline(self) -> None:
        self.write_manifest(self.manifest_text().rstrip("\n"))
        self.assert_problem("sidecar does not end with a newline")

    def test_trailing_whitespace_is_reported_by_line(self) -> None:
        self.break_manifest('id = "plain"', 'id = "plain" ')
        self.assert_problem("line 3 has trailing whitespace")

    def test_invalid_toml_is_reported_as_such(self) -> None:
        self.break_manifest('id = "plain"', "id = plain")
        self.assert_problem("sidecar is not valid TOML")


class DeclaredShapeVersusBytes(Scratch):
    def test_a_label_the_bytes_do_not_support(self) -> None:
        fixture = self.fixtures["plain"]
        fixture.account = account_json(num_sponsored=2)
        fixture.write(keep=("shape",))
        self.assert_problem("declared shape 'not_sponsored' is not what account.json shows")

    def test_a_shape_the_bytes_show_is_accepted(self) -> None:
        fixture = self.fixtures["plain"]
        fixture.account = account_json(num_sponsored=2)
        fixture.write()
        self.assertIn("sponsored", fixture.shape)
        self.assert_clean()

    def test_an_auth_flag_becomes_its_own_token(self) -> None:
        flags = dict(account_json()["flags"], auth_required=True)
        fixture = self.fixtures["plain"]
        fixture.account = account_json(flags=flags)
        fixture.write()
        self.assertIn("auth_required", fixture.shape)
        self.assert_clean()

    def test_blank_home_domain_is_not_absent_home_domain(self) -> None:
        fixture = self.fixtures["plain"]
        fixture.account = account_json(home_domain=" ")
        fixture.write()
        self.assertIn("blank_home_domain", fixture.shape)
        self.assert_clean()

    def test_master_key_absent_from_signers(self) -> None:
        fixture = self.fixtures["plain"]
        fixture.account = account_json(
            signers=[{"key": PEER, "type": "ed25519_public_key", "weight": 3}],
            thresholds={"low_threshold": 1, "med_threshold": 2, "high_threshold": 3},
        )
        fixture.write()
        self.assertIn("master_absent", fixture.shape)
        self.assertIn("thresholds_nonzero", fixture.shape)
        self.assert_clean()


class DuplicateFixtures(Scratch):
    def test_one_account_cannot_be_captured_twice(self) -> None:
        self.add_fixture("twin")
        self.assert_problem("already captured as fixtures/plain")

    def test_two_accounts_in_one_corpus_is_fine(self) -> None:
        self.add_fixture("twin", account_id=PEER)
        self.assert_clean()


class SeedRefusal(Scratch):
    def test_a_decodable_seed_in_the_body_is_refused(self) -> None:
        fixture = self.fixtures["plain"]
        fixture.account = account_json(data={"note": ZERO_SEED})
        fixture.write()
        problem = self.assert_problem("seed-shaped string")
        self.assertIn("checksum verifies", problem)

    def test_a_seed_shaped_token_is_refused_even_if_fake(self) -> None:
        fixture = self.fixtures["plain"]
        fixture.account = account_json(data={"note": SHAPE_ONLY_SEED})
        fixture.write()
        problem = self.assert_problem("seed-shaped string")
        self.assertNotIn("checksum verifies", problem)

    def test_a_seed_in_the_sidecar_is_refused(self) -> None:
        self.break_manifest('id = "plain"', f'id = "{ZERO_SEED}"')
        self.assert_problem("sidecar contains a seed-shaped string")

    def test_an_account_id_is_not_seed_shaped(self) -> None:
        self.assert_clean()


class SyntheticFixtures(Scratch):
    """A synthetic fixture is authored: no provenance, no hash, and it says so."""

    def synthetic(self, **field_overrides) -> Fixture:
        fixture = self.fixtures["plain"]
        fixture.header = "# Hand-authored specimen, not a capture."
        fixture.fields.update({"kind": "synthetic", "scenario": "synthetic: thresholds at 1/2/3"})
        for key in ("source_url", "captured_at", "ledger", "horizon_version", "sha256"):
            fixture.fields.pop(key)
        fixture.fields.update(field_overrides)
        fixture.manifest.write_text(fixture.manifest_text(), encoding="utf-8")
        return fixture

    def test_a_marked_synthetic_fixture_passes(self) -> None:
        self.synthetic()
        self.assert_clean()

    def test_provenance_a_synthetic_cannot_have(self) -> None:
        self.synthetic(ledger=65266813)
        self.assert_problem("synthetic fixture carries provenance it cannot have: ledger")

    def test_scenario_must_say_it_is_synthetic(self) -> None:
        self.synthetic(scenario="thresholds at 1/2/3")
        self.assert_problem("synthetic fixture must say so at the start of scenario")

    def test_synthetic_shape_is_still_checked_against_bytes(self) -> None:
        fixture = self.synthetic()
        fixture.body.write_text(pretty(account_json(num_sponsoring=4)), encoding="utf-8")
        self.assert_problem("declared shape 'not_sponsoring' is not what account.json shows")


class RootDocument(Scratch):
    def root_path(self) -> Path:
        return self.root / "corpus" / "root-public.json"

    def test_missing_root_document_is_named(self) -> None:
        self.root_path().unlink()
        self.assert_problem("corpus/root-public.json: missing")

    def test_root_document_must_carry_the_network_passphrase(self) -> None:
        wrong = root_document(network_passphrase=TESTNET_PASSPHRASE)
        self.root_path().write_text(pretty(wrong), encoding="utf-8")
        self.assert_problem("is not the public passphrase")

    def test_root_document_that_is_not_json(self) -> None:
        self.root_path().write_text("not json\n", encoding="utf-8")
        self.assert_problem("corpus/root-public.json: not JSON")

    def test_testnet_capture_needs_its_own_root_document(self) -> None:
        fixture = self.fixtures["plain"]
        fixture.fields.update(network="testnet", source_url=f"{TESTNET}/accounts/{ACCOUNT}")
        fixture.manifest.write_text(fixture.manifest_text(), encoding="utf-8")
        self.assert_problem("corpus/root-testnet.json: missing")

    def test_a_root_document_that_is_not_an_object(self) -> None:
        self.root_path().write_text("[]\n", encoding="utf-8")
        self.assert_problem("corpus/root-public.json: not a JSON object")

    def test_an_unknown_network_with_a_file_of_its_own_does_not_crash(self) -> None:
        """The network set is closed, so there is no passphrase to look up."""
        fixture = self.fixtures["plain"]
        fixture.fields.update(network="futurenet", source_url=f"https://frog/{ACCOUNT}")
        fixture.manifest.write_text(fixture.manifest_text(), encoding="utf-8")
        (self.root / "corpus" / "root-futurenet.json").write_text(
            pretty(root_document()), encoding="utf-8"
        )
        problems = self.problems()
        self.assertTrue(any("network 'futurenet' is not one of" in p for p in problems))
        self.assertFalse(any("root-futurenet" in p for p in problems))


class StrkeyDecoding(unittest.TestCase):
    def test_known_crc16_check_value(self) -> None:
        self.assertEqual(crc16_xmodm(b"123456789"), 0x31C3)

    def test_account_version_byte_decodes(self) -> None:
        self.assertEqual(validate.strkey_version(ACCOUNT), 48)
        self.assertTrue(validate.is_valid_account_id(ACCOUNT))

    def test_seed_and_med25519_are_not_account_ids(self) -> None:
        self.assertTrue(validate.is_valid_seed(ZERO_SEED))
        self.assertFalse(validate.is_valid_account_id(ZERO_SEED))
        self.assertFalse(validate.is_valid_account_id(MED25519))

    def test_one_tampered_character_breaks_the_checksum(self) -> None:
        flipped = ACCOUNT[:20] + ("A" if ACCOUNT[20] != "A" else "B") + ACCOUNT[21:]
        self.assertIsNone(validate.strkey_version(flipped))

    def test_wrong_length_and_bad_characters(self) -> None:
        for bad in (ACCOUNT[:-1], ACCOUNT + "A", ACCOUNT.lower(), "G" * 56, ""):
            self.assertIsNone(validate.strkey_version(bad), bad)

    def test_encoder_and_decoder_are_inverses(self) -> None:
        for version in (48, 96, 144):
            key = bytes([version]) * 32
            encoded = encode_strkey(version, key)
            self.assertEqual(len(encoded), 56)
            self.assertEqual(validate.strkey_version(encoded), version)


class ShapesVocabulary(unittest.TestCase):
    def test_defaults_are_the_boring_account(self) -> None:
        self.assertEqual(sorted(shapes_of(account_json())), PLAIN_SHAPE)

    def test_no_signers_is_its_own_shape(self) -> None:
        self.assertIn("no_signers", shapes_of(account_json(signers=[])))

    def test_many_balances_needs_ten(self) -> None:
        nine = [{"asset_type": "native"}] * 9
        ten = [{"asset_type": "native"}] * 10
        self.assertNotIn("many_balances", shapes_of(account_json(balances=nine)))
        self.assertIn("many_balances", shapes_of(account_json(balances=ten)))

    def test_wrong_types_in_a_body_produce_shapes_not_a_traceback(self) -> None:
        """The vocabulary reads files it does not trust, so every read is guarded."""
        garbage = {
            "account_id": 5,
            "signers": "nope",
            "thresholds": {"low_threshold": "high", "med_threshold": None},
            "flags": ["auth_required"],
            "home_domain": 12,
            "balances": 3,
            "num_sponsored": "2",
            "num_sponsoring": True,
        }
        self.assertEqual(
            shapes_of(garbage),
            {
                "no_signers",
                "master_absent",
                "thresholds_zero",
                "has_home_domain",
                "no_inflation",
                "no_data",
                "not_sponsored",
                "not_sponsoring",
                "no_balances",
            },
        )

    def test_a_list_of_signers_may_contain_junk(self) -> None:
        mixed = account_json(signers=[None, {"key": ACCOUNT}, "string"])
        self.assertIn("single_signer", shapes_of(mixed))
        self.assertIn("master_is_signer", shapes_of(mixed))


class FakeHorizon(unittest.TestCase):
    """capture() with one seam replaced: fetch. Everything else is the real code."""

    def setUp(self) -> None:
        stage = tempfile.TemporaryDirectory(prefix="capture-test-")
        self.addCleanup(stage.cleanup)
        self.root = Path(stage.name)
        self.account_payload = account_json()
        self.root_payload = root_document()
        self.account_text: str | None = None
        self.root_text: str | None = None
        self.calls: list[str] = []
        self.real_fetch = capture.fetch
        capture.fetch = self.fetch  # type: ignore[assignment]
        self.addCleanup(self.restore)

    def restore(self) -> None:
        capture.fetch = self.real_fetch  # type: ignore[assignment]

    def fetch(self, url: str, cap: int) -> bytes:
        self.calls.append(url)
        if url.endswith("/"):
            body = pretty(self.root_payload) if self.root_text is None else self.root_text
        elif url.startswith(ENDPOINT + "/accounts/") or url.startswith(TESTNET + "/accounts/"):
            body = pretty(self.account_payload) if self.account_text is None else self.account_text
        else:
            raise AssertionError(f"capture asked for an unexpected url: {url}")
        if len(body) > cap:
            raise capture.Refused(f"response from {url} exceeds the {cap} byte cap")
        return body.encode()

    def run_capture(
        self, *, network: str = "public", fixture_id: str = "fresh", account_id: str = ACCOUNT
    ) -> Path:
        return capture.capture(fixture_id, account_id, "a scenario", network, self.root, False)

    def test_a_capture_writes_a_directory_the_validator_accepts(self) -> None:
        directory = self.run_capture()
        self.assertEqual(
            sorted(p.name for p in directory.iterdir()), ["account.json", "fixture.toml"]
        )
        self.assertEqual(validate.validate(self.root)[0], [])

    def test_the_sidecar_labels_itself_from_the_bytes(self) -> None:
        directory = self.run_capture()
        sidecar = tomllib.loads((directory / "fixture.toml").read_text(encoding="utf-8"))
        self.assertEqual(sidecar["shape"], PLAIN_SHAPE)
        self.assertEqual(sidecar["ledger"], 65266813)
        self.assertEqual(sidecar["horizon_version"], "22.2.1")

    def test_a_changed_account_changes_the_labels(self) -> None:
        self.account_payload = account_json(home_domain="example.com", num_sponsoring=1)
        directory = self.run_capture()
        sidecar = tomllib.loads((directory / "fixture.toml").read_text(encoding="utf-8"))
        self.assertIn("has_home_domain", sidecar["shape"])
        self.assertIn("sponsoring", sidecar["shape"])
        self.assertEqual(validate.validate(self.root)[0], [])

    def test_coreversion_is_preferred_and_horizon_version_is_the_fallback(self) -> None:
        self.root_payload = root_document(coreversion=None)
        directory = self.run_capture()
        sidecar = tomllib.loads((directory / "fixture.toml").read_text(encoding="utf-8"))
        self.assertEqual(sidecar["horizon_version"], "30.0.0")

    def test_a_passphrase_mismatch_refuses_before_any_account_read(self) -> None:
        self.root_payload = root_document(network_passphrase=TESTNET_PASSPHRASE)
        with self.assertRaises(capture.Refused) as caught:
            self.run_capture()
        self.assertIn("network_passphrase", str(caught.exception))
        self.assertEqual(self.calls, [ENDPOINT + "/"])
        self.assertFalse((self.root / "fixtures").exists())

    def test_an_existing_fixture_is_not_overwritten_without_update(self) -> None:
        self.run_capture()
        before = list(self.calls)
        with self.assertRaises(capture.Refused) as caught:
            self.run_capture()
        self.assertIn("pass --update", str(caught.exception))
        self.assertEqual(self.calls, before)

    def test_a_non_g_address_is_refused_without_a_request(self) -> None:
        for bad in (MED25519, ZERO_SEED, "GA7", "MDEQ", ""):
            with self.subTest(bad=bad):
                with self.assertRaises(capture.Refused) as caught:
                    self.run_capture(account_id=bad)
                message = str(caught.exception)
                self.assertIn("M... and C... addresses are not captured here", message)
        self.assertEqual(self.calls, [])

    def test_a_g_shape_with_a_bad_checksum_is_refused_without_a_request(self) -> None:
        for bad in ("G" * 56, ACCOUNT[:-1] + ("A" if ACCOUNT[-1] != "A" else "B")):
            with self.subTest(bad=bad):
                with self.assertRaises(capture.Refused) as caught:
                    self.run_capture(account_id=bad)
                self.assertIn("checksum does not verify", str(caught.exception))
        self.assertEqual(self.calls, [])

    def test_a_non_kebab_fixture_id_is_refused_without_a_request(self) -> None:
        for bad in ("Fresh", "fresh_id", "fresh id", ""):
            with self.subTest(bad=bad), self.assertRaises(capture.Refused):
                self.run_capture(fixture_id=bad)
        self.assertEqual(self.calls, [])

    def test_an_unknown_network_is_refused_without_a_request(self) -> None:
        with self.assertRaises(capture.Refused) as caught:
            self.run_capture(network="futurenet")
        self.assertIn("unknown network", str(caught.exception))
        self.assertEqual(self.calls, [])

    def test_a_seed_in_the_response_is_not_written(self) -> None:
        self.account_payload = account_json(data={"note": ZERO_SEED})
        with self.assertRaises(capture.Refused) as caught:
            self.run_capture()
        self.assertIn("refusing to write it", str(caught.exception))
        self.assertFalse((self.root / "fixtures").exists())

    def test_a_response_about_another_account_is_refused(self) -> None:
        self.account_payload = account_json(account_id=PEER)
        with self.assertRaises(capture.Refused) as caught:
            self.run_capture()
        self.assertIn("not the requested", str(caught.exception))

    def test_a_root_document_that_is_not_json_is_refused(self) -> None:
        self.root_text = "<html>a captive portal, not Horizon</html>"
        with self.assertRaises(capture.Refused) as caught:
            self.run_capture()
        self.assertIn("did not return a JSON root document", str(caught.exception))
        self.assertEqual(self.calls, [ENDPOINT + "/"])

    def test_a_root_document_that_is_not_an_object_is_refused(self) -> None:
        self.root_text = "[]\n"
        with self.assertRaises(capture.Refused) as caught:
            self.run_capture()
        self.assertIn("expected an object", str(caught.exception))

    def test_an_account_body_that_is_not_json_is_refused(self) -> None:
        self.account_text = "{oops"
        with self.assertRaises(capture.Refused) as caught:
            self.run_capture()
        self.assertIn("cannot read", str(caught.exception))

    def test_an_account_body_that_is_not_an_object_is_refused(self) -> None:
        self.account_text = "[]\n"
        with self.assertRaises(capture.Refused) as caught:
            self.run_capture()
        self.assertIn("expected an account object", str(caught.exception))

    def test_update_replaces_an_existing_fixture(self) -> None:
        self.run_capture()
        directory = capture.capture("fresh", ACCOUNT, "a scenario", "public", self.root, True)
        self.assertTrue((directory / "fixture.toml").is_file())
        self.assertEqual(validate.validate(self.root)[0], [])


class Loopback(unittest.TestCase):
    """fetch() against a local server, so the size cap and the redirect rule are tested.

    This is not a run against Horizon: it is the two behaviors that a captured
    fixture's provenance claim depends on.
    """

    class Big(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            payload = b"x" * 4096
            self.send_response(200)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args) -> None:
            """Silence: the assertion is the output."""

    class Redirecting(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(302)
            self.send_header("Location", "http://example.invalid/elsewhere")
            self.end_headers()

        def log_message(self, *args) -> None:
            """Silence: the assertion is the output."""

    def url(self, handler: type[http.server.BaseHTTPRequestHandler]) -> str:
        try:
            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        except OSError:
            self.skipTest("this environment will not let a test bind loopback")
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        self.addCleanup(server.server_close)
        return f"http://127.0.0.1:{server.server_address[1]}/accounts/{ACCOUNT}"

    def test_size_cap_is_enforced(self) -> None:
        with self.assertRaises(capture.Refused) as caught:
            capture.fetch(self.url(self.Big), 512)
        self.assertIn("exceeds the 512 byte cap", str(caught.exception))

    def test_a_redirect_is_refused_rather_than_followed(self) -> None:
        with self.assertRaises(capture.Refused) as caught:
            capture.fetch(self.url(self.Redirecting), 512)
        self.assertIn("does not follow redirects", str(caught.exception))


class SidecarFormat(unittest.TestCase):
    """The writer's exact output, so a format change cannot pass silently."""

    def test_sidecar_is_exactly_this_schema(self) -> None:
        body = pretty(account_json())
        digest = hashlib.sha256(body.encode()).hexdigest()
        scenario = 'a scenario with a "quote" and a backslash \\ in it'
        written = capture.sidecar(
            fixture_id="plain",
            account_id=ACCOUNT,
            network="public",
            scenario=scenario,
            source=f"{ENDPOINT}/accounts/{ACCOUNT}",
            digest=digest,
            ledger=65266813,
            captured=CAPTURED_AT,
            core="22.2.1",
            shape=["no_data", "has_data"],
        )
        expected = (
            "# Written by tools/capture.py. Edit the capture, not this file.\n"
            "schema_version = 1\n"
            'id = "plain"\n'
            'kind = "captured"\n'
            'scenario = "a scenario with a \\"quote\\" and a backslash \\\\ in it"\n'
            f'account_id = "{ACCOUNT}"\n'
            'network = "public"\n'
            f'source_url = "{ENDPOINT}/accounts/{ACCOUNT}"\n'
            f'captured_at = "{CAPTURED_AT}"\n'
            "ledger = 65266813\n"
            'horizon_version = "22.2.1"\n'
            f'sha256 = "{digest}"\n'
            'shape = ["has_data", "no_data"]\n'
        )
        self.assertEqual(written, expected)
        parsed = tomllib.loads(written)
        self.assertEqual(parsed["scenario"], scenario)
        self.assertEqual(parsed["shape"], ["has_data", "no_data"])

    def test_shape_is_written_sorted(self) -> None:
        written = capture.sidecar(
            fixture_id="plain",
            account_id=ACCOUNT,
            network="public",
            scenario="s",
            source=f"{ENDPOINT}/accounts/{ACCOUNT}",
            digest="0" * 64,
            ledger=1,
            captured=CAPTURED_AT,
            core="22.2.1",
            shape=["thresholds_zero", "no_data"],
        )
        self.assertIn('shape = ["no_data", "thresholds_zero"]\n', written)


if __name__ == "__main__":
    unittest.main(verbosity=2)


def run_manifest(root: Path) -> tuple[int, str, str]:
    """The manifest printer, as a consumer would run it."""
    done = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "manifest.py"), "--root", str(root)],
        capture_output=True,
        text=True,
        check=False,
    )
    return done.returncode, done.stdout, done.stderr


class ManifestOfTheShippedCorpus(unittest.TestCase):
    """The manifest is a consumer's pin, so it is driven over the real tree."""

    def records(self) -> list[dict]:
        code, out, err = run_manifest(ROOT)
        self.assertEqual(code, 0, err)
        return [json.loads(line) for line in out.splitlines() if line]

    def test_one_line_per_fixture(self) -> None:
        fixtures = [p for p in (ROOT / "fixtures").iterdir() if p.is_dir()]
        self.assertEqual(len(self.records()), len(fixtures))

    def test_the_order_is_the_fixture_order_and_does_not_move_between_runs(self) -> None:
        first, second = run_manifest(ROOT), run_manifest(ROOT)
        self.assertEqual(first, second)
        ids = [record["id"] for record in self.records()]
        self.assertEqual(ids, sorted(ids))

    def test_each_line_carries_the_fields_a_consumer_pins_by(self) -> None:
        for record in self.records():
            self.assertEqual(
                sorted(record), ["account_id", "id", "kind", "ledger", "network", "sha256"]
            )
            self.assertRegex(record["sha256"], r"^[0-9a-f]{64}$")
            self.assertIsInstance(record["ledger"], int)
            self.assertIn(record["network"], ("public", "testnet"))

    def test_every_digest_is_the_digest_of_the_body_beside_it(self) -> None:
        for record in self.records():
            body = ROOT / "fixtures" / record["id"] / "account.json"
            self.assertEqual(record["sha256"], hashlib.sha256(body.read_bytes()).hexdigest())


class ManifestOfASyntheticFixture(Scratch):
    """A synthetic fixture has no ledger and no digest, and says so with null."""

    def synthetic(self) -> None:
        self.add_fixture("synth")
        text = self.manifest_text("synth")
        text = text.replace('kind = "captured"', 'kind = "synthetic"')
        for key in ("source_url", "captured_at", "ledger", "horizon_version", "sha256"):
            text = re.sub(rf"^{key} = .*\n", "", text, flags=re.MULTILINE)
        self.write_manifest(text, "synth")

    def test_the_provenance_fields_are_null_and_the_rest_survive(self) -> None:
        self.synthetic()
        code, out, err = run_manifest(self.root)
        self.assertEqual(code, 0, err)
        records = {json.loads(line)["id"]: json.loads(line) for line in out.splitlines()}
        record = records["synth"]
        self.assertIsNone(record["ledger"])
        self.assertIsNone(record["sha256"])
        self.assertEqual(record["kind"], "synthetic")
        self.assertTrue(record["account_id"].startswith("G"))

    def test_a_sidecar_that_disagrees_with_its_directory_is_refused(self) -> None:
        self.synthetic()
        self.break_manifest('id = "synth"', 'id = "elsewhere"', "synth")
        code, _, err = run_manifest(self.root)
        self.assertEqual(code, 2)
        self.assertIn("not the directory name", err)

    def test_a_missing_fixtures_directory_is_refused(self) -> None:
        shutil.rmtree(self.root / "fixtures")
        code, _, err = run_manifest(self.root)
        self.assertEqual(code, 2)
        self.assertIn("is not a directory", err)
