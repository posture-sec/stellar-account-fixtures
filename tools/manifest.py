#!/usr/bin/env python3
"""Print a machine-readable manifest of the fixture corpus.

One JSON object per line, so a consumer can name a fixture by what it contains
instead of by which commit was current when its test was written. The digest is
read from the sidecar, which `validate.py` has already checked against the bytes
of `account.json`; nothing here recomputes a check that exists elsewhere.

Stdlib only (D-02). The output carries no timestamp, so two runs over the same
tree are byte-identical and a consumer can pin the manifest itself.

Usage:
    python3 tools/manifest.py                # the corpus in this directory
    python3 tools/manifest.py --root <dir>   # a corpus somewhere else

Nulls, decided here rather than invented per line:
    ledger      null on a synthetic fixture, which was never read from a ledger
    sha256      null when the sidecar carries none, which is the same synthetic case
`account_id` and `network` are required on both kinds, so they are never null.

Exit codes: 0 printed, 2 the corpus could not be read at all.
"""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path
from typing import NoReturn

FIELDS = ("id", "kind", "account_id", "network", "ledger", "sha256")


def refuse(message: str) -> NoReturn:
    """Print a refusal and leave with the corpus-unreadable code."""
    print(f"manifest: {message}", file=sys.stderr)
    sys.exit(2)


def read_sidecar(path: Path) -> dict:
    """One sidecar, or a refusal that names the file."""
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        refuse(f"{path}: {exc}")


def fixtures(root: Path) -> list[Path]:
    """Every fixture directory, sorted by name so the order is the tree's, not the disk's."""
    corpus = root / "fixtures"
    if not corpus.is_dir():
        refuse(f"{corpus} is not a directory")
    directories = sorted(
        (entry for entry in corpus.iterdir() if entry.is_dir()), key=lambda p: p.name
    )
    if not directories:
        refuse(f"{corpus} holds no fixtures")
    return directories


def line_for(directory: Path) -> str:
    data = read_sidecar(directory / "fixture.toml")
    name = directory.name
    if data.get("id") != name:
        refuse(f"fixtures/{name}: id is {data.get('id')!r}, not the directory name")
    record = {field: data.get(field) for field in FIELDS}
    return json.dumps(record, separators=(",", ":"), ensure_ascii=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=Path(__file__).resolve().parent.parent, type=Path)
    args = parser.parse_args(argv)
    for directory in fixtures(args.root):
        print(line_for(directory))
    return 0


if __name__ == "__main__":
    sys.exit(main())
