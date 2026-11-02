#!/usr/bin/env python3
"""Capture one public Stellar account from Horizon into the corpus.

Stdlib only. The account resource is public data, so nothing is stripped and
nothing is invented: the bytes Horizon returns are written verbatim and the
sidecar records where they came from.

Exit codes: 0 wrote a fixture, 2 refused (bad input, unknown key, seed-shaped
string, network mismatch), 1 the fetch failed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

# The shape vocabulary belongs to the validator: one definition of what a
# fixture looks like, so a capture cannot invent a label nothing checks.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from validate import is_valid_account_id, shapes_of  # noqa: E402

ENDPOINTS = {
    "public": "https://horizon.stellar.org",
    "testnet": "https://horizon-testnet.stellar.org",
}
PASSPHRASES = {
    "public": "Public Global Stellar Network ; September 2015",
    "testnet": "Test SDF Network ; September 2015",
}
USER_AGENT = "stellar-account-fixtures-capture/0.1"
ACCOUNT_CAP = 512_000
ROOT_CAP = 128_000
# A secret seed is the same shape as an account id with a different version
# byte. Catching it here is cheaper than explaining it later.
SEED_SHAPE = re.compile(rb"S[A-Z2-7]{55}")
ACCOUNT_SHAPE = re.compile(r"^G[A-Z2-7]{55}$")
ID_SHAPE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class Refused(Exception):
    """A check said no. Reported as exit 2 with its reason."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """A sidecar records one URL as the source of one capture, so a redirect lies.

    urllib follows 3xx by default. Following one would write bytes from somewhere
    else under the URL that was asked for, and the passphrase check on the root
    document would not see it.
    """

    def redirect_request(self, request, fp, code, message, headers, newurl):
        raise Refused(
            f"{request.full_url} answered {code} with a redirect to {newurl}; "
            "the corpus does not follow redirects"
        )


OPENER = urllib.request.build_opener(NoRedirect)


def fetch(url: str, cap: int) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last: Exception | None = None
    for attempt in range(3):
        try:
            with OPENER.open(request, timeout=15) as response:
                body = response.read(cap + 1)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = exc
            time.sleep(1.5 * (attempt + 1))
            continue
        if len(body) > cap:
            raise Refused(f"response from {url} exceeds the {cap} byte cap")
        status = getattr(response, "status", 200)
        if status != 200:
            raise RuntimeError(f"{url} answered {status}")
        return body
    raise RuntimeError(f"{url} unreachable after 3 attempts: {type(last).__name__}")


def verify_network(endpoint: str, expected: str) -> str:
    body = fetch(f"{endpoint}/", ROOT_CAP)
    try:
        root = json.loads(body)
    except ValueError as exc:
        raise Refused(f"{endpoint}/ did not return a JSON root document: {exc}") from exc
    if not isinstance(root, dict):
        raise Refused(f"{endpoint}/ returned {type(root).__name__}, expected an object")
    version = str(root.get("network_passphrase", ""))
    if version != expected:
        raise Refused(f"{endpoint} reports network_passphrase {version!r}, expected {expected!r}")
    # Horizon 30 stopped reporting coreversion on the root document.
    for key in ("coreversion", "horizon_version"):
        value = root.get(key)
        if value:
            return str(value)
    return "unknown"


def toml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def sidecar(
    *,
    fixture_id: str,
    account_id: str,
    network: str,
    scenario: str,
    source: str,
    digest: str,
    ledger: int,
    captured: str,
    core: str,
    shape: list[str],
) -> str:
    shapes = ", ".join(f'"{toml_escape(token)}"' for token in sorted(shape))
    return (
        "# Written by tools/capture.py. Edit the capture, not this file.\n"
        "schema_version = 1\n"
        f'id = "{toml_escape(fixture_id)}"\n'
        'kind = "captured"\n'
        f'scenario = "{toml_escape(scenario)}"\n'
        f'account_id = "{toml_escape(account_id)}"\n'
        f'network = "{toml_escape(network)}"\n'
        f'source_url = "{toml_escape(source)}"\n'
        f'captured_at = "{captured}"\n'
        f"ledger = {ledger}\n"
        f'horizon_version = "{toml_escape(core)}"\n'
        f'sha256 = "{digest}"\n'
        f"shape = [{shapes}]\n"
    )


def capture(
    fixture_id: str, account_id: str, scenario: str, network: str, root: Path, update: bool
) -> Path:
    if not ID_SHAPE.match(fixture_id):
        raise Refused(f"fixture id {fixture_id!r} is not kebab-case")
    if not ACCOUNT_SHAPE.match(account_id):
        raise Refused(
            f"account {account_id!r} is not a G... ed25519 account id; "
            "M... and C... addresses are not captured here"
        )
    if not is_valid_account_id(account_id):
        raise Refused(
            f"account {account_id!r} is G-shaped but its checksum does not verify; "
            "a typo is refused here rather than 404ing at Horizon"
        )
    if network not in ENDPOINTS:
        raise Refused(f"unknown network {network!r}; expected one of {sorted(ENDPOINTS)}")
    directory = root / "fixtures" / fixture_id
    if directory.exists() and not update:
        raise Refused(f"{directory} already exists; pass --update to replace it")
    endpoint = ENDPOINTS[network]
    core = verify_network(endpoint, PASSPHRASES[network])

    source = f"{endpoint}/accounts/{account_id}"
    body = fetch(source, ACCOUNT_CAP)
    try:
        payload = json.loads(body)
    except ValueError as exc:
        raise Refused(f"Horizon returned JSON this parser cannot read: {exc}") from exc
    if SEED_SHAPE.search(body):
        raise Refused("captured body contains a seed-shaped string; refusing to write it")
    if not isinstance(payload, dict):
        raise Refused(f"{source} returned {type(payload).__name__}, expected an account object")
    if payload.get("account_id") != account_id:
        raise Refused(
            f"response describes {payload.get('account_id')!r}, not the requested {account_id!r}"
        )

    directory.mkdir(parents=True, exist_ok=True)

    pretty = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    digest = hashlib.sha256(pretty.encode()).hexdigest()
    (directory / "account.json").write_text(pretty, encoding="utf-8")
    captured = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    (directory / "fixture.toml").write_text(
        sidecar(
            fixture_id=fixture_id,
            account_id=account_id,
            network=network,
            scenario=scenario,
            source=source,
            digest=digest,
            ledger=int(payload.get("last_modified_ledger") or 0),
            captured=captured,
            core=core,
            shape=sorted(shapes_of(payload)),
        ),
        encoding="utf-8",
    )

    corpus_file = root / "corpus" / f"root-{network}.json"
    corpus_file.parent.mkdir(parents=True, exist_ok=True)
    root_body = fetch(endpoint + "/", ROOT_CAP)
    corpus_file.write_text(
        json.dumps(json.loads(root_body), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return directory


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--network", required=True, choices=sorted(ENDPOINTS))
    parser.add_argument("--account", required=True)
    parser.add_argument("--id", required=True, dest="fixture_id")
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--root", default=".", type=Path)
    parser.add_argument("--update", action="store_true")
    args = parser.parse_args(argv)
    try:
        directory = capture(
            args.fixture_id,
            args.account,
            args.scenario,
            args.network,
            Path(args.root).resolve(),
            args.update,
        )
    except Refused as exc:
        print(f"capture refused: {exc}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(f"capture failed: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {directory.relative_to(Path(args.root).resolve())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
