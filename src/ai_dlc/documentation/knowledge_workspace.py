"""Additive personal workspace navigation; repository documents remain in Git."""

from pathlib import Path

from ai_dlc.documentation import document_files
from ai_dlc.documentation.vault_link import plan_vault_link
from ai_dlc.files import inside


def _template(kind: str) -> bytes:
    sections = {
        "daily": "## Focus\n\n## Work and source links\n\n## Selected learning\n",
        "question": "## Question\n\n## Context and source links\n\n## Resolution evidence\n",
        "learning": "## Learning\n\n## Evidence and source links\n\n## Applicability and uncertainty\n\n## Next review\n",
    }
    return (
        f'---\nnote_kind: {kind}\nproject: ""\nstatus: '
        + ("open" if kind == "question" else "draft")
        + '\nsource: ""\nreviewed_on: ""\n---\n\n'
        "Set project to a link to the project workspace. Keep personal interpretation distinct from source evidence.\n\n"
        + sections[kind]
    ).encode()


def _view(kind: str, condition: str = "") -> bytes:
    filters = f"    - 'note_kind == \"{kind}\"'\n"
    if condition:
        filters += f"    - '{condition}'\n"
    return (
        "filters:\n  and:\n"
        + filters
        + 'views:\n  - type: table\n    name: "'
        + kind.title()
        + '"\n    order:\n      - file.name\n      - project\n      - status\n      - source\n      - reviewed_on\n'
    ).encode()


def setup_workspace(
    root: Path | str = ".",
    *,
    vault: Path | str | None = None,
    name: str | None = None,
    bases: bool = False,
    apply: bool = False,
) -> dict:
    root = Path(root).absolute()
    if not root.is_dir():
        raise ValueError("Project repository is missing; repair its machine-local binding first.")
    portal = plan_vault_link(root, vault=vault, name=name)
    project = portal.name
    body = (
        f'---\nnote_kind: project\nproject: "{project}"\nstatus: active\nsource: "{root.as_uri()}"\n---\n\n'
        f"# {project} workspace\n\n"
        f"Canonical project documents: [[Projects/{project}]]. This note organizes personal work; the linked repository owns project documentation.\n\n"
        "## Current focus\n\nRecord the question or outcome you are working on; link the work item and relevant OpenSpec change.\n\n"
        "## Daily work, questions and learnings\n\nLink selected notes here and set their project property to this workspace. Backlinks reveal related notes without importing their contents.\n\n"
        "Templates: [[AI-DLC/Templates/daily]], [[AI-DLC/Templates/question]], [[AI-DLC/Templates/learning]].\n\n"
        "## Documentation review\n\nRun the project documentation impact/check workflow in the repository; link reviewed findings here when relevant. Review age is a prompt to inspect, not proof of inaccuracy.\n\n"
        "## Personal notes\n\n"
    ).encode()
    planned = {f"Projects/{project}.md": portal.body, f"Projects/{project}-workspace.md": body}
    planned.update(
        {
            f"AI-DLC/Templates/{kind}.md": _template(kind)
            for kind in ("daily", "question", "learning")
        }
    )
    if bases:
        planned.update(
            {
                "AI-DLC/Views/projects.base": _view("project", 'status == "active"'),
                "AI-DLC/Views/questions.base": _view("question", 'status != "resolved"'),
                "AI-DLC/Views/learnings.base": _view("learning", 'status != "reviewed"'),
            }
        )
    files = []
    for relative, content in planned.items():
        destination = inside(portal.vault, relative)
        document_files.validate_parent(destination)
        try:
            current = document_files.read_document(destination)
        except FileNotFoundError:
            current = None
        # Notes may have personal additions. Templates/views must remain identical.
        if current is not None and not (
            current.startswith(content) if relative.startswith("Projects/") else current == content
        ):
            raise ValueError(
                f"Authored workspace content conflicts: {relative}. Preserve it and choose another project name or reconcile manually."
            )
        files.append(
            {
                "path": relative,
                "action": "create" if current is None else "unchanged",
                "content": content.decode(),
            }
        )
    result = {
        "status": "preview",
        "mode": "linked-workspace",
        "files": files,
        "workspace": f"Projects/{project}-workspace.md",
        "created": [],
        "limitations": [
            "Existing portals remain unchanged; the workspace is an additive personal navigation companion.",
            "No repository bodies, private summaries or remote documents are copied.",
        ],
        "missing_sources": [p for p in ("docs/index.md", "openspec") if not (root / p).exists()],
    }
    if apply:
        for file in files:
            if file["action"] != "create":
                continue
            try:
                if not document_files.create_document(
                    inside(portal.vault, file["path"]), file["content"].encode()
                ):
                    raise ValueError("Destination appeared during workspace setup: " + file["path"])
                result["created"].append(file["path"])
            except (OSError, ValueError) as exc:
                retained = sorted(set(result["created"] + [file["path"]]))
                cause = exc.__cause__ or exc
                raise ValueError(
                    f"{cause}; retained or attempted workspace paths: {retained}. Inspect partial output before retrying."
                ) from exc
        result["status"] = "applied"
    return result
