"""Optional project navigation: one canonical home per document, no duplicate specs."""

from pathlib import Path
from urllib.parse import quote

import tomli_w

from ai_dlc.documentation.document_files import (
    create_document,
    directory,
    read_document,
    validate_parent,
)
from ai_dlc.files import inside

PRESETS = {None, "5-pillar", "organized"}


def plan_documents(root: Path, project_name: str) -> dict[str, bytes]:
    """Plan additive navigation using existing layout; never relocate authored documents."""
    root = root.absolute()
    try:
        with directory(root):
            pass
    except FileNotFoundError:
        pass
    output: dict[str, bytes] = {}
    categories = [
        ("architecture", "Architecture", ["docs/architecture.md", "docs/architecture/README.md"]),
        ("decision", "Decisions", ["docs/decisions/README.md", "docs/adr/README.md"]),
        ("runbook", "Operations", ["docs/runbooks/README.md"]),
        ("reference", "Reference", ["docs/reference/README.md"]),
    ]
    # Validate every possible destination before creating any file.
    candidates = ["docs/index.md", "docs/catalog.toml"]
    candidates.extend(p for _, _, paths in categories for p in paths)
    for relative in candidates:
        path = inside(root, relative)
        validate_parent(path)
        if path.exists() and not path.is_file():
            raise ValueError(f"Document destination is not a regular file: {relative}")
        if path.exists():
            read_document(path)
    entries = []
    links = []
    for kind, label, choices in categories:
        selected = next((p for p in choices if (root / p).is_file()), choices[0])
        if (
            kind == "architecture"
            and (root / "docs/architecture").is_dir()
            and not (root / "docs/architecture.md").exists()
        ):
            selected = "docs/architecture/README.md"
        # An existing ADR directory remains its project's decision location.
        if (
            kind == "decision"
            and (root / "docs/adr").is_dir()
            and not (root / "docs/decisions").exists()
        ):
            selected = "docs/adr/README.md"
        if not (root / selected).exists():
            siblings = (
                sorted((root / selected).parent.glob("*.md"))
                if selected.endswith("/README.md")
                else []
            )
            navigation = "".join(
                f"- [{p.stem}]({quote(p.name)})\n"
                for p in siblings
                if not p.is_symlink() and p.is_file()
            )
            output[selected] = (
                f"# {label}\n\nStatus: draft navigation. Owner: unassigned.\n\n"
                "Link existing authoritative documents here before creating new ones. "
                "Record decisions and evidence; do not invent system facts.\n\n" + navigation
            ).encode()
        links.append(f"- [{label}]({Path(selected).relative_to('docs').as_posix()})")
        entries.append(
            {"id": kind, "path": selected, "kind": kind, "owner": "unassigned", "status": "draft"}
        )
    spec_text = (
        "[OpenSpec](../openspec/)"
        if (root / "openspec").is_dir()
        else "`openspec/` (initialize with the selected OpenSpec tool when needed)"
    )
    index = (
        f"# {project_name} documentation\n\n"
        "This map points to canonical documents; it is not another copy of their content.\n\n"
        + "\n".join(links[:2])
        + f"\n- Specifications: {spec_text}\n"
        + "\n".join(links[2:])
        + "\n\n"
        "## Ownership and upkeep\n\n"
        "Formal specifications and change artifacts live only in `openspec/`. "
        "Repository architecture, decisions, operations and reference live in `docs/`. "
        "Personal journals stay in Obsidian. Existing team pages remain authoritative in Confluence.\n\n"
        "Search this map, the catalog and the selected specification tool before creating a document. "
        "Extend the canonical document when it answers the same question. "
        "Record an owner, lifecycle status and an explicit review date in `docs/catalog.toml`; "
        "a file modification date is not evidence of accuracy. "
        "Identify derived summaries with source URL, available version and retrieval date. "
        "Supersede outdated documents with a replacement link; never silently delete them.\n\n"
        "Run `ai-dlc project docs-check` to surface coverage and review gaps. "
        "Checks do not certify semantic freshness. Review sources when related code or decisions change. "
        "Publish only explicitly reviewed shared drafts; following links never authorizes copying "
        "private notes or synchronizing a vault or Confluence space.\n"
    )
    if not (root / "docs/index.md").exists():
        output["docs/index.md"] = index.encode()
    if not (root / "docs/catalog.toml").exists():
        output["docs/catalog.toml"] = tomli_w.dumps({"schema": 1, "documents": entries}).encode()
    return output


def scaffold_5_pillar_docs(docs_root: Path, project_name: str) -> list[str]:
    """Compatibility entry point for the organized preset, using exclusive creation."""
    if docs_root.name != "docs":
        raise ValueError("The document root must be the project docs directory")
    planned = plan_documents(docs_root.parent, project_name)
    created = []
    try:
        for relative, body in planned.items():
            if create_document(docs_root.parent / relative, body):
                created.append(str(Path(relative).relative_to("docs")))
            else:
                raise ValueError(f"Document appeared after preview: {relative}")
    except (OSError, ValueError) as exc:
        raise ValueError(
            f"Document setup stopped; retained created files {created}: {exc}"
        ) from exc
    return created


def initialize_documents(
    root: Path | str = ".", *, preset: str = "organized", apply: bool = False
) -> dict:
    root = Path(root).absolute()
    if preset not in PRESETS or preset is None:
        raise ValueError("Unknown documentation preset")
    planned = plan_documents(root, root.name)
    if apply:
        scaffold_5_pillar_docs(root / "docs", root.name)
    return {"status": "applied" if apply else "planned", "files": sorted(planned)}
