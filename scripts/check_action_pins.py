#!/usr/bin/env python3
"""Verify every GitHub Action pin is a 40-hex SHA with a version comment.

Each `uses: owner/repo@sha # tag` line across `.github/workflows/*.yml` must:
- reference a 40-character lowercase hex commit SHA
- carry a trailing `# <tag>` comment naming the tag that SHA resolved from
- use one consistent SHA per action repository across all workflows

Exit 0 when all pins are honest, exit 1 with the problem on stderr otherwise.

Stdlib only, re and pathlib. Zero em dashes.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORKFLOWS = REPO / ".github" / "workflows"

USES_RE = re.compile(
    r"^\s*- uses:\s*(?P<action>[^@\s#]+)@(?P<sha>[0-9a-f]{40})\s+#\s*(?P<tag>\S+)\s*$"
)


def problem(message: str) -> None:
    print(f"check_action_pins: {message}", file=sys.stderr)


def check(workflows: Path) -> bool:
    ok = True
    pins: dict[str, str] = {}
    for path in sorted(workflows.glob("*.yml")):
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if not stripped.startswith("- uses:"):
                continue
            match = USES_RE.match(line)
            if match is None:
                ok = False
                problem(
                    f"{path}:{lineno}: uses line is not 'owner/repo@40hexsha # tag': {stripped}"
                )
                continue
            action = match.group("action")
            sha = match.group("sha")
            previous = pins.setdefault(action, sha)
            if previous != sha:
                ok = False
                problem(f"{path}:{lineno}: {action} pinned to {sha} here but {previous} elsewhere")
    return ok


def main(argv: list[str]) -> int:
    workflows = Path(argv[0]) if argv else WORKFLOWS
    return 0 if check(workflows) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
