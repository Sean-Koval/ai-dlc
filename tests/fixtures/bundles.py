"""Workflow-bundle fixtures shared across test modules: sources, payloads and vendored copies."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any

from fixtures.git import git

SKILL = b"---\nname: day-start\ndescription: Start the work day\n---\n\n# Start\n"
TEMPLATE = b"# Product brief\n\nDescribe the outcome.\n"


def content_digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def write_bundle(
    root: Path,
    *,
    skills: dict[str, tuple[str, bytes]] | None = None,
    templates: dict[str, tuple[str, bytes]] | None = None,
) -> dict[str, Any]:
    skill_entries = skills if skills is not None else {"day-start": ("skills/day/SKILL.md", SKILL)}
    template_entries = (
        templates
        if templates is not None
        else {"product-brief": ("templates/product-brief.md", TEMPLATE)}
    )
    manifest: dict[str, Any] = {
        "schema": 1,
        "id": "example-bundle",
        "skills": {name: path for name, (path, _) in skill_entries.items()},
        "templates": {name: path for name, (path, _) in template_entries.items()},
        "files": {
            path: content_digest(content)
            for path, content in [*skill_entries.values(), *template_entries.values()]
        },
    }
    for path, content in [*skill_entries.values(), *template_entries.values()]:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    write_manifest(root, manifest)
    return manifest


def write_manifest(root: Path, manifest: dict[str, Any]) -> None:
    (root / "bundle.json").write_text(json.dumps(manifest), encoding="utf-8")


def bundle_repository(tmp_path: Path) -> tuple[Path, str, dict[str, str]]:
    repository = tmp_path / "bundle-source"
    repository.mkdir()
    git(repository, "init", "-b", "main")
    git(repository, "config", "user.name", "AI-DLC Test")
    git(repository, "config", "user.email", "ai-dlc@example.test")
    write_bundle(repository)
    git(repository, "add", ".")
    git(repository, "commit", "-m", "add bundle")
    source = "https://example.test/workflow.git"
    environment = dict(os.environ)
    environment.update(
        {
            "GIT_ALLOW_PROTOCOL": "file:https:ssh",
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": f"url.{repository.as_uri()}.insteadOf",
            "GIT_CONFIG_VALUE_0": source,
        }
    )
    return repository, source, environment


def write_vendored_bundle(
    root: Path,
    bundle_id: str,
    *,
    skills: dict[str, tuple[str, str]] | None = None,
    templates: dict[str, tuple[str, str]] | None = None,
) -> None:
    skills = skills or {}
    templates = templates or {}
    destination = root / ".ai-dlc/bundles" / bundle_id
    files = {
        path: hashlib.sha256(body.encode()).hexdigest()
        for path, body in [*skills.values(), *templates.values()]
    }
    manifest = {
        "schema": 1,
        "id": bundle_id,
        "skills": {name: path for name, (path, _) in skills.items()},
        "templates": {name: path for name, (path, _) in templates.items()},
        "files": files,
    }
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    lock = {
        "schema": 1,
        "id": bundle_id,
        "source": f"https://example.test/{bundle_id}.git",
        "ref": "v1",
        "resolved_commit": "a" * 40,
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "files": files,
    }
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "bundle.json").write_bytes(manifest_bytes)
    (destination / "bundle.lock.json").write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")
    for path, body in [*skills.values(), *templates.values()]:
        output = destination / path
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(body)


def skill_document(name: str, body: str = "Use the reviewed workflow.") -> str:
    return f"---\nname: {name}\ndescription: Portable reviewed workflow\n---\n{body}\n"
