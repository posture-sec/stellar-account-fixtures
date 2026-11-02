#!/usr/bin/env bash
# Fails when a pull request changes files without updating ROADMAP.md in the
# same change, or updates it while leaving the "Last updated" line untouched.
#
# Usage: scripts/check_roadmap_touched.sh [base-ref]   (default: $GITHUB_BASE_REF or main)
set -euo pipefail

base="${1:-${GITHUB_BASE_REF:-main}}"
cd "$(git rev-parse --show-toplevel)"

if ! git rev-parse --verify --quiet "${base}^{commit}" >/dev/null; then
  echo "check_roadmap_touched: base ref '${base}' is not available; fetch it before running" >&2
  exit 1
fi

changed="$(git diff --name-only "${base}...HEAD")"

if [ -z "${changed}" ]; then
  echo "check_roadmap_touched: nothing changed against ${base}, nothing to enforce"
  exit 0
fi

if ! printf '%s\n' "${changed}" | grep -qx 'ROADMAP.md'; then
  echo "check_roadmap_touched: ROADMAP.md must be updated in the same pull request." >&2
  echo "Files changed:" >&2
  printf '%s\n' "${changed}" | sed 's/^/  /' >&2
  exit 1
fi

old_line="$(git show "${base}:ROADMAP.md" | grep -m1 '^Last updated:' || true)"
new_line="$(grep -m1 '^Last updated:' ROADMAP.md || true)"

if [ -z "${new_line}" ]; then
  echo "check_roadmap_touched: ROADMAP.md has no 'Last updated' line." >&2
  exit 1
fi

if [ "${old_line}" = "${new_line}" ]; then
  echo "check_roadmap_touched: ROADMAP.md changed but 'Last updated' did not." >&2
  echo "  ${new_line}" >&2
  exit 1
fi

echo "check_roadmap_touched: ${new_line}"
