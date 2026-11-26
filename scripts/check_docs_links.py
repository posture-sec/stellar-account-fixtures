#!/usr/bin/env python3
"""Check relative markdown links and fragment anchors across documentation files.

Scans `README.md`, `CONTRIBUTING.md`, `SCHEMA.md`, and markdown files under `docs/`
for relative filesystem links and `#anchor` fragments without making network calls.
External URLs (`http://`, `https://`, `mailto:`, etc.) are skipped.

Usage:
    python3 scripts/check_docs_links.py [--root <dir>] [paths...]

Exit codes: 0 when all relative links resolve, 1 when any link is broken or
no documentation files are found.
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.parse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CORE_DOCS = ("README.md", "CONTRIBUTING.md", "SCHEMA.md")

FENCE_OPEN_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
ATX_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}[ \t]+(.+?)(?:[ \t]+#+[ \t]*)?$")
LINK_RE = re.compile(r"!?\[(?:[^\[\]\\]|\\.)*\]\(((?:[^()\n]|(?:\([^()\n]*\)))*)\)")
SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
HTML_ANCHOR_RE = re.compile(r"""<a\b[^>]*\b(?:id|name)=["']([^"']+)["']""", re.IGNORECASE)
HTML_TAG_RE = re.compile(r"<[^>]+>")
INLINE_LINK_RE = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
LINE_ANCHOR_RE = re.compile(r"L(\d+)(?:-L(\d+))?")


def strip_fenced_code_blocks(text: str) -> list[tuple[int, str]]:
    """Return 1-based `(lineno, line)` pairs outside fenced code blocks."""
    visible: list[tuple[int, str]] = []
    fence_char: str | None = None
    fence_len = 0

    for lineno, line in enumerate(text.splitlines(), 1):
        if fence_char is None:
            match = FENCE_OPEN_RE.match(line)
            if match:
                fence = match.group(1)
                fence_char = fence[0]
                fence_len = len(fence)
                continue
            visible.append((lineno, line))
        else:
            stripped = line.strip()
            if (
                len(stripped) >= fence_len
                and set(stripped) == {fence_char}
                and len(line) - len(line.lstrip(" ")) <= 3
            ):
                fence_char = None
                fence_len = 0

    return visible


def inline_code_ranges(line: str) -> list[tuple[int, int]]:
    """Return `(start, end)` character spans for inline backtick code on a line."""
    ranges: list[tuple[int, int]] = []
    index = 0
    length = len(line)
    while index < length:
        if line[index] == "`":
            ticks = 1
            while index + ticks < length and line[index + ticks] == "`":
                ticks += 1
            close = line.find("`" * ticks, index + ticks)
            if close != -1:
                ranges.append((index, close + ticks))
                index = close + ticks
                continue
            index += ticks
        else:
            index += 1
    return ranges


def slugify_heading(raw_heading: str) -> str:
    """Convert a markdown heading into a GitHub-compatible anchor slug."""
    cleaned = INLINE_LINK_RE.sub(r"\1", raw_heading)
    cleaned = HTML_TAG_RE.sub("", cleaned)
    cleaned = cleaned.strip().lower()
    cleaned = re.sub(r"[^\w -]", "", cleaned)
    return cleaned.replace(" ", "-")


def extract_anchors(path: Path) -> set[str]:
    """Collect heading slugs and explicit HTML anchors from a markdown file."""
    text = path.read_text(encoding="utf-8")
    anchors: set[str] = set()
    seen_counts: dict[str, int] = {}

    for _lineno, line in strip_fenced_code_blocks(text):
        heading = ATX_HEADING_RE.match(line)
        if heading:
            base = slugify_heading(heading.group(1))
            if base:
                count = seen_counts.get(base, 0)
                seen_counts[base] = count + 1
                candidate = base if count == 0 else f"{base}-{count}"
                while candidate in anchors:
                    count += 1
                    seen_counts[base] = count + 1
                    candidate = f"{base}-{count}"
                anchors.add(candidate)

        for html_match in HTML_ANCHOR_RE.finditer(line):
            anchors.add(html_match.group(1))

    return anchors


def extract_links(path: Path) -> list[tuple[int, str]]:
    """Return `(lineno, raw_target)` tuples for markdown links outside code blocks."""
    text = path.read_text(encoding="utf-8")
    links: list[tuple[int, str]] = []

    for lineno, line in strip_fenced_code_blocks(text):
        code_spans = inline_code_ranges(line)
        for match in LINK_RE.finditer(line):
            start = match.start()
            if any(span_start <= start < span_end for span_start, span_end in code_spans):
                continue
            links.append((lineno, match.group(1)))

    return links


def parse_target(raw_target: str) -> str | None:
    """Extract the target path/fragment from a raw markdown link destination."""
    stripped = raw_target.strip()
    if not stripped:
        return None
    if stripped.startswith("<"):
        end = stripped.find(">")
        if end == -1:
            return None
        inner = stripped[1:end].strip()
        return inner or None
    target = re.split(r"\s+(?=[\"'])", stripped, maxsplit=1)[0].strip()
    return target or None


def collect_doc_files(root: Path, paths: list[Path] | None = None) -> list[Path]:
    """Collect markdown files to scan under `root` or from explicit `paths`."""
    if paths:
        collected: list[Path] = []
        for item in paths:
            candidate = item if item.is_absolute() else (root / item)
            if candidate.is_dir():
                collected.extend(sorted(candidate.rglob("*.md")))
            else:
                collected.append(candidate)
        return collected

    files: list[Path] = []
    for name in CORE_DOCS:
        candidate = root / name
        if candidate.is_file():
            files.append(candidate)
    docs_dir = root / "docs"
    if docs_dir.is_dir():
        files.extend(sorted(docs_dir.rglob("*.md")))
    return files


def check_links(root: Path, paths: list[Path] | None = None) -> tuple[list[str], int, int]:
    """Check all relative links and anchors across selected docs under `root`.

    Returns `(problems, files_checked, links_checked)`.
    """
    root_resolved = root.resolve()
    doc_files = collect_doc_files(root_resolved, paths)
    if not doc_files:
        return [f"no documentation files found under {root_resolved}"], 0, 0

    problems: list[str] = []
    anchor_cache: dict[Path, set[str]] = {}
    links_checked = 0
    files_checked = 0

    def anchors_for(md_path: Path) -> set[str]:
        resolved = md_path.resolve()
        if resolved not in anchor_cache:
            anchor_cache[resolved] = extract_anchors(resolved)
        return anchor_cache[resolved]

    def display_path(path: Path) -> str:
        resolved = path.resolve()
        if resolved.is_relative_to(root_resolved):
            return resolved.relative_to(root_resolved).as_posix()
        return str(path)

    for source in doc_files:
        if not source.is_file():
            problems.append(f"{display_path(source)}: documentation file does not exist")
            continue

        files_checked += 1
        rel_source = display_path(source)

        for lineno, raw_target in extract_links(source):
            target = parse_target(raw_target)
            if target is None:
                links_checked += 1
                problems.append(f"{rel_source}:{lineno}: empty or malformed markdown link target")
                continue

            if SCHEME_RE.match(target) or target.startswith("//"):
                continue

            links_checked += 1
            path_part, sep, fragment = target.partition("#")
            path_part = urllib.parse.unquote(path_part.split("?", 1)[0])
            fragment = urllib.parse.unquote(fragment)

            if not path_part:
                if not sep or not fragment:
                    problems.append(f"{rel_source}:{lineno}: empty anchor fragment '{target}'")
                elif fragment not in anchors_for(source):
                    problems.append(
                        f"{rel_source}:{lineno}: broken in-file anchor '#{fragment}' "
                        f"(heading not found in {rel_source})"
                    )
                continue

            if path_part.startswith("/"):
                problems.append(
                    f"{rel_source}:{lineno}: non-relative link target '{target}' "
                    f"(use a relative path)"
                )
                continue

            resolved_target = (source.parent / path_part).resolve()
            if not resolved_target.is_relative_to(root_resolved):
                problems.append(
                    f"{rel_source}:{lineno}: link target '{target}' escapes repository root"
                )
                continue

            if not resolved_target.exists():
                problems.append(
                    f"{rel_source}:{lineno}: broken relative link '{target}' (file not found)"
                )
                continue

            if sep == "#" and fragment:
                if resolved_target.is_dir():
                    problems.append(
                        f"{rel_source}:{lineno}: broken anchor '{target}' (target is a directory)"
                    )
                elif resolved_target.suffix.lower() == ".md":
                    if fragment not in anchors_for(resolved_target):
                        problems.append(
                            f"{rel_source}:{lineno}: broken anchor '#{fragment}' in '{target}' "
                            f"(heading not found in {display_path(resolved_target)})"
                        )
                else:
                    line_match = LINE_ANCHOR_RE.fullmatch(fragment)
                    if line_match:
                        target_text = resolved_target.read_text(encoding="utf-8", errors="replace")
                        total_lines = len(target_text.splitlines())
                        start_line = int(line_match.group(1))
                        end_line = int(line_match.group(2)) if line_match.group(2) else start_line
                        if start_line < 1 or end_line < start_line or end_line > total_lines:
                            problems.append(
                                f"{rel_source}:{lineno}: broken line anchor '#{fragment}' "
                                f"in '{target}'"
                            )

    return problems, files_checked, links_checked


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=REPO_ROOT,
        help="Repository root containing README.md, CONTRIBUTING.md, SCHEMA.md, and docs/",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Optional explicit markdown files or directories to check",
    )
    args = parser.parse_args(argv)

    problems, files_checked, links_checked = check_links(
        args.root,
        args.paths if args.paths else None,
    )
    if problems:
        for problem in problems:
            print(f"check_docs_links: {problem}", file=sys.stderr)
        print(f"check_docs_links: {len(problems)} broken link(s) found", file=sys.stderr)
        return 1

    print(
        f"check_docs_links: checked {files_checked} file(s), "
        f"{links_checked} relative link(s), 0 broken"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
