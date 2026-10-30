"""Keep docs-site links resolvable: links that leave the built site become GitHub URLs.

The documentation site builds ``docs/`` without ``mkdocs.yml``'s ``exclude_docs``
(``archive/``, ``verification/``, ``reviews/``, ``catalog.toml``). A relative Markdown link from
a built page to a file outside that set (``../src/...``, ``../../AGENTS.md``, an
archived note, a directory without an index) renders as a 404 on the site while it
works on GitHub. This script rewrites such links to
``https://github.com/Sean-Koval/ai-dlc/blob/main/<path>`` (``tree`` for
directories), keeping any ``#anchor``. Links inside the site and absolute URLs are
left alone; fenced and inline code is skipped.

    python scripts/docs_site_links.py --check   # exit 1 and list links that would change
    python scripts/docs_site_links.py --write   # rewrite them in place
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = "docs"
GITHUB = "https://github.com/Sean-Koval/ai-dlc"
BRANCH = "main"
# Mirrors mkdocs.yml exclude_docs; tests keep the two in step.
EXCLUDED = ("archive/*", "verification/*", "reviews/*", "catalog.toml")
LINK = re.compile(
    r"(?<!!)\[(?P<text>[^\]\n]*)\]\((?P<target><[^>\n]+>|[^)\s]+)(?P<title>\s+\"[^\"\n]*\")?\)"
)
FENCE = re.compile(r"^\s*(```|~~~)")
INLINE_CODE = re.compile(r"`[^`\n]*`")


def excluded(relative: str) -> bool:
    """Whether a docs-relative path is left out of the site."""
    return any(fnmatch.fnmatch(relative, pattern) for pattern in EXCLUDED)


def built_pages(root: Path) -> list[Path]:
    docs = root / DOCS
    return [
        path
        for path in sorted(docs.rglob("*.md"))
        if not excluded(path.relative_to(docs).as_posix())
    ]


def _on_site(root: Path, target: Path) -> bool:
    docs = (root / DOCS).resolve()
    try:
        relative = target.relative_to(docs).as_posix()
    except ValueError:
        return False
    if excluded(relative) or not target.exists():
        return False
    if target.is_dir():
        return (target / "index.md").is_file() or (target / "README.md").is_file()
    return True


def rewrite_target(root: Path, page: Path, target: str) -> str | None:
    """The GitHub URL for a link that would leave the site, or None to keep it."""
    raw = target[1:-1] if target.startswith("<") else target
    if not raw or raw.startswith(("#", "/")) or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", raw):
        return None
    path_part, _, anchor = raw.partition("#")
    if not path_part:
        return None
    resolved = (page.parent / path_part).resolve()
    if _on_site(root, resolved):
        return None
    try:
        repository_path = resolved.relative_to(root.resolve()).as_posix()
    except ValueError:
        return None  # outside the repository: leave it for review
    if not resolved.exists():
        return None  # broken everywhere; `ai-dlc docs check` reports those
    kind = "tree" if resolved.is_dir() else "blob"
    url = f"{GITHUB}/{kind}/{BRANCH}/{repository_path}"
    return url + (f"#{anchor}" if anchor else "")


def rewrite_text(root: Path, page: Path, text: str) -> tuple[str, list[tuple[str, str]]]:
    changes: list[tuple[str, str]] = []
    out: list[str] = []
    fenced = False
    for line in text.splitlines(keepends=True):
        if FENCE.match(line):
            fenced = not fenced
            out.append(line)
            continue
        if fenced:
            out.append(line)
            continue
        code = [m.span() for m in INLINE_CODE.finditer(line)]

        def replace(match: re.Match[str], code: list[tuple[int, int]] = code) -> str:
            if any(start <= match.start() < end for start, end in code):
                return match.group(0)
            url = rewrite_target(root, page, match.group("target"))
            if url is None:
                return match.group(0)
            changes.append((match.group("target"), url))
            return f"[{match.group('text')}]({url}{match.group('title') or ''})"

        out.append(LINK.sub(replace, line))
    return "".join(out), changes


def run(root: Path, write: bool) -> dict[str, list[tuple[str, str]]]:
    found: dict[str, list[tuple[str, str]]] = {}
    for page in built_pages(root):
        text = page.read_text()
        updated, changes = rewrite_text(root, page, text)
        if changes:
            found[page.relative_to(root).as_posix()] = changes
            if write:
                page.write_text(updated)
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    found = run(args.root, args.write)
    total = sum(len(v) for v in found.values())
    for page, changes in found.items():
        for old, new in changes:
            print(f"{page}: {old} -> {new}")
    if args.check and total:
        print(
            f"{total} docs-site link(s) leave the site; run "
            "`python scripts/docs_site_links.py --write`",
            file=sys.stderr,
        )
        return 1
    print(f"{total} link(s) {'rewritten' if args.write else 'to rewrite'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
