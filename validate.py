#!/usr/bin/env python3
"""Validate the fixture corpus: prove what each sidecar claims about its capture.

Stdlib only, Python 3.11+. The corpus is public account data, so this is not a
security tool and says nothing about whether an account is well configured. It
answers one question: does the sidecar still describe the bytes next to it.

Usage:
    python3 validate.py                 # validate the corpus in this directory
    python3 validate.py --report        # print the shape of every fixture
    python3 validate.py --root <dir>    # validate a corpus somewhere else

Exit codes: 0 clean, 1 at least one problem, 2 the corpus could not be read at
all (missing directory, unreadable root, unknown key in a manifest).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tomllib
from datetime import UTC, datetime
from pathlib import Path

SCHEMA_VERSION = 1
BASE_KEYS = {
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
}
CAPTURED_ONLY = {"source_url", "captured_at", "ledger", "horizon_version", "sha256"}
# A synthetic fixture is authored, not captured, so it cannot carry the keys
# below; they are required of a captured one and checked in check_captured.
REQUIRED = sorted(BASE_KEYS - {"schema_version"} - CAPTURED_ONLY)
KINDS = {"captured", "synthetic"}
NETWORKS = {
    "public": ("https://horizon.stellar.org", "Public Global Stellar Network ; September 2015"),
    "testnet": (
        "https://horizon-testnet.stellar.org",
        "Test SDF Network ; September 2015",
    ),
}
ID_SHAPE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SEED_SHAPE = re.compile(r"(?<![A-Z2-7])S[A-Z2-7]{55}(?![A-Z2-7])")
TIMESTAMP_SHAPE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
SHA_SHAPE = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_FILES = {"account.json", "fixture.toml"}
MISSING_ROOT = "missing; every network used must have its root document"
STRKEY_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
VERSION_ACCOUNT = 6 << 3
VERSION_SEED = 18 << 3


class Corpus:
    """The tree being validated, with the errors found so far."""

    def __init__(self, root: Path, report: bool = False) -> None:
        self.root = root
        self.reporting = report
        self.problems: list[str] = []
        self.report: list[str] = []
        self.networks: set[str] = set()

    def error(self, where: str, message: str) -> None:
        self.problems.append(f"{where}: {message}")


def crc16_xmodm(data: bytes) -> int:
    crc = 0
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def strkey_version(text: str) -> int | None:
    """Decode a Stellar strkey enough to check its version byte and checksum.

    A strkey is 56 base32 characters holding a version byte, 32 bytes of key
    material and a CRC16-CCITT of the first 33 bytes. The checksum is what makes
    a typo'd or fabricated address fail here instead of in a consumer's tests.
    """
    if len(text) != 56:
        return None
    bits = 0
    width = 0
    raw = bytearray()
    for char in text:
        index = STRKEY_ALPHABET.find(char)
        if index < 0:
            return None
        bits = (bits << 5) | index
        width += 5
        while width >= 8:
            width -= 8
            raw.append((bits >> width) & 0xFF)
    if len(raw) != 35:
        return None
    body = bytes(raw[:33])
    checksum = bytes(raw[33:35])
    # Horizon's addresses carry the CRC low byte first, which is what a real
    # capture shows; comparing big-endian marks every valid account invalid.
    if crc16_xmodm(body) != int.from_bytes(checksum, "little"):
        return None
    return body[0]


def is_valid_account_id(text: object) -> bool:
    return isinstance(text, str) and strkey_version(text) == VERSION_ACCOUNT


def is_valid_seed(text: str) -> bool:
    return strkey_version(text) == VERSION_SEED


def as_int(value: object) -> int:
    """A count read out of a corpus file. Anything that is not an integer is zero.

    Horizon sends these as integers, but this runs on files, and a body with the
    wrong type must produce a shape or a problem, never a traceback.
    """
    if isinstance(value, bool):
        return 0
    return value if isinstance(value, int) else 0


def shapes_of(account: dict) -> set[str]:
    """Vocabulary the sidecar declares and this validator re-derives from bytes."""
    account_id = account.get("account_id")
    raw_signers = account.get("signers")
    signers = (
        [s for s in raw_signers if isinstance(s, dict)] if isinstance(raw_signers, list) else []
    )
    raw_thresholds = account.get("thresholds")
    thresholds = raw_thresholds if isinstance(raw_thresholds, dict) else {}
    raw_flags = account.get("flags")
    flags = raw_flags if isinstance(raw_flags, dict) else {}
    home_domain = account.get("home_domain")
    found = set()
    if not signers:
        found.add("no_signers")
    elif len(signers) == 1:
        found.add("single_signer")
    else:
        found.add("multi_signer")
    if any(signer.get("key") == account_id for signer in signers):
        found.add("master_is_signer")
    else:
        found.add("master_absent")
    keys = ("low_threshold", "med_threshold", "high_threshold")
    if any(as_int(thresholds.get(key)) for key in keys):
        found.add("thresholds_nonzero")
    else:
        found.add("thresholds_zero")
    for flag, value in flags.items():
        if value:
            found.add(str(flag))
    if home_domain is None:
        found.add("no_home_domain")
    elif isinstance(home_domain, str) and home_domain.strip() == "":
        found.add("blank_home_domain")
    else:
        found.add("has_home_domain")
    found.add("has_inflation" if account.get("inflation_destination") else "no_inflation")
    found.add("has_data" if account.get("data") else "no_data")
    found.add("sponsored" if as_int(account.get("num_sponsored")) > 0 else "not_sponsored")
    found.add("sponsoring" if as_int(account.get("num_sponsoring")) > 0 else "not_sponsoring")
    raw_balances = account.get("balances")
    balances = len(raw_balances) if isinstance(raw_balances, list) else 0
    if balances == 0:
        found.add("no_balances")
    if balances >= 10:
        found.add("many_balances")
    return found


def load_manifest(corpus: Corpus, path: Path, where: str) -> dict | None:
    # read_bytes, not read_text: universal newlines would translate CRLF into
    # LF before this function could see it, and the check below would be dead.
    raw = path.read_bytes()
    if b"\r" in raw:
        corpus.error(where, "sidecar has CRLF line endings")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        corpus.error(where, f"sidecar is not valid UTF-8: {exc}")
        return None
    if not text.endswith("\n"):
        corpus.error(where, "sidecar does not end with a newline")
    for number, line in enumerate(text.splitlines(), start=1):
        if line != line.rstrip():
            corpus.error(where, f"line {number} has trailing whitespace")
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        corpus.error(where, f"sidecar is not valid TOML: {exc}")
        return None
    unknown = sorted(set(data) - BASE_KEYS)
    if unknown:
        corpus.error(where, f"unknown key(s) in sidecar: {', '.join(unknown)}")
    missing = sorted(set(REQUIRED) - set(data))
    if missing:
        corpus.error(where, f"missing key(s): {', '.join(missing)}")
    declared = data.get("schema_version", SCHEMA_VERSION)
    if isinstance(declared, bool) or not isinstance(declared, int):
        corpus.error(where, f"schema_version {declared!r} must be an integer")
    elif declared != SCHEMA_VERSION:
        corpus.error(where, f"schema_version {declared}, this tool reads {SCHEMA_VERSION}")
    return data


def seed_findings(text: str, label: str) -> list[str]:
    """Seed-shaped tokens in `text`, named by `label`, with the real ones flagged.

    A secret seed is the same length and alphabet as an account id with a
    different version byte, so a shape match is already a refusal. Decoding it
    adds nothing a reader should trust; the note just says whether the token is
    a fabricated shape or a key that really exists.
    """
    found = []
    for token in SEED_SHAPE.findall(text):
        suffix = " and its checksum verifies" if is_valid_seed(token) else ""
        found.append(
            f"{label} contains a seed-shaped string{suffix}; the corpus holds public data only"
        )
    return found


def check_common(corpus: Corpus, where: str, data: dict, raw: bytes) -> None:
    for finding in seed_findings(raw.decode("utf-8", "replace"), "sidecar"):
        corpus.error(where, finding)
    fixture_id = data.get("id")
    if not isinstance(fixture_id, str) or not ID_SHAPE.match(fixture_id):
        corpus.error(where, f"id {fixture_id!r} is not kebab-case")
    if fixture_id != Path(where.split(":")[0]).name:
        corpus.error(where, f"id {fixture_id!r} does not match its directory name")
    kind = data.get("kind")
    if kind not in KINDS:
        corpus.error(where, f"kind {kind!r} is not one of {sorted(KINDS)}")
    if kind == "synthetic":
        pretend = sorted(CAPTURED_ONLY & set(data))
        if pretend:
            corpus.error(
                where, f"synthetic fixture carries provenance it cannot have: {', '.join(pretend)}"
            )
        scenario = str(data.get("scenario", ""))
        if not scenario.lower().startswith("synthetic:"):
            corpus.error(where, "synthetic fixture must say so at the start of scenario")
    network = data.get("network")
    if network not in NETWORKS:
        corpus.error(where, f"network {network!r} is not one of {sorted(NETWORKS)}")
    if not is_valid_account_id(data.get("account_id")):
        corpus.error(where, f"account_id {data.get('account_id')!r} is not a valid G... strkey")
    shape = data.get("shape")
    if not isinstance(shape, list) or not all(isinstance(s, str) for s in shape):
        corpus.error(where, "shape must be a list of strings")


def check_captured(corpus: Corpus, where: str, data: dict, body: Path, account: dict) -> None:
    digest = hashlib.sha256(body.read_bytes()).hexdigest()
    if not isinstance(data.get("sha256"), str) or not SHA_SHAPE.match(str(data["sha256"])):
        corpus.error(where, f"sha256 {data.get('sha256')!r} is not 64 lowercase hex characters")
    elif data["sha256"] != digest:
        corpus.error(where, f"sha256 does not match account.json (bytes say {digest[:12]}...)")
    ledger = data.get("ledger")
    if not isinstance(ledger, int) or isinstance(ledger, bool) or ledger <= 0:
        corpus.error(where, f"ledger {ledger!r} must be a positive integer")
    captured = data.get("captured_at")
    if not isinstance(captured, str) or not TIMESTAMP_SHAPE.match(captured):
        corpus.error(where, f"captured_at {captured!r} must look like 2026-01-02T03:04:05Z")
    else:
        stamp = datetime.strptime(captured, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
        if stamp > datetime.now(UTC):
            corpus.error(where, f"captured_at {captured} is in the future")
    endpoint, _ = NETWORKS.get(str(data.get("network")), ("", ""))
    source = data.get("source_url")
    if not isinstance(source, str) or not endpoint:
        corpus.error(where, f"source_url {source!r} is not a string")
    else:
        expected = f"{endpoint}/accounts/{data.get('account_id')}"
        if source != expected:
            corpus.error(where, f"source_url {source!r} should be {expected!r}")
    if not str(data.get("horizon_version", "")):
        corpus.error(where, "horizon_version is empty; the capture must say what served it")
    if account.get("account_id") != data.get("account_id"):
        corpus.error(
            where,
            f"account.json describes {account.get('account_id')!r}, "
            f"sidecar says {data.get('account_id')!r}",
        )
    declared = set(data.get("shape") or [])
    derived = shapes_of(account)
    for token in sorted(declared - derived):
        corpus.error(where, f"declared shape {token!r} is not what account.json shows")


def check_synthetic(corpus: Corpus, where: str, data: dict, account: dict) -> None:
    declared = set(data.get("shape") or [])
    derived = shapes_of(account)
    for token in sorted(declared - derived):
        corpus.error(where, f"declared shape {token!r} is not what account.json shows")


def validate_fixture(corpus: Corpus, directory: Path, seen_ids: dict[str, str]) -> None:
    name = directory.name
    where = f"fixtures/{name}"
    files = {p.name for p in directory.iterdir() if p.is_file()}
    extra = sorted(files - ALLOWED_FILES)
    missing = sorted(ALLOWED_FILES - files)
    if extra:
        corpus.error(where, f"unexpected file(s): {', '.join(extra)}")
    if missing:
        corpus.error(where, f"missing file(s): {', '.join(missing)}")
    if missing:
        return
    body = directory / "account.json"
    manifest_path = directory / "fixture.toml"
    data = load_manifest(corpus, manifest_path, where)
    if data is None:
        return
    check_common(corpus, where, data, manifest_path.read_bytes())
    network = data.get("network")
    if isinstance(network, str):
        corpus.networks.add(network)
    raw_body = body.read_bytes()
    for finding in seed_findings(raw_body.decode("utf-8", "replace"), "account.json"):
        corpus.error(where, finding)
    if not raw_body.endswith(b"\n"):
        corpus.error(where, "account.json does not end with a newline")
    if b"\r" in raw_body:
        corpus.error(where, "account.json has CRLF line endings")
    try:
        account = json.loads(raw_body)
    except ValueError as exc:
        corpus.error(where, f"account.json is not JSON: {exc}")
        return
    if not isinstance(account, dict):
        corpus.error(where, "account.json is not an object")
        return
    fixture_id = str(data.get("id"))
    account_id = str(data.get("account_id") or account.get("account_id") or "")
    if fixture_id in seen_ids:
        corpus.error(where, f"id {fixture_id!r} already used by {seen_ids[fixture_id]}")
    elif account_id and account_id in seen_ids:
        corpus.error(where, f"account {account_id} already captured as {seen_ids[account_id]}")
    else:
        seen_ids[fixture_id] = where
        seen_ids[account_id] = where
    if data.get("kind") == "captured":
        check_captured(corpus, where, data, body, account)
    elif data.get("kind") == "synthetic":
        check_synthetic(corpus, where, data, account)
    if corpus.reporting:
        corpus.report.append(f"{where}: {', '.join(sorted(shapes_of(account)))}")


def check_root(corpus: Corpus, networks: set[str]) -> None:
    # An unknown network is already a problem on its fixture; there is no
    # passphrase to compare it against, and indexing NETWORKS with it would raise.
    for network in sorted(networks & set(NETWORKS)):
        path = corpus.root / "corpus" / f"root-{network}.json"
        if not path.is_file():
            corpus.error(f"corpus/root-{network}.json", MISSING_ROOT)
            continue
        try:
            root = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            corpus.error(f"corpus/root-{network}.json", f"not JSON: {exc}")
            continue
        if not isinstance(root, dict):
            corpus.error(f"corpus/root-{network}.json", "not a JSON object")
            continue
        _, passphrase = NETWORKS[network]
        if root.get("network_passphrase") != passphrase:
            corpus.error(
                f"corpus/root-{network}.json",
                f"network_passphrase {root.get('network_passphrase')!r} "
                f"is not the {network} passphrase",
            )


def validate(root: Path, report: bool = False) -> tuple[list[str], list[str]]:
    fixtures = root / "fixtures"
    if not fixtures.is_dir():
        return [f"{fixtures}: no fixtures directory"], []
    corpus = Corpus(root, report)
    seen: dict[str, str] = {}
    directories = sorted(p for p in fixtures.iterdir() if p.is_dir())
    if not directories:
        corpus.error("fixtures", "the corpus is empty")
    for directory in directories:
        validate_fixture(corpus, directory, seen)
    check_root(corpus, corpus.networks)
    return corpus.problems, corpus.report


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=Path(__file__).resolve().parent, type=Path)
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if not root.is_dir() or not (root / "fixtures").is_dir():
        print(f"validate: no readable corpus at {root}", file=sys.stderr)
        return 2
    problems, report = validate(root, args.report)
    for line in report:
        print(line)
    if problems:
        for line in sorted(problems):
            print(line, file=sys.stderr)
        print(f"validate: {len(problems)} problem(s) in {root}", file=sys.stderr)
        return 1
    print("validate: corpus agrees with itself")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
