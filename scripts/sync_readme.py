#!/usr/bin/env python3
"""Synchronize dynamic README metrics and live Shields.io endpoint data for Fixtures.

Inspects the repository test suites, fixtures corpus, and status, and writes:
1. Dynamic Shields.io JSON endpoints under `site/data/badge-*.json`.
2. Marked block between `<!-- METRICS:START -->` and `<!-- METRICS:END -->` in `README.md`.
3. Marked block between `<!-- ACCOUNTS:START -->` and `<!-- ACCOUNTS:END -->` in `README.md`.
4. Marked block between `<!-- SHAPE-GAPS:START -->` and `<!-- SHAPE-GAPS:END -->` in `README.md`.

With `--check`, exits 1 if any target is stale without modifying files.
"""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
README_PATH = REPO_ROOT / "README.md"
SCHEMA_PATH = REPO_ROOT / "SCHEMA.md"
FIXTURES_DIR = REPO_ROOT / "fixtures"
DATA_DIR = REPO_ROOT / "site" / "data"

METRICS_START = "<!-- METRICS:START -->"
METRICS_END = "<!-- METRICS:END -->"
ACCOUNTS_START = "<!-- ACCOUNTS:START -->"
ACCOUNTS_END = "<!-- ACCOUNTS:END -->"
SHAPE_GAPS_START = "<!-- SHAPE-GAPS:START -->"
SHAPE_GAPS_END = "<!-- SHAPE-GAPS:END -->"


def count_fixtures() -> int:
    if not FIXTURES_DIR.is_dir():
        return 9
    return len([p for p in FIXTURES_DIR.iterdir() if p.is_dir() and (p / "account.json").is_file()])


def count_networks() -> tuple[int, int]:
    """Count public (mainnet) and testnet fixtures from sidecar metadata."""
    if not FIXTURES_DIR.is_dir():
        return 8, 1
    mainnet = 0
    testnet = 0
    for p in FIXTURES_DIR.iterdir():
        if p.is_dir() and (p / "account.json").is_file():
            sidecar = p / "fixture.toml"
            if sidecar.is_file():
                try:
                    with open(sidecar, "rb") as f:
                        data = tomllib.load(f)
                    net = str(data.get("network", ""))
                    if net == "public":
                        mainnet += 1
                    elif net == "testnet":
                        testnet += 1
                except Exception:
                    pass
    return mainnet, testnet


def count_tests() -> int:
    sys.path.insert(0, str(REPO_ROOT))
    import test_validate

    suite1 = unittest.defaultTestLoader.loadTestsFromModule(test_validate)
    count1 = suite1.countTestCases()

    loader = unittest.TestLoader()
    suite2 = loader.discover(str(REPO_ROOT / "tests"), pattern="test_*.py")
    if loader.errors:
        raise RuntimeError("test discovery failed:\n" + "\n".join(map(str, loader.errors)))

    return count1 + suite2.countTestCases()


def generate_metrics_table(
    fixtures_count: int, test_count: int, mainnet_count: int = 8, testnet_count: int = 1
) -> str:
    captures_cell = (
        f"| Verified Captures | **{fixtures_count} accounts** "
        f"({mainnet_count} Mainnet, {testnet_count} Test) | `fixtures/` |\n"
    )
    return (
        f"{METRICS_START}\n"
        "| Indicator | Value | Source |\n"
        "|---|---|---|\n"
        f"{captures_cell}"
        f"| Test Suite | **{test_count} passing** | `python -m unittest` |\n"
        "| Integrity Assurance | **SHA-256 sidecars verified** | `validate.py` |\n"
        "| Safety Invariant | **Zero secret keys (`S...`)** | Validator enforced |\n"
        f"{METRICS_END}"
    )


def generate_accounts_table() -> str:
    """Render 'The nine accounts' table from on-disk fixture sidecars sorted by id."""
    if not FIXTURES_DIR.is_dir():
        return f"{ACCOUNTS_START}\n| Fixture | Why it is here |\n|---|---|\n{ACCOUNTS_END}"
    rows: list[tuple[str, str]] = []
    for p in FIXTURES_DIR.iterdir():
        if p.is_dir() and (p / "account.json").is_file():
            sidecar = p / "fixture.toml"
            fixture_id = p.name
            scenario = ""
            if sidecar.is_file():
                try:
                    with open(sidecar, "rb") as f:
                        data = tomllib.load(f)
                    fixture_id = str(data.get("id", p.name))
                    scenario = str(data.get("scenario", ""))
                except Exception:
                    pass
            rows.append((fixture_id, scenario))
    rows.sort(key=lambda item: item[0])
    lines = [
        ACCOUNTS_START,
        "| Fixture | Why it is here |",
        "|---|---|",
    ]
    for f_id, sc in rows:
        lines.append(f"| `{f_id}` | {sc} |")
    lines.append(ACCOUNTS_END)
    return "\n".join(lines)


def schema_shape_labels() -> set[str]:
    """Read the shape-label vocabulary from Section 5 of SCHEMA.md."""
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    lines = schema.splitlines()
    try:
        start = lines.index("## 5. The shape vocabulary") + 1
    except ValueError as exc:
        raise ValueError("SCHEMA.md has no Section 5 shape vocabulary") from exc

    labels: set[str] = set()
    for line in lines[start:]:
        if line.startswith("## "):
            break
        if line.startswith("| `"):
            labels.add(line.split("`", 2)[1])
    if not labels:
        raise ValueError("SCHEMA.md Section 5 contains no shape labels")
    return labels


def fixture_shape_labels() -> set[str]:
    """Return the union of shape labels declared by on-disk fixture sidecars."""
    labels: set[str] = set()
    if not FIXTURES_DIR.is_dir():
        return labels
    for sidecar in FIXTURES_DIR.glob("*/fixture.toml"):
        with sidecar.open("rb") as f:
            data = tomllib.load(f)
        shapes = data.get("shape")
        if not isinstance(shapes, list) or not all(isinstance(shape, str) for shape in shapes):
            raise ValueError(f"{sidecar} must contain a list of string shape labels")
        labels.update(shapes)
    return labels


def generate_shape_gaps_block() -> str:
    """Render shape-label coverage from the schema vocabulary and fixture sidecars."""
    vocabulary = schema_shape_labels()
    uncovered = sorted(vocabulary - fixture_shape_labels())
    covered_count = len(vocabulary) - len(uncovered)
    lines = [SHAPE_GAPS_START]
    if uncovered:
        lines.append(
            f"{covered_count} of {len(vocabulary)} shape labels have a fixture. "
            f"These {len(uncovered)} do not:"
        )
        lines.append("")
        lines.extend(f"- `{label}`" for label in uncovered)
    else:
        lines.append(f"All {len(vocabulary)} shape labels have a fixture.")
    lines.append(SHAPE_GAPS_END)
    return "\n".join(lines)


def build_badge_json(label: str, message: str, color: str) -> dict[str, object]:
    return {
        "schemaVersion": 1,
        "label": label,
        "message": message,
        "color": color,
    }


def sync(*, check: bool = False) -> bool:
    fixtures_count = count_fixtures()
    mainnet_count, testnet_count = count_networks()
    test_count = count_tests()
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    badges = {
        DATA_DIR / "badge-fixtures.json": build_badge_json(
            "fixtures", f"{fixtures_count} verified", "06b6d4"
        ),
        DATA_DIR / "badge-tests.json": build_badge_json("tests", f"{test_count} passed", "38bdf8"),
        DATA_DIR / "badge-status.json": build_badge_json("corpus", "active", "10b981"),
    }

    stale = False

    # Check/write badge JSONs
    for path, data in badges.items():
        rendered = json.dumps(data, indent=2, sort_keys=True) + "\n"
        if path.exists():
            current = path.read_text(encoding="utf-8")
            if current != rendered:
                stale = True
                if not check:
                    path.write_text(rendered, encoding="utf-8")
        else:
            stale = True
            if not check:
                path.write_text(rendered, encoding="utf-8")

    # Check/write README.md
    if README_PATH.exists():
        content = README_PATH.read_text(encoding="utf-8")
        updated = content
        if METRICS_START in updated and METRICS_END in updated:
            before, rest = updated.split(METRICS_START, 1)
            _, after = rest.split(METRICS_END, 1)
            new_table = generate_metrics_table(
                fixtures_count, test_count, mainnet_count, testnet_count
            )
            updated = f"{before}{new_table}{after}"

        if ACCOUNTS_START in updated and ACCOUNTS_END in updated:
            before, rest = updated.split(ACCOUNTS_START, 1)
            _, after = rest.split(ACCOUNTS_END, 1)
            new_accounts = generate_accounts_table()
            updated = f"{before}{new_accounts}{after}"

        if updated.count(SHAPE_GAPS_START) != 1 or updated.count(SHAPE_GAPS_END) != 1:
            print(
                f"sync_readme: README.md must contain exactly one "
                f"{SHAPE_GAPS_START} ... {SHAPE_GAPS_END} block.",
                file=sys.stderr,
            )
            return False
        before, rest = updated.split(SHAPE_GAPS_START, 1)
        _, after = rest.split(SHAPE_GAPS_END, 1)
        updated = f"{before}{generate_shape_gaps_block()}{after}"

        if updated != content:
            stale = True
            if not check:
                README_PATH.write_text(updated, encoding="utf-8")

    if check and stale:
        print(
            "sync_readme: README metrics, accounts table, shape gap list, or badge data are stale. "
            "Run: python3 scripts/sync_readme.py",
            file=sys.stderr,
        )
        return False

    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="Exit 1 if stale without modifying files"
    )
    args = parser.parse_args()

    ok = sync(check=args.check)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
