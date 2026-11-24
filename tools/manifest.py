#!/usr/bin/env python3
"""Generate a JSON Lines manifest of corpus fixtures for external consumers.

Prints one JSON object per line with id, kind, account_id, network, ledger and sha256,
sorted by id, allowing consumer test suites (such as Gauge and Airlock) to pin the
corpus by cryptographic content rather than repository commit hash.

Null semantics:
    ledger:  null on synthetic fixtures (never read from a chain)
    sha256:  null on synthetic fixtures when not computed
`account_id` and `network` are required on both captured and synthetic fixtures.
"""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = REPO_ROOT / "fixtures"


def build_manifest(fixtures_dir: Path | None = None) -> list[dict[str, object]]:
    """Build sorted manifest records from fixture directories."""
    target_dir = fixtures_dir or FIXTURES_DIR
    if not target_dir.is_dir():
        return []

    records: list[dict[str, object]] = []
    for fixture_dir in sorted(target_dir.iterdir()):
        sidecar = fixture_dir / "fixture.toml"
        account_file = fixture_dir / "account.json"
        if fixture_dir.is_dir() and sidecar.is_file() and account_file.is_file():
            try:
                with open(sidecar, "rb") as f:
                    data = tomllib.load(f)
            except Exception:
                continue

            ledger_val = data.get("ledger")
            sha_val = data.get("sha256")
            record: dict[str, object] = {
                "id": str(data.get("id", fixture_dir.name)),
                "kind": str(data.get("kind", "captured")),
                "account_id": str(data.get("account_id", "")),
                "network": str(data.get("network", "")),
                "ledger": int(ledger_val) if isinstance(ledger_val, int) else None,
                "sha256": str(sha_val) if sha_val is not None else None,
            }
            records.append(record)

    records.sort(key=lambda r: str(r["id"]))
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Root repository directory or fixtures directory to generate manifest from",
    )
    args = parser.parse_args(argv)

    fixtures_dir: Path | None = None
    if args.root:
        if (args.root / "fixtures").is_dir():
            fixtures_dir = args.root / "fixtures"
        elif args.root.is_dir():
            fixtures_dir = args.root
        else:
            print(f"manifest: {args.root} is not a valid directory", file=sys.stderr)
            return 2

    records = build_manifest(fixtures_dir)
    for record in records:
        print(json.dumps(record, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
