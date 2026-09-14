"""Repository-owned FDE engagement scaffolding; no publication or vault access."""

from __future__ import annotations

import json
import re
import shlex
from pathlib import Path
from typing import Any

import yaml

from ai_dlc.config import load_project
from ai_dlc.files import inside

# Folder names are the documented FDE engagement convention, independent of any account.
STAGES = (
    (
        "01_discover",
        "Discover",
        "ACTIVE",
        "Customer context, stakeholders, workflows and constraints.",
        "Stakeholders have reviewed the current workflow, evidence and constraints.",
    ),
    (
        "02_frame",
        "Frame",
        "GATED",
        "Problem statement, baseline and target metrics, scope boundaries.",
        "Owners agree on the problem, measurable outcomes and scope boundaries.",
    ),
    (
        "03_design",
        "Design",
        "GATED",
        "Solution architecture, interfaces, user experience and risks.",
        "Owners have reviewed feasibility, interfaces, risks and the validation approach.",
    ),
    (
        "04_build",
        "Build",
        "PLANNED",
        "Working increments, implementation and automated verification.",
        "The agreed acceptance and regression checks pass for the working solution.",
    ),
    (
        "05_deploy",
        "Deploy",
        "PLANNED",
        "Deployment, observability, recovery and production arrangements.",
        "Operations owners have reviewed deployment evidence, monitoring and recovery.",
    ),
    (
        "06_enable",
        "Enable",
        "PLANNED",
        "Operator guidance, user onboarding, adoption and feedback.",
        "Users and operators can use, support and improve the delivered workflow.",
    ),
    (
        "07_expand",
        "Expand",
        "PLANNED",
        "Measured outcomes, extension opportunities and self-service roadmap.",
        "Sponsors have reviewed results and decided whether and how to extend value.",
    ),
)


def _destination(root: Path, slug: str, docs_dir: str | None) -> Path:
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,99}", slug):
        raise ValueError("FDE slug must use lowercase letters, digits, underscores or hyphens")
    if docs_dir is None:
        config = load_project(root) if (root / "ai-dlc.toml").is_file() else {}
        settings = config.get("project", {}).get("fde", {})
        if not isinstance(settings, dict):
            raise ValueError("project.fde must be a table")
        docs_dir = settings.get("docs_dir", "docs/fde_engagements")
    if not isinstance(docs_dir, str):
        raise TypeError("project.fde.docs_dir must be a repository-relative directory")
    _line(docs_dir, "FDE docs directory")
    directory = Path(docs_dir)
    if len(directory.parts) < 2 or directory.parts[0] != "docs":
        raise ValueError("FDE docs directory must be a dedicated subdirectory beneath docs/")
    # Shared boundary rejects traversal and every symlink, including internal redirects.
    return inside(root, str(directory / slug))


def _line(value: str, name: str) -> str:
    if not value.strip() or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError(f"{name} must be a nonempty single line")
    return value


def _frontmatter(metadata: dict[str, Any]) -> str:
    # JSON scalars and arrays are also YAML, so user-supplied punctuation stays data.
    return (
        "---\n"
        + "".join(
            f"{key}: {json.dumps(value, ensure_ascii=False)}\n" for key, value in metadata.items()
        )
        + "---\n\n"
    )


def scaffold_engagement(
    root: Path,
    slug: str,
    *,
    title: str,
    docs_dir: str | None = None,
    space: str | None = None,
    parent: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    root = root.resolve()
    destination = _destination(root, slug, docs_dir)
    _line(title, "Title")
    if (space is None) != (parent is None):
        raise ValueError("Provide both --space and --parent, or neither")
    if space is not None:
        _line(space, "Space")
        if not parent or not re.fullmatch(r"[1-9][0-9]*", parent):
            raise ValueError("Parent page ID must be a positive decimal ID")
    if destination.exists():
        raise ValueError(f"Engagement already exists; refusing to overwrite: {destination}")
    relative_directory = destination.parent.relative_to(root).as_posix()
    command = f"ai-dlc fde check {slug} --docs-dir {shlex.quote(relative_directory)}"
    fence = "`" * (max((len(run) for run in re.findall(r"`+", command)), default=0) + 1)
    command_markdown = f"{fence}{command}{fence}"
    metadata: dict[str, Any] = {"title": title, "engagement": slug, "tags": ["fde", "fde-kit"]}
    if space is not None:
        metadata.update(confluence_space_key=space, confluence_parent_page_id=parent)
    charter = _frontmatter(metadata) + f"# {title}\n\n"
    charter += (
        "## Executive sponsors\n\nRecord sponsors, delivery owners and decision responsibilities.\n\n"
        "## Business goals\n\nRecord the customer outcome, baseline, target measures and scope.\n\n"
        f"## Stage dashboard\n\nStage pages own current status and exit evidence. Run {command_markdown} "
        "to inspect the current states; this table links their canonical records.\n\n"
        "| Stage | Current status and exit evidence |\n| --- | --- |\n"
    )
    files: dict[str, str] = {}
    for folder, name, status, focus, criteria in STAGES:
        charter += f"| {name} | [{folder}]({folder}/_index.md) |\n"
        page_metadata = {
            "title": f"{title}: {name}",
            "engagement": slug,
            "stage": folder,
            "status": status,
            "exit_criteria_met": False,
            "exit_evidence": "",
            "tags": ["fde", "fde-kit"],
        }
        files[f"{folder}/_index.md"] = _frontmatter(page_metadata) + (
            f"# {name}\n\n{focus}\n\n"
            "## Deliverables\n\nLink reviewed Markdown deliverables stored in this stage folder.\n\n"
            f"## Exit criteria\n\n{criteria}\n\n"
            "Record the review or evidence in `exit_evidence` before setting "
            "`exit_criteria_met: true`. All earlier stage exits must be satisfied "
            "before this stage becomes ACTIVE or records completed exit criteria.\n"
        )
    charter += (
        "\n## Publication\n\nConfluence publication is unavailable in this scaffold. "
        "Optional space and parent metadata are destination hints, not remote page bindings. "
        "Stage pages are intended parents for stage deliverables; no remote IDs have been assigned.\n"
    )
    files["_index.md"] = charter
    files["AGENTS.md"] = (
        "# Engagement documentation guidance\n\n"
        "Author and review team documents in this engagement's seven numbered stage folders. "
        "Keep each `_index.md` as its stage landing page; put child deliverables beside it. "
        "Keep engagement documents separate from commercial product documentation.\n\n"
        "The charter records any explicitly supplied Confluence space and engagement parent. "
        "Do not infer company accounts, page identities or authorization from these hints.\n\n"
        "Stage frontmatter owns status (ACTIVE, GATED or PLANNED), exit_criteria_met and "
        "exit_evidence. Review exit evidence before activating downstream stages. "
        "If assumptions change, reopen the relevant exit and gate downstream stages again.\n\n"
        f"From the repository root, validate with {command_markdown}. Preview a new workspace with "
        "`ai-dlc fde scaffold <slug> --title <title> --dry-run`. This validates local structure "
        "and metadata; it does not validate XHTML fidelity.\n\n"
        "Confluence conversion, dry-run XHTML verification and syncing are unavailable here. "
        "Do not invent sync commands or successful publication records. Use only a separately "
        "reviewed existing connection if explicitly authorized. Publish selected reviewed "
        "team documents only; never scan, mirror or publish private Obsidian vaults. "
        "Private source links do not authorize reading or including linked notes. "
        "Relevant team pages may be read on request. A requested local summary records its "
        "source URL, available version and retrieval date; explicit refresh preserves personal "
        "annotations and reports stale or inaccessible sources honestly. Guidance is not an "
        "access control and does not qualify the native connection.\n\n"
        "CLAUDE.md references this rule. For another harness, explicitly include this AGENTS.md "
        "through its supported project guidance mechanism before using the engagement.\n"
    )
    files["CLAUDE.md"] = "@AGENTS.md\n"
    output_files = {
        f"{destination.relative_to(root).as_posix()}/{path}": body for path, body in files.items()
    }
    if not dry_run:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.mkdir()  # Exclusive: a competing scaffold must never reuse this directory.
        for path, content in files.items():
            target = inside(destination, path)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("x", encoding="utf-8") as stream:
                stream.write(content)
    return {
        "status": "scaffolded" if not dry_run else "preview",
        "applied": not dry_run,
        "engagement": destination.relative_to(root).as_posix(),
        "files": output_files,
        "publication": "unavailable",
    }


class _UniqueKeyLoader(yaml.SafeLoader):
    """Keep gate metadata unambiguous without changing PyYAML's global loaders."""

    def construct_mapping(self, node, deep=False):
        if isinstance(node, yaml.MappingNode):
            self.flatten_mapping(node)
            seen = set()
            for key_node, _ in node.value:
                key = self.construct_object(key_node, deep=deep)
                try:
                    if key in seen:
                        raise yaml.YAMLError("duplicate mapping key")
                    seen.add(key)
                except TypeError:
                    raise yaml.YAMLError("unhashable mapping key") from None
        return super().construct_mapping(node, deep=deep)


def _metadata(root: Path, path: Path) -> dict[str, Any]:
    inside(root, str(path.relative_to(root)))
    if not path.is_file() or path.stat().st_size > 256_000:
        raise ValueError("landing page missing or exceeds 256000 bytes")
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        raise ValueError("landing page requires YAML frontmatter")
    try:
        result = yaml.load("\n".join(lines[1 : lines.index("---", 1)]), Loader=_UniqueKeyLoader)
    except yaml.YAMLError:
        raise ValueError("invalid YAML frontmatter") from None
    if not isinstance(result, dict):
        raise TypeError("frontmatter must be a mapping")
    return result


def check_engagement(root: Path, slug: str, *, docs_dir: str | None = None) -> dict[str, Any]:
    root = root.resolve()
    destination = _destination(root, slug, docs_dir)
    findings: list[str] = []
    stages: list[dict[str, Any]] = []
    unmet: list[str] = []
    for folder in ["", *(stage[0] for stage in STAGES)]:
        path = destination / folder / "_index.md"
        label = folder or "charter"
        try:
            metadata = _metadata(root, path)
            title = metadata.get("title")
            if (
                not isinstance(title, str)
                or not title.strip()
                or metadata.get("engagement") != slug
            ):
                raise ValueError("title and matching engagement identity are required")
            if not folder:
                continue
            status = metadata.get("status")
            complete = metadata.get("exit_criteria_met")
            evidence = metadata.get("exit_evidence")
            if metadata.get("stage") != folder:
                raise ValueError("stage identity must match its folder")
            if status not in ("ACTIVE", "GATED", "PLANNED"):
                raise ValueError("status must be ACTIVE, GATED or PLANNED")
            if type(complete) is not bool or not isinstance(evidence, str):
                raise ValueError("exit_criteria_met must be boolean and exit_evidence must be text")
            if complete and not evidence.strip():
                raise ValueError("completed exit criteria require review evidence")
            if (status == "ACTIVE" or complete) and unmet:
                findings.append(f"{label}: unmet earlier stage exit criteria: {', '.join(unmet)}")
            stages.append(
                {
                    "stage": folder,
                    "status": status,
                    "exit_criteria_met": complete,
                    "exit_evidence": evidence,
                }
            )
            if not complete:
                unmet.append(folder)
        except (ValueError, TypeError, OSError) as error:
            findings.append(f"{label}: {error}")
            if folder:
                unmet.append(folder)
    return {
        "valid": not findings,
        "engagement": destination.relative_to(root).as_posix(),
        "stages": stages,
        "findings": findings,
        "publication": "unavailable",
    }
