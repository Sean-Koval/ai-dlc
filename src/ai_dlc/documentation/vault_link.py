"""Machine-local Obsidian project portals pointing to canonical repository documents."""

import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ai_dlc.config import resolve_runtime
from ai_dlc.documentation.document_files import (
    create_document,
    directory,
    read_document,
    validate_parent,
)
from ai_dlc.documentation.moc import PRESETS, plan_documents
from ai_dlc.documentation.vault_mount import VaultMountResult, mount_vault
from ai_dlc.files import inside


@dataclass(frozen=True)
class VaultLinkResult:
    project_root: str
    project_name: str
    docs_path: str
    vault_path: str
    link_path: str
    created_link: bool
    created_docs: bool
    scaffolded_docs: list[str]
    status: str
    mode: str = "portal"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VaultLinkPlan:
    root: Path
    vault: Path
    name: str
    portal: Path
    body: bytes
    exists: bool

    def preview(self) -> dict:
        return {
            "mode": "portal",
            "path": str(self.portal),
            "source": str(self.root),
            "action": "unchanged" if self.exists else "create",
            "content": self.body.decode(),
        }


def plan_vault_link(
    root: Path,
    *,
    vault: Path | str | None = None,
    name: str | None = None,
    environ: Mapping[str, str] | None = None,
    home: Path | None = None,
    enrollment_paths: Any = None,
) -> VaultLinkPlan:
    root = root.absolute()
    project_name = root.name if name is None else name
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}", project_name):
        raise ValueError(
            "Project name must be one safe filename (letters, digits, dot, dash, underscore)."
        )
    if vault is None:
        resolved = resolve_runtime(
            root, environ=environ, home=home, enrollment_paths=enrollment_paths
        )
        vault = resolved.values.get("paths", {}).get("vault")
    if vault is None:
        raise ValueError("Configure paths.vault in machine configuration or pass --vault.")
    vault_path = Path(vault).expanduser().absolute()
    if not vault_path.is_dir():
        raise ValueError("The configured vault must already exist.")
    with directory(vault_path):
        pass
    # No binding is published through symlinks, including legacy PR28 directory links.
    legacy = vault_path / "Projects" / project_name
    if legacy.is_symlink() or legacy.exists():
        raise ValueError(
            "Legacy project path exists; inspect it and choose a new portal name. No link was removed."
        )
    portal = inside(vault_path, f"Projects/{project_name}.md")
    validate_parent(portal)
    docs = inside(root, "docs")
    inside(root, "openspec")
    body = (
        f"# {project_name}\n\n"
        "Repository documents are canonical. These links do not copy or synchronize content.\n\n"
        f"- [Project documentation]({docs.as_uri()})\n"
        f"- [Documentation map]({(docs / 'index.md').as_uri()}) (available after docs-init)\n"
        f"- [Formal specifications]({(root / 'openspec').as_uri()}) "
        "(available after OpenSpec initialization)\n\n"
        "Keep personal observations below this portal, or in daily notes. "
        "Repository edits use the project workflow. Publication to Confluence is a separate reviewed action.\n"
    ).encode()
    exists = portal.exists()
    if exists and not read_document(portal).startswith(body):
        raise ValueError(
            "Portal conflicts with authored content or a different source; choose a new name."
        )
    return VaultLinkPlan(root, vault_path, project_name, portal, body, exists)


def apply_vault_link(plan: VaultLinkPlan) -> bool:
    # Revalidate identity/content immediately before exclusive creation, without replacing anything.
    current = plan_vault_link(plan.root, vault=plan.vault, name=plan.name)
    if current.body != plan.body:
        raise ValueError("Portal source changed; preview again.")
    if current.exists:
        return False
    if not create_document(current.portal, current.body):
        raise ValueError("Portal appeared during setup; preserved it. Inspect and retry.")
    return True


def link_vault(
    root: Path | str = ".",
    *,
    vault: Path | str | None = None,
    name: str | None = None,
    force: bool = False,
    mode: str = "portal",
    adopt: bool = False,
    create_docs: bool = True,
    docs_preset: str | None = None,
    apply: bool = True,
    environ: Mapping[str, str] | None = None,
    home: Path | None = None,
    enrollment_paths: Any = None,
) -> VaultLinkResult | VaultMountResult:
    """Create an additive project portal. Force never grants permission to overwrite notes."""
    project_root = Path(root).absolute()
    if not project_root.is_dir():
        raise ValueError("Project directory does not exist.")
    if docs_preset not in PRESETS:
        raise ValueError("Unknown documentation preset")
    if mode not in {"portal", "mount"}:
        raise ValueError("Unknown vault link mode; choose portal or mount.")
    if mode == "mount":
        if docs_preset:
            raise ValueError("Initialize documentation separately before mounting.")
        if vault is None:
            resolved = resolve_runtime(
                project_root, environ=environ, home=home, enrollment_paths=enrollment_paths
            )
            vault = resolved.values.get("paths", {}).get("vault")
        if vault is None:
            raise ValueError("Configure paths.vault or pass --vault.")
        return mount_vault(project_root, Path(vault), name, adopt=adopt, apply=apply)
    if adopt:
        raise ValueError("Adoption applies only to mount mode.")
    plan = plan_vault_link(
        project_root,
        vault=vault,
        name=name,
        environ=environ,
        home=home,
        enrollment_paths=enrollment_paths,
    )
    planned = plan_documents(project_root, project_root.name) if docs_preset else {}
    if not (project_root / "docs").is_dir() and not planned:
        raise ValueError(
            "Project docs are missing; use --docs-preset organized to initialize navigation."
        )
    had_docs = (project_root / "docs").is_dir()
    if not had_docs and not create_docs:
        raise ValueError("Project docs directory does not exist.")
    created: list[str] = []
    linked = False
    if apply:
        try:
            for relative, content in planned.items():
                if not create_document(project_root / relative, content):
                    raise ValueError(f"Document appeared during setup: {relative}")
                created.append(relative)
            linked = apply_vault_link(plan)
        except (OSError, ValueError) as exc:
            raise ValueError(f"Setup stopped; retained created documents {created}. {exc}") from exc
    return VaultLinkResult(
        str(project_root),
        plan.name,
        str(project_root / "docs"),
        str(plan.vault),
        str(plan.portal),
        linked,
        apply and not had_docs,
        created,
        "applied" if apply else "planned",
    )
