#!/usr/bin/env python3
"""Generate a JSON Lines manifest of corpus fixtures for external consumers (issue #17, #18).

Prints one JSON object per line with id, account_id, network, ledger and sha256, sorted by id,
allowing consumer test suites (such as Gauge) to pin the corpus by cryptographic content rather
than repository commit hash.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = REPO_ROOT / "fixtures"


def build_manifest(fixtures_dir: Path | None = None) -> list[dict[str, object]]:
    target_dir = fixtures_dir or FIXTURES_DIR
    if not target_dir.is_dir():
        return []

    records: list[dict[str, object]] = []
    for fixture_dir in sorted(target_dir.iterdir()):
        sidecar = fixture_dir / "fixture.toml"
        account_file = fixture_dir / "account.json"
        if fixture_dir.is_dir() and sidecar.is_file() and account_file.is_file():
            with open(sidecar, "rb") as f:
                data = tomllib.load(f)
            digest = str(data.get("sha256", ""))
            if not digest and account_file.is_file():
                digest = hashlib.sha256(account_file.read_bytes()).hexdigest()
            record: dict[str, object] = {
                "id": str(data.get("id", fixture_dir.name)),
                "account_id": str(data.get("account_id", "")),
                "network": str(data.get("network", "")),
                "ledger": data.get("ledger"),
                "sha256": digest,
            }
            records.append(record)

    records.sort(key=lambda r: str(r["id"]))
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()

    records = build_manifest()
    for record in records:
        print(json.dumps(record, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
