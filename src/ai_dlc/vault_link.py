"""Obsidian vault linking and project documentation integration."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from ai_dlc.config import resolve_runtime
from ai_dlc.moc import scaffold_5_pillar_docs


@dataclass(frozen=True)
class VaultLinkResult:
    project_root: Path
    project_name: str
    docs_path: Path
    vault_path: Path
    link_path: Path
    created_link: bool
    created_docs: bool
    gitignore_updated: bool
    scaffolded_docs: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "project_root": str(self.project_root),
            "project_name": self.project_name,
            "docs_path": str(self.docs_path),
            "vault_path": str(self.vault_path),
            "link_path": str(self.link_path),
            "created_link": self.created_link,
            "created_docs": self.created_docs,
            "gitignore_updated": self.gitignore_updated,
            "scaffolded_docs": self.scaffolded_docs,
        }


def ensure_gitignore_entries(project_root: Path, entries: list[str]) -> bool:
    """Ensure specific entries are in .gitignore, appending them if missing."""
    gitignore_file = project_root / ".gitignore"
    existing_lines = []
    if gitignore_file.exists():
        existing_lines = [
            line.strip() for line in gitignore_file.read_text(encoding="utf-8").splitlines()
        ]

    missing = [entry for entry in entries if entry not in existing_lines]
    if not missing:
        return False

    content = gitignore_file.read_text(encoding="utf-8") if gitignore_file.exists() else ""
    if content and not content.endswith("\n"):
        content += "\n"
    content += "\n# Obsidian vault artifacts\n" + "\n".join(missing) + "\n"
    gitignore_file.write_text(content, encoding="utf-8")
    return True


def link_vault(
    root: Path | str = ".",
    *,
    vault: Path | str | None = None,
    name: str | None = None,
    force: bool = False,
    create_docs: bool = True,
    docs_preset: str | None = None,
    environ: Mapping[str, str] | None = None,
    home: Path | None = None,
    enrollment_paths: Any = None,
) -> VaultLinkResult:
    project_root = Path(root).resolve()
    if not project_root.is_dir():
        raise ValueError(f"Project directory does not exist: {project_root}")

    vault_path: Path | None = None
    if vault is not None:
        vault_path = Path(vault).expanduser().resolve()
    else:
        resolved = resolve_runtime(
            project_root,
            environ=environ,
            home=home,
            enrollment_paths=enrollment_paths,
        )
        cfg_vault = resolved.values.get("paths", {}).get("vault")
        if cfg_vault:
            vault_path = Path(cfg_vault).expanduser().resolve()

    if vault_path is None or not vault_path.is_dir():
        raise ValueError(
            "Configure paths.vault in your machine configuration or pass --vault <path>"
        )

    project_name = name or project_root.name
    docs_dir = project_root / "docs"
    created_docs = False
    if not docs_dir.exists():
        if create_docs:
            docs_dir.mkdir(parents=True, exist_ok=True)
            created_docs = True
        else:
            raise ValueError(f"Project docs directory does not exist: {docs_dir}")

    scaffolded_docs: list[str] = []
    if docs_preset == "5-pillar":
        scaffolded_docs = scaffold_5_pillar_docs(docs_dir, project_name)

    projects_dir = vault_path / "Projects"
    projects_dir.mkdir(parents=True, exist_ok=True)

    link_path = projects_dir / project_name
    created_link = False

    if link_path.is_symlink():
        target = link_path.resolve()
        if target == docs_dir.resolve():
            created_link = False
        elif force:
            link_path.unlink()
            link_path.symlink_to(docs_dir, target_is_directory=True)
            created_link = True
        else:
            raise ValueError(
                f"Symlink {link_path} already points to {target}. Use --force to overwrite."
            )
    elif link_path.exists():
        raise ValueError(f"Path {link_path} already exists. Refusing to overwrite.")
    else:
        link_path.symlink_to(docs_dir, target_is_directory=True)
        created_link = True

    gitignore_updated = ensure_gitignore_entries(project_root, [".obsidian/", ".trash/"])

    return VaultLinkResult(
        project_root=project_root,
        project_name=project_name,
        docs_path=docs_dir,
        vault_path=vault_path,
        link_path=link_path,
        created_link=created_link,
        created_docs=created_docs,
        gitignore_updated=gitignore_updated,
        scaffolded_docs=scaffolded_docs,
    )
