"""Workflow bundle manifest and payload validation."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

SKILL = b"---\nname: day-start\ndescription: Start the work day\n---\n\n# Start\n"
TEMPLATE = b"# Product brief\n\nDescribe the outcome.\n"


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _write_bundle(
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
            path: _digest(content)
            for path, content in [*skill_entries.values(), *template_entries.values()]
        },
    }
    for path, content in [*skill_entries.values(), *template_entries.values()]:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    _write_manifest(root, manifest)
    return manifest


def _write_manifest(root: Path, manifest: dict[str, Any]) -> None:
    (root / "bundle.json").write_text(json.dumps(manifest), encoding="utf-8")


def _snapshot(root: Path) -> dict[str, bytes | str]:
    snapshot: dict[str, bytes | str] = {}
    for directory, directories, filenames in os.walk(root, followlinks=False):
        parent = Path(directory)
        for name in [*directories, *filenames]:
            path = parent / name
            relative = path.relative_to(root).as_posix()
            snapshot[relative] = (
                "symlink" if path.is_symlink() else path.read_bytes() if path.is_file() else "dir"
            )
    return snapshot


def _bundle_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    (project / "ai-dlc.toml").write_text("schema = 4\n")
    return project


def test_loads_duplicate_key_free_utf8_bundle_manifest(tmp_path: Path):
    """Would fail if the raw loader did not return the complete JSON object."""
    from ai_dlc.harness.workflow_bundles import load_bundle_manifest

    manifest = _write_bundle(tmp_path)

    assert load_bundle_manifest(tmp_path) == manifest


@pytest.mark.parametrize(
    "document",
    [
        b'{"schema":1,"schema":1,"id":"example","skills":{},"templates":{},"files":{}}',
        b'{"schema":1,"id":"example","skills":{"same":"a/SKILL.md","same":"b/SKILL.md"},"templates":{},"files":{}}',
        b'{"schema":1,"id":"example","skills":{},"templates":{},"files":{"a.md":"0","a.md":"1"}}',
    ],
)
def test_raw_loader_rejects_duplicate_keys_at_every_manifest_level(tmp_path: Path, document: bytes):
    """Would fail if JSON decoding silently accepted an overwritten key."""
    from ai_dlc.harness.workflow_bundles import load_bundle_manifest

    (tmp_path / "bundle.json").write_bytes(document)

    with pytest.raises(ValueError, match="duplicate JSON key"):
        load_bundle_manifest(tmp_path)


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (b"\xff", "UTF-8 JSON"),
        (b"{", "UTF-8 JSON"),
        (b"[]", "JSON object"),
    ],
)
def test_raw_loader_rejects_malformed_manifest(tmp_path: Path, content: bytes, message: str):
    """Would fail if malformed raw metadata crossed the dictionary boundary."""
    from ai_dlc.harness.workflow_bundles import load_bundle_manifest

    (tmp_path / "bundle.json").write_bytes(content)

    with pytest.raises(ValueError, match=message):
        load_bundle_manifest(tmp_path)


def test_raw_loader_rejects_manifest_larger_than_one_mib(tmp_path: Path):
    """Would fail if an oversized manifest were read and decoded."""
    from ai_dlc.harness.workflow_bundles import load_bundle_manifest

    (tmp_path / "bundle.json").write_bytes(b" " * (1024 * 1024 + 1))

    with pytest.raises(ValueError, match="at most 1 MiB"):
        load_bundle_manifest(tmp_path)


@pytest.mark.parametrize("replacement", ["symlink", "directory"])
def test_raw_loader_requires_a_regular_bundle_json(tmp_path: Path, replacement: str):
    """Would fail if the manifest boundary followed a link or accepted a non-file."""
    from ai_dlc.harness.workflow_bundles import load_bundle_manifest

    if replacement == "symlink":
        target = tmp_path / "outside.json"
        target.write_text("{}")
        (tmp_path / "bundle.json").symlink_to(target)
    else:
        (tmp_path / "bundle.json").mkdir()

    with pytest.raises(ValueError, match="regular file|symlink"):
        load_bundle_manifest(tmp_path)


def test_validates_and_normalizes_a_complete_schema_one_bundle(tmp_path: Path):
    """Would fail if valid portable skills/templates were refused or returned unsorted."""
    from ai_dlc.harness.workflow_bundles import validate_bundle

    manifest = _write_bundle(
        tmp_path,
        skills={"z-skill": ("z/SKILL.md", SKILL.replace(b"day-start", b"z-skill"))},
        templates={
            "z-template": ("templates/z.md", b"# Z\n"),
            "a-template": ("templates/a.md", b"# A\n"),
        },
    )

    assert validate_bundle(tmp_path, manifest) == {
        "schema": 1,
        "id": "example-bundle",
        "skills": {"z-skill": "z/SKILL.md"},
        "templates": {
            "a-template": "templates/a.md",
            "z-template": "templates/z.md",
        },
        "files": {
            "templates/a.md": _digest(b"# A\n"),
            "templates/z.md": _digest(b"# Z\n"),
            "z/SKILL.md": _digest(SKILL.replace(b"day-start", b"z-skill")),
        },
    }


@pytest.mark.parametrize(
    ("manifest", "message"),
    [
        ([], "JSON object"),
        (
            {"schema": 1, "id": "example", "skills": {}, "templates": {}},
            "exactly schema, id, skills, templates, and files",
        ),
        (
            {
                "schema": 1,
                "id": "example",
                "skills": {},
                "templates": {},
                "files": {},
                "extra": None,
            },
            "exactly schema, id, skills, templates, and files",
        ),
        (
            {"schema": True, "id": "example", "skills": {}, "templates": {}, "files": {}},
            "schema must be 1",
        ),
        (
            {"schema": 2, "id": "example", "skills": {}, "templates": {}, "files": {}},
            "schema 2 bundle manifest must contain exactly",
        ),
        (
            {"schema": 1, "id": 1, "skills": {}, "templates": {}, "files": {}},
            "id must be a lowercase ASCII slug",
        ),
        (
            {"schema": 1, "id": "Bad_ID", "skills": {}, "templates": {}, "files": {}},
            "id must be a lowercase ASCII slug",
        ),
        (
            {"schema": 1, "id": "example", "skills": [], "templates": {}, "files": {}},
            "skills must be an object",
        ),
        (
            {"schema": 1, "id": "example", "skills": {}, "templates": [], "files": {}},
            "templates must be an object",
        ),
        (
            {"schema": 1, "id": "example", "skills": {}, "templates": {}, "files": []},
            "files must be an object",
        ),
    ],
)
def test_rejects_wrong_manifest_fields_and_types(tmp_path: Path, manifest: Any, message: str):
    """Would fail if schema-1 accepted fields or JSON types outside its exact shape."""
    from ai_dlc.harness.workflow_bundles import validate_bundle

    with pytest.raises((TypeError, ValueError), match=message):
        validate_bundle(tmp_path, manifest)


@pytest.mark.parametrize(
    ("field", "name"),
    [
        ("skills", "Bad_Name"),
        ("skills", "café"),
        ("templates", "-leading"),
    ],
)
def test_rejects_non_slug_export_names(tmp_path: Path, field: str, name: str):
    """Would fail if a non-portable export name entered the shared namespace."""
    from ai_dlc.harness.workflow_bundles import validate_bundle

    manifest = _write_bundle(tmp_path)
    original = next(iter(manifest[field]))
    manifest[field][name] = manifest[field].pop(original)
    _write_manifest(tmp_path, manifest)

    with pytest.raises(ValueError, match=f"{field} name must be a lowercase ASCII slug"):
        validate_bundle(tmp_path, manifest)


@pytest.mark.parametrize(
    "path",
    [
        "../SKILL.md",
        "/skills/SKILL.md",
        "C:/skills/SKILL.md",
        "skills\\SKILL.md",
        "skills//SKILL.md",
        "skills/./SKILL.md",
        "skills/../SKILL.md",
        "skills/café/SKILL.md",
        "skills/a b/SKILL.md",
    ],
)
def test_rejects_unsafe_or_nonnormalized_paths(tmp_path: Path, path: str):
    """Would fail if a payload path could escape or vary across filesystems."""
    from ai_dlc.harness.workflow_bundles import validate_bundle

    manifest = _write_bundle(tmp_path)
    old_path = manifest["skills"]["day-start"]
    manifest["skills"]["day-start"] = path
    manifest["files"][path] = manifest["files"].pop(old_path)
    _write_manifest(tmp_path, manifest)

    with pytest.raises(ValueError, match="relative normalized safe ASCII path"):
        validate_bundle(tmp_path, manifest)


def test_rejects_paths_deeper_than_sixteen_segments(tmp_path: Path):
    """Would fail if bundle traversal admitted an over-deep payload."""
    from ai_dlc.harness.workflow_bundles import validate_bundle

    path = "/".join([*(["a"] * 16), "SKILL.md"])
    manifest = _write_bundle(tmp_path)
    old_path = manifest["skills"]["day-start"]
    manifest["skills"]["day-start"] = path
    manifest["files"][path] = manifest["files"].pop(old_path)
    _write_manifest(tmp_path, manifest)

    with pytest.raises(ValueError, match="at most 16 path segments"):
        validate_bundle(tmp_path, manifest)


@pytest.mark.parametrize(
    ("field", "path", "message"),
    [
        ("skills", "skills/day.md", "skills paths must end in SKILL.md"),
        ("templates", "templates/day.txt", "templates paths must end in .md"),
    ],
)
def test_rejects_non_markdown_export_paths(tmp_path: Path, field: str, path: str, message: str):
    """Would fail if schema 1 admitted scripts or non-Markdown payloads."""
    from ai_dlc.harness.workflow_bundles import validate_bundle

    manifest = _write_bundle(tmp_path)
    old_path = next(iter(manifest[field].values()))
    name = next(iter(manifest[field]))
    manifest[field][name] = path
    manifest["files"][path] = manifest["files"].pop(old_path)
    _write_manifest(tmp_path, manifest)

    with pytest.raises(ValueError, match=message):
        validate_bundle(tmp_path, manifest)


def test_requires_at_least_one_export(tmp_path: Path):
    """Would fail if an empty bundle could pass schema validation."""
    from ai_dlc.harness.workflow_bundles import validate_bundle

    manifest = _write_bundle(tmp_path, skills={}, templates={})

    with pytest.raises(ValueError, match="at least one skill or template"):
        validate_bundle(tmp_path, manifest)


@pytest.mark.parametrize("collision", ["name", "path"])
def test_skill_and_template_exports_form_one_namespace(tmp_path: Path, collision: str):
    """Would fail if two exports could claim the same name or payload path."""
    from ai_dlc.harness.workflow_bundles import validate_bundle

    manifest = _write_bundle(tmp_path)
    if collision == "name":
        manifest["templates"]["day-start"] = manifest["templates"].pop("product-brief")
        message = "export names must be unique"
    else:
        path = manifest["skills"]["day-start"]
        manifest["templates"]["product-brief"] = path
        manifest["files"].pop("templates/product-brief.md")
        message = "payload path may have only one export"
    _write_manifest(tmp_path, manifest)

    with pytest.raises(ValueError, match=message):
        validate_bundle(tmp_path, manifest)


@pytest.mark.parametrize("difference", ["missing", "undeclared"])
def test_files_are_exactly_the_export_path_union(tmp_path: Path, difference: str):
    """Would fail if files omitted an export or admitted undefined supporting content."""
    from ai_dlc.harness.workflow_bundles import validate_bundle

    manifest = _write_bundle(tmp_path)
    if difference == "missing":
        manifest["files"].pop("skills/day/SKILL.md")
    else:
        manifest["files"]["supporting.md"] = "0" * 64
    _write_manifest(tmp_path, manifest)

    with pytest.raises(ValueError, match="files keys must equal the export paths exactly"):
        validate_bundle(tmp_path, manifest)


@pytest.mark.parametrize("digest", ["A" * 64, "0" * 63, 7])
def test_rejects_non_lowercase_sha256_file_digests(tmp_path: Path, digest: Any):
    """Would fail if a file digest were not an exact lowercase SHA-256 value."""
    from ai_dlc.harness.workflow_bundles import validate_bundle

    manifest = _write_bundle(tmp_path)
    manifest["files"]["skills/day/SKILL.md"] = digest
    _write_manifest(tmp_path, manifest)

    with pytest.raises(ValueError, match="lowercase SHA-256"):
        validate_bundle(tmp_path, manifest)


def test_rejects_more_than_1024_payload_files(tmp_path: Path):
    """Would fail if a manifest could exceed the payload-count resource bound."""
    from ai_dlc.harness.workflow_bundles import validate_bundle

    templates = {f"template-{index}": (f"templates/{index}.md", b"# T\n") for index in range(1025)}
    manifest = {
        "schema": 1,
        "id": "example",
        "skills": {},
        "templates": {name: path for name, (path, _) in templates.items()},
        "files": {path: _digest(content) for path, content in templates.values()},
    }
    _write_manifest(tmp_path, manifest)

    with pytest.raises(ValueError, match="at most 1024 payload files"):
        validate_bundle(tmp_path, manifest)


@pytest.mark.parametrize("kind", ["file", "directory"])
def test_rejects_symlinks_at_any_payload_path_component(tmp_path: Path, kind: str):
    """Would fail if validation followed an export or ancestor symlink."""
    from ai_dlc.harness.workflow_bundles import validate_bundle

    manifest = _write_bundle(tmp_path)
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    if kind == "file":
        target = outside / "SKILL.md"
        target.write_bytes(SKILL)
        (tmp_path / "skills/day/SKILL.md").unlink()
        (tmp_path / "skills/day/SKILL.md").symlink_to(target)
    else:
        (outside / "SKILL.md").write_bytes(SKILL)
        (tmp_path / "skills/day/SKILL.md").unlink()
        (tmp_path / "skills/day").rmdir()
        (tmp_path / "skills/day").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        validate_bundle(tmp_path, manifest)


def test_rejects_a_nonregular_payload(tmp_path: Path):
    """Would fail if a declared export were a directory rather than a regular file."""
    from ai_dlc.harness.workflow_bundles import validate_bundle

    manifest = _write_bundle(tmp_path)
    path = tmp_path / "skills/day/SKILL.md"
    path.unlink()
    path.mkdir()

    with pytest.raises(ValueError, match="regular file"):
        validate_bundle(tmp_path, manifest)


def test_rejects_missing_and_extra_checkout_entries_without_writing(tmp_path: Path):
    """Would fail if incomplete or undeclared checkout content passed, or validation wrote."""
    from ai_dlc.harness.workflow_bundles import validate_bundle

    manifest = _write_bundle(tmp_path)
    (tmp_path / "skills/day/SKILL.md").unlink()
    extra = tmp_path / "undeclared.md"
    extra.write_text("# Extra\n")
    before = _snapshot(tmp_path)

    with pytest.raises(ValueError, match="checkout tree"):
        validate_bundle(tmp_path, manifest)

    assert _snapshot(tmp_path) == before


def test_ignores_only_the_checkout_roots_git_metadata(tmp_path: Path):
    """Would fail if normal root Git metadata were treated as payload."""
    from ai_dlc.harness.workflow_bundles import validate_bundle

    manifest = _write_bundle(tmp_path)
    (tmp_path / ".git/objects").mkdir(parents=True)
    (tmp_path / ".git/HEAD").write_text("ref: refs/heads/main\n")

    assert validate_bundle(tmp_path, manifest)["id"] == "example-bundle"


def test_rejects_a_nested_git_entry_as_undeclared_content(tmp_path: Path):
    """Would fail if nested Git metadata received the checkout-root exception."""
    from ai_dlc.harness.workflow_bundles import validate_bundle

    manifest = _write_bundle(tmp_path)
    (tmp_path / "skills/day/.git").mkdir()

    with pytest.raises(ValueError, match="checkout tree"):
        validate_bundle(tmp_path, manifest)


def test_rejects_a_payload_digest_mismatch(tmp_path: Path):
    """Would fail if tampered Markdown bytes passed authenticated validation."""
    from ai_dlc.harness.workflow_bundles import validate_bundle

    manifest = _write_bundle(tmp_path)
    (tmp_path / "templates/product-brief.md").write_text("# Tampered\n")

    with pytest.raises(ValueError, match="digest mismatch"):
        validate_bundle(tmp_path, manifest)


def test_rejects_non_utf8_markdown(tmp_path: Path):
    """Would fail if payload bytes were authenticated but not portable UTF-8 Markdown."""
    from ai_dlc.harness.workflow_bundles import validate_bundle

    manifest = _write_bundle(
        tmp_path,
        skills={},
        templates={"invalid": ("templates/invalid.md", b"\xff")},
    )

    with pytest.raises(ValueError, match="UTF-8 Markdown"):
        validate_bundle(tmp_path, manifest)


def test_rejects_a_payload_larger_than_two_mib(tmp_path: Path):
    """Would fail if a single payload could exceed its resource bound."""
    from ai_dlc.harness.workflow_bundles import validate_bundle

    content = b"# T\n" + b"a" * (2 * 1024 * 1024)
    manifest = _write_bundle(
        tmp_path,
        skills={},
        templates={"large": ("templates/large.md", content)},
    )

    with pytest.raises(ValueError, match="at most 2 MiB"):
        validate_bundle(tmp_path, manifest)


def test_rejects_more_than_ten_mib_total_payload(tmp_path: Path):
    """Would fail if individually valid files could exceed the aggregate resource bound."""
    from ai_dlc.harness.workflow_bundles import validate_bundle

    content = b"# T\n" + b"a" * (2 * 1024 * 1024 - 4)
    templates = {f"template-{index}": (f"templates/{index}.md", content) for index in range(6)}
    manifest = _write_bundle(tmp_path, skills={}, templates=templates)

    with pytest.raises(ValueError, match="at most 10 MiB"):
        validate_bundle(tmp_path, manifest)


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (b"# No frontmatter\n", "four-line frontmatter"),
        (
            b"---\nname: other\ndescription: Start the work day\n---\n\n# Start\n",
            "name must equal its export",
        ),
        (
            b"---\nname: day-start\ndescription: Start\nextra: field\n---\n# Start\n",
            "four-line frontmatter",
        ),
        (b"---\nname: day-start\ndescription: \n---\n\n# Start\n", "description"),
        (b"---\nname: day-start\ndescription: leading \n---\n\n# Start\n", "description"),
        (b"---\nname: day-start\ndescription: bad\tvalue\n---\n\n# Start\n", "description"),
        (
            b"---\nname: day-start\ndescription: " + b"a" * 1025 + b"\n---\n\n# Start\n",
            "description",
        ),
        (b"---\nname: day-start\ndescription: Start\n---\n   \n", "body"),
    ],
)
def test_rejects_nonportable_skill_frontmatter_or_body(
    tmp_path: Path, content: bytes, message: str
):
    """Would fail if a skill could render differently across supported harnesses."""
    from ai_dlc.harness.workflow_bundles import validate_bundle

    manifest = _write_bundle(
        tmp_path,
        skills={"day-start": ("skills/day/SKILL.md", content)},
        templates={},
    )

    with pytest.raises(ValueError, match=message):
        validate_bundle(tmp_path, manifest)


def test_accepts_the_maximum_skill_description_length(tmp_path: Path):
    """Would fail on an off-by-one error at the 1,024-character boundary."""
    from ai_dlc.harness.workflow_bundles import validate_bundle

    content = b"---\nname: day-start\ndescription: " + b"a" * 1024 + b"\n---\n\n# Start\n"
    manifest = _write_bundle(
        tmp_path,
        skills={"day-start": ("skills/day/SKILL.md", content)},
        templates={},
    )

    assert validate_bundle(tmp_path, manifest)["skills"] == {"day-start": "skills/day/SKILL.md"}


def test_rejects_an_empty_template(tmp_path: Path):
    """Would fail if a template contained no usable Markdown body."""
    from ai_dlc.harness.workflow_bundles import validate_bundle

    manifest = _write_bundle(
        tmp_path,
        skills={},
        templates={"empty": ("templates/empty.md", b" \n\t")},
    )

    with pytest.raises(ValueError, match="template body must be non-empty"):
        validate_bundle(tmp_path, manifest)


def test_validation_rejects_leaf_symlink_swap_between_check_and_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Would fail if a checked leaf were reopened by mutable pathname for reading."""
    from ai_dlc.harness import workflow_bundles

    manifest = _write_bundle(
        tmp_path,
        skills={},
        templates={"brief": ("templates/brief.md", b"# Brief\n")},
    )
    leaf = tmp_path / "templates/brief.md"
    replacement = tmp_path.parent / f"{tmp_path.name}-replacement.md"
    replacement.write_bytes(b"# Brief\n")
    original = tmp_path.parent / f"{tmp_path.name}-original.md"
    real_read = os.read
    swapped = False

    def swap_then_read(descriptor: int, count: int) -> bytes:
        nonlocal swapped
        if not swapped:
            leaf.replace(original)
            leaf.symlink_to(replacement)
            swapped = True
        return real_read(descriptor, count)

    monkeypatch.setattr(workflow_bundles.os, "read", swap_then_read)

    with pytest.raises(ValueError, match="changed|symlink"):
        workflow_bundles.validate_bundle(tmp_path, manifest)


def test_validation_rejects_growth_past_per_file_limit_between_stat_and_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Would fail if a file could grow past its limit after its metadata check."""
    from ai_dlc.harness import workflow_bundles

    manifest = _write_bundle(
        tmp_path,
        skills={},
        templates={"brief": ("templates/brief.md", b"# Brief\n")},
    )
    leaf = tmp_path / "templates/brief.md"
    real_read = os.read
    grown = False

    def grow_then_read(descriptor: int, count: int) -> bytes:
        nonlocal grown
        if not grown:
            with leaf.open("ab") as stream:
                stream.write(b"x" * (2 * 1024 * 1024))
            grown = True
        return real_read(descriptor, count)

    monkeypatch.setattr(workflow_bundles.os, "read", grow_then_read)

    with pytest.raises(ValueError, match="at most 2 MiB"):
        workflow_bundles.validate_bundle(tmp_path, manifest)


def test_validation_rejects_tree_mutation_after_scan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Would fail if validation trusted a checkout snapshot after the tree changed."""
    from ai_dlc.harness import workflow_bundles

    manifest = _write_bundle(tmp_path)
    real_checkout_tree = workflow_bundles._checkout_tree
    mutated = False

    def mutate_after_scan(root: Path, *, ignore_root_git: bool = True):
        nonlocal mutated
        snapshot = real_checkout_tree(root, ignore_root_git=ignore_root_git)
        if not mutated:
            (root / "added-after-scan.md").write_text("# Added\n")
            mutated = True
        return snapshot

    monkeypatch.setattr(workflow_bundles, "_checkout_tree", mutate_after_scan)

    with pytest.raises(ValueError, match="changed during validation"):
        workflow_bundles.validate_bundle(tmp_path, manifest)


@pytest.mark.parametrize("control", ["\u202e", "\u200b", "\u2066", "\ufeff"])
def test_rejects_every_unicode_category_c_description_control(tmp_path: Path, control: str):
    """Would fail if a format control could make skill metadata display deceptively."""
    from ai_dlc.harness.workflow_bundles import validate_bundle

    content = (f"---\nname: day-start\ndescription: Start{control}here\n---\n\n# Start\n").encode()
    manifest = _write_bundle(
        tmp_path,
        skills={"day-start": ("skills/day/SKILL.md", content)},
        templates={},
    )

    with pytest.raises(ValueError, match="description"):
        validate_bundle(tmp_path, manifest)


@pytest.mark.parametrize("operation", ["manifest-read", "payload-read", "scandir", "stat"])
def test_filesystem_errors_are_normalized_and_do_not_disclose_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str
):
    """Would fail if an OS error or absolute source path escaped the validation boundary."""
    from ai_dlc.harness import workflow_bundles

    manifest = _write_bundle(tmp_path)
    original_path_read = Path.read_bytes
    secret = f"filesystem failed at {tmp_path}/credential-sentinel"

    def fail_path_read(path: Path) -> bytes:
        if operation == "manifest-read" and path.name == "bundle.json":
            raise OSError(secret)
        if operation == "payload-read" and path.name != "bundle.json":
            raise OSError(secret)
        return original_path_read(path)

    def fail_read(_descriptor: int, _count: int) -> bytes:
        raise OSError(secret)

    def fail_scandir(_directory: object):
        raise OSError(secret)

    def fail_lstat(_path: Path):
        raise OSError(secret)

    def fail_fstat(_descriptor: int):
        raise OSError(secret)

    if operation in {"manifest-read", "payload-read"}:
        monkeypatch.setattr(Path, "read_bytes", fail_path_read)
        monkeypatch.setattr(workflow_bundles.os, "read", fail_read)
    elif operation == "scandir":
        monkeypatch.setattr(workflow_bundles.os, "scandir", fail_scandir)
    else:
        monkeypatch.setattr(Path, "lstat", fail_lstat)
        monkeypatch.setattr(workflow_bundles.os, "fstat", fail_fstat)

    operation_under_test = (
        workflow_bundles.load_bundle_manifest
        if operation == "manifest-read"
        else lambda root: workflow_bundles.validate_bundle(root, manifest)
    )
    with pytest.raises(ValueError) as captured:
        operation_under_test(tmp_path)

    assert str(captured.value) == "bundle filesystem operation failed"
    assert str(tmp_path) not in str(captured.value)
    assert "credential-sentinel" not in str(captured.value)


def test_duplicate_key_error_does_not_echo_the_arbitrary_key(tmp_path: Path):
    """Would fail if attacker-controlled JSON keys were included in refusal messages."""
    from ai_dlc.harness.workflow_bundles import load_bundle_manifest

    secret_key = f"{tmp_path}/credential-sentinel"
    (tmp_path / "bundle.json").write_text(
        json.dumps({"before": 1})[:-1]
        + f", {json.dumps(secret_key)}: 1, {json.dumps(secret_key)}: 2}}"
    )

    with pytest.raises(ValueError) as captured:
        load_bundle_manifest(tmp_path)

    assert str(captured.value) == "bundle.json contains duplicate JSON key"
    assert str(tmp_path) not in str(captured.value)
    assert "credential-sentinel" not in str(captured.value)


def test_manifest_loader_rejects_same_inode_content_mutation_during_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Would fail if equal-length in-place changes escaped post-read identity validation."""
    from ai_dlc.harness import workflow_bundles

    manifest_path = tmp_path / "bundle.json"
    manifest_path.write_bytes(b'{"before":1}')
    initial = manifest_path.stat()
    real_read = os.read
    mutated = False

    def mutate_then_read(descriptor: int, count: int) -> bytes:
        nonlocal mutated
        if not mutated:
            manifest_path.write_bytes(b'{"before":2}')
            os.utime(
                manifest_path,
                ns=(initial.st_atime_ns, initial.st_mtime_ns + 1_000_000_000),
            )
            mutated = True
        return real_read(descriptor, count)

    monkeypatch.setattr(workflow_bundles.os, "read", mutate_then_read)

    with pytest.raises(ValueError, match="changed during validation"):
        workflow_bundles.load_bundle_manifest(tmp_path)


def test_overdeep_undeclared_tree_is_rejected_without_recursion_error(tmp_path: Path):
    """Would fail if undeclared traversal were not bounded by the 16-segment contract."""
    from ai_dlc.harness.workflow_bundles import validate_bundle

    manifest = _write_bundle(tmp_path)
    overdeep = tmp_path
    for _ in range(17):
        overdeep /= "d"
    overdeep.mkdir(parents=True)

    with pytest.raises(ValueError, match="at most 16 path segments"):
        validate_bundle(tmp_path, manifest)


def _git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.stdout.strip()


def _bundle_repository(tmp_path: Path) -> tuple[Path, str, dict[str, str]]:
    repository = tmp_path / "bundle-source"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "AI-DLC Test")
    _git(repository, "config", "user.email", "ai-dlc@example.test")
    _write_bundle(repository)
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "add bundle")
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


def _project_files(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_resolve_bundle_uses_portable_git_and_cleans_up_candidate(tmp_path: Path):
    """Would fail if resolution accepted no portable ref or leaked its temporary checkout."""
    from ai_dlc.harness.workflow_bundles import resolve_bundle

    repository, source, environment = _bundle_repository(tmp_path)
    commit = _git(repository, "rev-parse", "HEAD")

    with resolve_bundle(source, "main", "example-bundle", environ=environment) as candidate:
        checkout = candidate.root
        assert candidate.source == source
        assert candidate.ref == "main"
        assert candidate.bundle_id == "example-bundle"
        assert candidate.resolved_commit == commit
        assert candidate.manifest_sha256 == _digest((repository / "bundle.json").read_bytes())
        assert candidate.file_hashes == dict(sorted(candidate.manifest["files"].items()))
        assert checkout.is_dir()

    assert not checkout.exists()


@pytest.mark.parametrize("source", ["/tmp/bundle", "file:///tmp/bundle"])
def test_resolve_bundle_refuses_machine_specific_sources_before_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: str
):
    """Would fail if local provenance reached Git or the eventual import lock."""
    from ai_dlc.environment import profile_source
    from ai_dlc.harness.workflow_bundles import resolve_bundle

    calls: list[object] = []
    monkeypatch.setattr(profile_source, "_run_git", lambda *args, **kwargs: calls.append(args))

    with pytest.raises(ValueError, match="portable Git source"):
        resolve_bundle(source, "main", "example-bundle", environ=dict(os.environ))

    assert calls == []
    assert not list(tmp_path.glob(".ai-dlc-bundle-*"))


def test_resolve_bundle_requires_requested_and_manifest_ids_to_match(tmp_path: Path):
    """Would fail if a caller could vendor a bundle under a misleading requested identity."""
    _, source, environment = _bundle_repository(tmp_path)
    from ai_dlc.harness.workflow_bundles import resolve_bundle

    with pytest.raises(ValueError, match="manifest id does not match"):
        resolve_bundle(source, "main", "other-bundle", environ=environment)


def test_import_preview_is_exact_sorted_and_writes_nothing(tmp_path: Path):
    """Would fail if preview omitted reviewed metadata, reordered maps, or touched the project."""
    from ai_dlc.harness.workflow_bundles import import_bundle, resolve_bundle

    _, source, environment = _bundle_repository(tmp_path)
    project = _bundle_project(tmp_path)
    before = _project_files(project)

    with resolve_bundle(source, "main", "example-bundle", environ=environment) as candidate:
        result = import_bundle(project, candidate)

    assert list(result) == [
        "applied",
        "changed",
        "conflicts",
        "source",
        "ref",
        "bundle_id",
        "resolved_commit",
        "manifest_sha256",
        "skills",
        "templates",
        "files",
    ]
    assert result["applied"] is False
    assert result["conflicts"] == []
    assert result["source"] == source
    assert result["changed"] == [
        ".ai-dlc/bundles/example-bundle/bundle.json",
        ".ai-dlc/bundles/example-bundle/bundle.lock.json",
        ".ai-dlc/bundles/example-bundle/skills/day/SKILL.md",
        ".ai-dlc/bundles/example-bundle/templates/product-brief.md",
    ]
    assert _project_files(project) == before


def test_apply_requires_reviewed_commit_and_vendors_complete_deterministic_lock(tmp_path: Path):
    """Would fail if apply skipped the preview pin or omitted authenticated vendored bytes."""
    from ai_dlc.harness.workflow_bundles import import_bundle, resolve_bundle

    repository, source, environment = _bundle_repository(tmp_path)
    project = _bundle_project(tmp_path)
    profile_lock = project / ".ai-dlc/profile.lock.json"
    profile_lock.parent.mkdir()
    profile_lock.write_text('{"sentinel": true}\n')
    before_config = (project / "ai-dlc.toml").read_bytes()
    before_profile = profile_lock.read_bytes()

    with resolve_bundle(source, "main", "example-bundle", environ=environment) as candidate:
        with pytest.raises(ValueError, match="40-character expected commit"):
            import_bundle(project, candidate, apply=True)
        with pytest.raises(ValueError, match="reviewed commit"):
            import_bundle(project, candidate, apply=True, expected_commit="0" * 40)
        result = import_bundle(
            project, candidate, apply=True, expected_commit=candidate.resolved_commit
        )

    destination = project / ".ai-dlc/bundles/example-bundle"
    lock_bytes = (destination / "bundle.lock.json").read_bytes()
    lock = json.loads(lock_bytes)
    assert lock_bytes == (json.dumps(lock, indent=2, sort_keys=True) + "\n").encode()
    assert lock == {
        "schema": 1,
        "id": "example-bundle",
        "source": source,
        "ref": "main",
        "resolved_commit": _git(repository, "rev-parse", "HEAD"),
        "manifest_sha256": _digest((repository / "bundle.json").read_bytes()),
        "files": {
            "skills/day/SKILL.md": _digest(SKILL),
            "templates/product-brief.md": _digest(TEMPLATE),
        },
    }
    assert (destination / "bundle.json").read_bytes() == (repository / "bundle.json").read_bytes()
    assert (destination / "skills/day/SKILL.md").read_bytes() == SKILL
    assert (destination / "templates/product-brief.md").read_bytes() == TEMPLATE
    assert result["applied"] is True
    assert (project / "ai-dlc.toml").read_bytes() == before_config
    assert profile_lock.read_bytes() == before_profile


def test_apply_revalidates_candidate_bytes_immediately_before_writing(tmp_path: Path):
    """Would fail if a resolved candidate could be altered after preview and still publish."""
    from ai_dlc.harness.workflow_bundles import import_bundle, resolve_bundle

    _, source, environment = _bundle_repository(tmp_path)
    project = _bundle_project(tmp_path)
    with resolve_bundle(source, "main", "example-bundle", environ=environment) as candidate:
        (candidate.root / "templates/product-brief.md").write_text("# Tampered\n")
        with pytest.raises(ValueError, match="digest mismatch"):
            import_bundle(project, candidate, apply=True, expected_commit=candidate.resolved_commit)

    assert not (project / ".ai-dlc/bundles").exists()


def test_same_owner_update_and_idempotent_apply_are_supported(tmp_path: Path):
    """Would fail if intact owned content could not update or a repeat apply reported drift."""
    from ai_dlc.harness.workflow_bundles import import_bundle, resolve_bundle

    repository, source, environment = _bundle_repository(tmp_path)
    project = _bundle_project(tmp_path)
    with resolve_bundle(source, "main", "example-bundle", environ=environment) as first:
        import_bundle(project, first, apply=True, expected_commit=first.resolved_commit)
    (repository / "templates/product-brief.md").write_text("# Updated brief\n")
    manifest = json.loads((repository / "bundle.json").read_text())
    manifest["files"]["templates/product-brief.md"] = _digest(b"# Updated brief\n")
    _write_manifest(repository, manifest)
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "update bundle")

    with resolve_bundle(source, "main", "example-bundle", environ=environment) as second:
        preview = import_bundle(project, second)
        applied = import_bundle(project, second, apply=True, expected_commit=second.resolved_commit)
        repeated = import_bundle(
            project, second, apply=True, expected_commit=second.resolved_commit
        )

    expected_changes = [
        ".ai-dlc/bundles/example-bundle/bundle.json",
        ".ai-dlc/bundles/example-bundle/bundle.lock.json",
        ".ai-dlc/bundles/example-bundle/templates/product-brief.md",
    ]
    assert preview["changed"] == applied["changed"] == expected_changes
    assert repeated["applied"] is True
    assert repeated["changed"] == []


def test_apply_refuses_a_ref_that_moved_after_preview(tmp_path: Path):
    """Would fail if apply accepted newly resolved bytes under an earlier review commit."""
    from ai_dlc.harness.workflow_bundles import import_bundle, resolve_bundle

    repository, source, environment = _bundle_repository(tmp_path)
    with resolve_bundle(source, "main", "example-bundle", environ=environment) as preview:
        reviewed_commit = preview.resolved_commit
    (repository / "templates/product-brief.md").write_text("# Moved ref\n")
    manifest = json.loads((repository / "bundle.json").read_text())
    manifest["files"]["templates/product-brief.md"] = _digest(b"# Moved ref\n")
    _write_manifest(repository, manifest)
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "move reviewed ref")
    project = _bundle_project(tmp_path)
    before = _snapshot(project)

    with (
        resolve_bundle(source, "main", "example-bundle", environ=environment) as candidate,
        pytest.raises(ValueError, match="reviewed commit"),
    ):
        import_bundle(project, candidate, apply=True, expected_commit=reviewed_commit)

    assert _snapshot(project) == before


def test_apply_rechecks_existing_owner_after_staging_before_replace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Would fail if a local edit arriving during staging could be overwritten."""
    from ai_dlc.harness import workflow_bundles

    repository, source, environment = _bundle_repository(tmp_path)
    project = _bundle_project(tmp_path)
    with workflow_bundles.resolve_bundle(
        source, "main", "example-bundle", environ=environment
    ) as initial:
        workflow_bundles.import_bundle(
            project, initial, apply=True, expected_commit=initial.resolved_commit
        )
    (repository / "templates/product-brief.md").write_text("# Updated brief\n")
    manifest = json.loads((repository / "bundle.json").read_text())
    manifest["files"]["templates/product-brief.md"] = _digest(b"# Updated brief\n")
    _write_manifest(repository, manifest)
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "update bundle")
    edited = project / ".ai-dlc/bundles/example-bundle/templates/product-brief.md"
    real_stage = workflow_bundles._stage_bundle_at

    def stage_then_edit(*args, **kwargs):
        staged = real_stage(*args, **kwargs)
        edited.write_text("# Local edit during staging\n")
        return staged

    monkeypatch.setattr(workflow_bundles, "_stage_bundle_at", stage_then_edit)
    with workflow_bundles.resolve_bundle(
        source, "main", "example-bundle", environ=environment
    ) as candidate:
        result = workflow_bundles.import_bundle(
            project, candidate, apply=True, expected_commit=candidate.resolved_commit
        )

    assert result["applied"] is False
    assert result["changed"] == []
    expected_conflict = (
        ".ai-dlc/bundles/example-bundle/templates/product-brief.md: "
        "existing bundle file has local edits"
    )
    assert result["conflicts"] == [expected_conflict]
    assert edited.read_text() == "# Local edit during staging\n"


@pytest.mark.parametrize("damage", ["authored", "extra", "local-edit", "invalid-lock"])
def test_existing_destination_conflicts_are_stable_and_preserve_bytes(tmp_path: Path, damage: str):
    """Would fail if import adopted, repaired, or partially replaced untrusted existing state."""
    from ai_dlc.harness.workflow_bundles import import_bundle, resolve_bundle

    _, source, environment = _bundle_repository(tmp_path)
    project = _bundle_project(tmp_path)
    destination = project / ".ai-dlc/bundles/example-bundle"
    if damage == "authored":
        destination.mkdir(parents=True)
        (destination / "notes.md").write_text("authored\n")
    else:
        with resolve_bundle(source, "main", "example-bundle", environ=environment) as initial:
            import_bundle(project, initial, apply=True, expected_commit=initial.resolved_commit)
        if damage == "extra":
            (destination / "extra.md").write_text("extra\n")
        elif damage == "local-edit":
            (destination / "templates/product-brief.md").write_text("local\n")
        else:
            (destination / "bundle.lock.json").write_text("{}\n")
    before = _project_files(project)

    with resolve_bundle(source, "main", "example-bundle", environ=environment) as candidate:
        result = import_bundle(
            project, candidate, apply=True, expected_commit=candidate.resolved_commit
        )

    assert result["applied"] is False
    assert result["changed"] == []
    assert result["conflicts"]
    assert result["conflicts"] == sorted(result["conflicts"])
    assert all(
        item.startswith(".ai-dlc/bundles/example-bundle") and ": " in item
        for item in result["conflicts"]
    )
    assert _project_files(project) == before


def test_publication_failure_rolls_back_previous_bundle_byte_for_byte(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Would fail if a failed staged replacement lost an intact prior bundle."""
    from ai_dlc.harness import workflow_bundles

    repository, source, environment = _bundle_repository(tmp_path)
    project = _bundle_project(tmp_path)
    with workflow_bundles.resolve_bundle(
        source, "main", "example-bundle", environ=environment
    ) as initial:
        workflow_bundles.import_bundle(
            project, initial, apply=True, expected_commit=initial.resolved_commit
        )
    before = _project_files(project)
    (repository / "templates/product-brief.md").write_text("# Updated brief\n")
    manifest = json.loads((repository / "bundle.json").read_text())
    manifest["files"]["templates/product-brief.md"] = _digest(b"# Updated brief\n")
    _write_manifest(repository, manifest)
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "update bundle")
    real_replace = workflow_bundles._rename_directory_noreplace
    calls = 0

    def fail_new_tree(parent: int, source_path: str, destination_path: str) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("credential-sentinel")
        real_replace(parent, source_path, destination_path)

    monkeypatch.setattr(workflow_bundles, "_rename_directory_noreplace", fail_new_tree)
    with (
        workflow_bundles.resolve_bundle(
            source, "main", "example-bundle", environ=environment
        ) as candidate,
        pytest.raises(ValueError) as captured,
    ):
        workflow_bundles.import_bundle(
            project, candidate, apply=True, expected_commit=candidate.resolved_commit
        )

    assert str(captured.value) == "bundle filesystem operation failed"
    assert "credential-sentinel" not in str(captured.value)
    assert all(_project_files(project)[name] == value for name, value in before.items())
    _assert_import_residue_reported(project, captured.value)


def test_first_publication_failure_retains_and_reports_stage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """A failed first publication must retain and report its unused stage."""
    from ai_dlc.harness import workflow_bundles

    _, source, environment = _bundle_repository(tmp_path)
    project = _bundle_project(tmp_path)
    before = _snapshot(project)

    def fail_publish(*args: object, **kwargs: object) -> None:
        raise OSError("credential-sentinel")

    monkeypatch.setattr(workflow_bundles, "_rename_directory_noreplace", fail_publish)
    with (
        workflow_bundles.resolve_bundle(
            source, "main", "example-bundle", environ=environment
        ) as candidate,
        pytest.raises(ValueError, match="bundle filesystem operation failed") as failure,
    ):
        workflow_bundles.import_bundle(
            project, candidate, apply=True, expected_commit=candidate.resolved_commit
        )

    assert all(_snapshot(project)[name] == value for name, value in before.items())
    assert not (project / ".ai-dlc/bundles/example-bundle").exists()
    _assert_import_residue_reported(project, failure.value)


@pytest.mark.parametrize("damage", ["boolean-schema", "reformatted"])
def test_existing_lock_requires_exact_schema_type_and_deterministic_bytes(
    tmp_path: Path, damage: str
):
    """Would fail if a semantic reparse silently adopted edited lock metadata."""
    from ai_dlc.harness.workflow_bundles import import_bundle, resolve_bundle

    _, source, environment = _bundle_repository(tmp_path)
    project = _bundle_project(tmp_path)
    with resolve_bundle(source, "main", "example-bundle", environ=environment) as initial:
        import_bundle(project, initial, apply=True, expected_commit=initial.resolved_commit)
    lock_path = project / ".ai-dlc/bundles/example-bundle/bundle.lock.json"
    lock = json.loads(lock_path.read_text())
    if damage == "boolean-schema":
        lock["schema"] = True
        lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")
    else:
        lock_path.write_text(json.dumps(lock, sort_keys=True) + "\n")
    before = lock_path.read_bytes()

    with resolve_bundle(source, "main", "example-bundle", environ=environment) as candidate:
        result = import_bundle(
            project, candidate, apply=True, expected_commit=candidate.resolved_commit
        )

    assert result["applied"] is False
    assert result["changed"] == []
    assert result["conflicts"] == [
        ".ai-dlc/bundles/example-bundle/bundle.lock.json: existing bundle lock is invalid"
    ]
    assert lock_path.read_bytes() == before


def test_successful_updates_retain_reported_backups_without_blocking_later_imports(tmp_path):
    """Retained backup content is never adopted, changed, or a blocker for later updates."""
    from ai_dlc.harness.workflow_bundles import import_bundle

    project = _bundle_project(tmp_path)
    first, second, third = [_local_candidate(tmp_path, revision) for revision in ("1", "2", "3")]
    import_bundle(project, first, apply=True, expected_commit=first.resolved_commit)
    result = import_bundle(project, second, apply=True, expected_commit=second.resolved_commit)
    retained = result["retained_paths"]
    assert len(retained) == 1
    backup = project / retained[0]
    assert (backup / "templates/product-brief.md").read_bytes() == b"# 1\n"
    (backup / "authored.md").write_bytes(b"preserve retained backup\r\n")
    before = _snapshot(backup)
    later = import_bundle(project, third, apply=True, expected_commit=third.resolved_commit)
    assert later["applied"] and len(later["retained_paths"]) == 1
    assert later["retained_paths"] != retained
    assert _snapshot(backup) == before
    assert "retained_paths" not in import_bundle(project, third)
    repeated = import_bundle(project, third, apply=True, expected_commit=third.resolved_commit)
    assert repeated["applied"] and repeated["changed"] == []
    assert "retained_paths" not in repeated


def _updated_bundle(repository: Path) -> None:
    (repository / "templates/product-brief.md").write_text("# Updated brief\n")
    manifest = json.loads((repository / "bundle.json").read_text())
    manifest["files"]["templates/product-brief.md"] = _digest(b"# Updated brief\n")
    _write_manifest(repository, manifest)
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "update bundle")


def test_publication_binds_post_validation_local_edit_to_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Would fail if an edit after the last scan could be overwritten by publication."""
    from ai_dlc.harness import workflow_bundles

    repository, source, environment = _bundle_repository(tmp_path)
    project = _bundle_project(tmp_path)
    with workflow_bundles.resolve_bundle(
        source, "main", "example-bundle", environ=environment
    ) as initial:
        workflow_bundles.import_bundle(
            project, initial, apply=True, expected_commit=initial.resolved_commit
        )
    _updated_bundle(repository)
    edited = project / ".ai-dlc/bundles/example-bundle/templates/product-brief.md"
    real_changed = workflow_bundles._changed_paths_at
    calls = 0

    def edit_after_final_scan(*args, **kwargs):
        nonlocal calls
        changed = real_changed(*args, **kwargs)
        calls += 1
        if calls == 3:
            edited.write_text("# Edit after final scan\n")
        return changed

    monkeypatch.setattr(workflow_bundles, "_changed_paths_at", edit_after_final_scan)
    with workflow_bundles.resolve_bundle(
        source, "main", "example-bundle", environ=environment
    ) as candidate:
        result = workflow_bundles.import_bundle(
            project, candidate, apply=True, expected_commit=candidate.resolved_commit
        )

    assert result["applied"] is False
    assert result["changed"] == []
    assert result["conflicts"] == [
        (
            ".ai-dlc/bundles/example-bundle/templates/product-brief.md: "
            "existing bundle file has local edits"
        )
    ]
    assert edited.read_text() == "# Edit after final scan\n"


def test_publication_binds_validated_destination_identity_to_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Would fail if a swapped destination could be silently deleted and overwritten."""
    from ai_dlc.harness import workflow_bundles

    repository, source, environment = _bundle_repository(tmp_path)
    project = _bundle_project(tmp_path)
    with workflow_bundles.resolve_bundle(
        source, "main", "example-bundle", environ=environment
    ) as initial:
        workflow_bundles.import_bundle(
            project, initial, apply=True, expected_commit=initial.resolved_commit
        )
    _updated_bundle(repository)
    destination = project / ".ai-dlc/bundles/example-bundle"
    displaced = project / ".ai-dlc/bundles/displaced"
    real_changed = workflow_bundles._changed_paths_at
    calls = 0

    def swap_after_final_scan(*args, **kwargs):
        nonlocal calls
        changed = real_changed(*args, **kwargs)
        calls += 1
        if calls == 3:
            destination.rename(displaced)
            destination.mkdir()
            (destination / "authored.md").write_text("preserve me\n")
        return changed

    monkeypatch.setattr(workflow_bundles, "_changed_paths_at", swap_after_final_scan)
    with workflow_bundles.resolve_bundle(
        source, "main", "example-bundle", environ=environment
    ) as candidate:
        result = workflow_bundles.import_bundle(
            project, candidate, apply=True, expected_commit=candidate.resolved_commit
        )

    assert result["applied"] is False
    assert result["conflicts"]
    assert (destination / "authored.md").read_text() == "preserve me\n"
    assert displaced.is_dir()


def test_publication_refuses_bundles_parent_symlink_swap_without_external_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Would fail if final path operations followed a replaced bundles parent."""
    from ai_dlc.harness import workflow_bundles

    repository, source, environment = _bundle_repository(tmp_path)
    project = _bundle_project(tmp_path)
    with workflow_bundles.resolve_bundle(
        source, "main", "example-bundle", environ=environment
    ) as initial:
        workflow_bundles.import_bundle(
            project, initial, apply=True, expected_commit=initial.resolved_commit
        )
    _updated_bundle(repository)
    bundles = project / ".ai-dlc/bundles"
    outside = tmp_path / "outside-bundles"
    old_payload = (bundles / "example-bundle/templates/product-brief.md").read_bytes()
    real_changed = workflow_bundles._changed_paths_at
    calls = 0

    def swap_parent_after_final_scan(*args, **kwargs):
        nonlocal calls
        changed = real_changed(*args, **kwargs)
        calls += 1
        if calls == 3:
            bundles.rename(outside)
            bundles.symlink_to(outside, target_is_directory=True)
        return changed

    monkeypatch.setattr(workflow_bundles, "_changed_paths_at", swap_parent_after_final_scan)
    with (
        workflow_bundles.resolve_bundle(
            source, "main", "example-bundle", environ=environment
        ) as candidate,
        pytest.raises(ValueError, match="bundle filesystem operation failed") as failure,
    ):
        workflow_bundles.import_bundle(
            project, candidate, apply=True, expected_commit=candidate.resolved_commit
        )

    assert (outside / "example-bundle/templates/product-brief.md").read_bytes() == old_payload
    retained = list(outside.glob(".example-bundle.stage-*"))
    assert retained
    assert all(path.name in "\n".join(failure.value.__notes__) for path in retained)


@pytest.mark.parametrize("swap_point", ["before-acquire", "after-acquire"])
def test_apply_binds_requested_project_root_identity_through_return(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, swap_point: str
):
    """Would fail if publication continued in a project displaced from its requested pathname."""
    from ai_dlc.harness import workflow_bundles

    _, source, environment = _bundle_repository(tmp_path)
    project = _bundle_project(tmp_path)
    displaced = tmp_path / "displaced-project"
    replacement = tmp_path / "project-replacement"
    replacement.mkdir()
    (replacement / "ai-dlc.toml").write_text("schema = 4\n")
    before_replacement = _snapshot(replacement)

    def swap_root() -> None:
        project.rename(displaced)
        replacement.rename(project)

    if swap_point == "before-acquire":
        real_open = workflow_bundles._open_project_root

        def open_after_swap(parent: int, name: str, expected: os.stat_result) -> int:
            swap_root()
            return real_open(parent, name, expected)

        monkeypatch.setattr(workflow_bundles, "_open_project_root", open_after_swap)
    else:
        real_stage = workflow_bundles._stage_bundle_at

        def stage_then_swap(*args, **kwargs):
            staged = real_stage(*args, **kwargs)
            swap_root()
            return staged

        monkeypatch.setattr(workflow_bundles, "_stage_bundle_at", stage_then_swap)

    with (
        workflow_bundles.resolve_bundle(
            source, "main", "example-bundle", environ=environment
        ) as candidate,
        pytest.raises(ValueError, match="bundle filesystem operation failed") as failure,
    ):
        workflow_bundles.import_bundle(
            project, candidate, apply=True, expected_commit=candidate.resolved_commit
        )

    assert _snapshot(project) == before_replacement
    assert (displaced / "ai-dlc.toml").read_bytes() == b"schema = 4\n"
    assert not (displaced / ".ai-dlc/bundles/example-bundle").exists()
    if swap_point == "after-acquire":
        _assert_import_residue_reported(displaced, failure.value)


def test_post_stage_conflict_retains_stage_and_reports_it(tmp_path, monkeypatch):
    """An authored edit detected after staging is preserved and residue is discoverable."""
    from ai_dlc.harness import workflow_bundles as bundles

    project = _bundle_project(tmp_path)
    first, second = _local_candidate(tmp_path, "1"), _local_candidate(tmp_path, "2")
    bundles.import_bundle(project, first, apply=True, expected_commit=first.resolved_commit)
    edited = project / ".ai-dlc/bundles/example-bundle/templates/product-brief.md"
    original_stage = bundles._stage_bundle_at

    def stage_then_edit(*args):
        result = original_stage(*args)
        edited.write_bytes(b"authored active edit\r\n")
        return result

    monkeypatch.setattr(bundles, "_stage_bundle_at", stage_then_edit)
    result = bundles.import_bundle(
        project, second, apply=True, expected_commit=second.resolved_commit
    )
    assert not result["applied"] and result["conflicts"]
    assert edited.read_bytes() == b"authored active edit\r\n"
    assert result["retained_paths"]
    assert all((project / path).exists() for path in result["retained_paths"])


def test_stage_open_failure_after_create_retains_and_reports_stage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """A failed stage open must retain and report the directory already created."""
    from ai_dlc.harness import workflow_bundles

    _, source, environment = _bundle_repository(tmp_path)
    project = _bundle_project(tmp_path)
    before = _snapshot(project)
    real_open = workflow_bundles._open_named_directory
    failed = False

    def fail_stage_open_once(parent: int, name: str) -> int:
        nonlocal failed
        if ".stage-" in name and not failed:
            failed = True
            raise OSError("credential-sentinel")
        return real_open(parent, name)

    monkeypatch.setattr(workflow_bundles, "_open_named_directory", fail_stage_open_once)
    with (
        workflow_bundles.resolve_bundle(
            source, "main", "example-bundle", environ=environment
        ) as candidate,
        pytest.raises(ValueError, match="bundle filesystem operation failed") as failure,
    ):
        workflow_bundles.import_bundle(
            project, candidate, apply=True, expected_commit=candidate.resolved_commit
        )

    assert all(_snapshot(project)[name] == value for name, value in before.items())
    assert not (project / ".ai-dlc/bundles/example-bundle").exists()
    _assert_import_residue_reported(project, failure.value)


def test_first_import_placeholder_swap_preserves_empty_authored_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Would fail if first publication clobbered a concurrent empty authored destination."""
    from ai_dlc.harness import workflow_bundles

    _, source, environment = _bundle_repository(tmp_path)
    project = _bundle_project(tmp_path)
    real_publish = workflow_bundles._rename_directory_noreplace

    def create_then_publish(parent: int, source_name: str, bundle_id: str) -> None:
        os.mkdir(bundle_id, dir_fd=parent)
        real_publish(parent, source_name, bundle_id)

    monkeypatch.setattr(workflow_bundles, "_rename_directory_noreplace", create_then_publish)
    with (
        workflow_bundles.resolve_bundle(
            source, "main", "example-bundle", environ=environment
        ) as candidate,
        pytest.raises(ValueError, match="bundle filesystem operation failed"),
    ):
        workflow_bundles.import_bundle(
            project, candidate, apply=True, expected_commit=candidate.resolved_commit
        )

    destination = project / ".ai-dlc/bundles/example-bundle"
    assert destination.is_dir()
    assert list(destination.iterdir()) == []


def test_first_import_detects_placeholder_swap_inside_replace_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Would fail if a swap after the precheck let replace erase an empty authored directory."""
    from ai_dlc.harness import workflow_bundles

    _, source, environment = _bundle_repository(tmp_path)
    project = _bundle_project(tmp_path)
    real_replace = workflow_bundles.os.replace
    swapped = False

    def swap_inside_replace(
        source_name: object, destination_name: object, **kwargs: object
    ) -> None:
        nonlocal swapped
        if destination_name == "example-bundle" and not swapped:
            swapped = True
            bundles = project / ".ai-dlc/bundles"
            (bundles / "example-bundle").rename(bundles / "displaced-placeholder")
            (bundles / "example-bundle").mkdir()
        real_replace(source_name, destination_name, **kwargs)

    monkeypatch.setattr(workflow_bundles.os, "replace", swap_inside_replace)
    with workflow_bundles.resolve_bundle(
        source, "main", "example-bundle", environ=environment
    ) as candidate:
        result = workflow_bundles.import_bundle(
            project, candidate, apply=True, expected_commit=candidate.resolved_commit
        )

    assert result["applied"] is True
    assert swapped is False


@pytest.mark.parametrize("created_name", [".ai-dlc", "bundles"])
def test_created_destination_parent_is_removed_when_immediate_open_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, created_name: str
):
    """Would fail if mkdir escaped cleanup coverage before its descriptor opened."""
    from ai_dlc.harness import workflow_bundles

    _, source, environment = _bundle_repository(tmp_path)
    project = _bundle_project(tmp_path)
    if created_name == "bundles":
        (project / ".ai-dlc").mkdir()
    before = _snapshot(project)
    real_open = workflow_bundles._open_named_directory
    failed = False

    def fail_created_open_once(parent: int, name: str) -> int:
        nonlocal failed
        created_path = (
            project / ".ai-dlc" if created_name == ".ai-dlc" else project / ".ai-dlc/bundles"
        )
        if name == created_name and created_path.exists() and not failed:
            failed = True
            raise OSError("credential-sentinel")
        return real_open(parent, name)

    monkeypatch.setattr(workflow_bundles, "_open_named_directory", fail_created_open_once)
    with (
        workflow_bundles.resolve_bundle(
            source, "main", "example-bundle", environ=environment
        ) as candidate,
        pytest.raises(ValueError, match="bundle filesystem operation failed"),
    ):
        workflow_bundles.import_bundle(
            project, candidate, apply=True, expected_commit=candidate.resolved_commit
        )

    assert _snapshot(project) == before


def test_first_import_never_uses_overwriting_replace_after_external_placeholder_displacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Would fail when replace lost a placeholder moved outside the searched parent."""
    from ai_dlc.harness import workflow_bundles

    _, source, environment = _bundle_repository(tmp_path)
    project = _bundle_project(tmp_path)
    outside = tmp_path / "outside-placeholder"
    real_replace = workflow_bundles.os.replace
    swapped = False

    def displace_outside_replace(
        source_name: object, destination_name: object, **kwargs: object
    ) -> None:
        nonlocal swapped
        if destination_name == "example-bundle" and not swapped:
            swapped = True
            bundles = project / ".ai-dlc/bundles"
            (bundles / "example-bundle").rename(outside)
            (bundles / "example-bundle").mkdir()
        real_replace(source_name, destination_name, **kwargs)

    monkeypatch.setattr(workflow_bundles.os, "replace", displace_outside_replace)
    with workflow_bundles.resolve_bundle(
        source, "main", "example-bundle", environ=environment
    ) as candidate:
        result = workflow_bundles.import_bundle(
            project, candidate, apply=True, expected_commit=candidate.resolved_commit
        )

    assert result["applied"] is True
    assert swapped is False
    assert not outside.exists()


def test_first_import_atomic_no_clobber_preserves_concurrent_empty_authored_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Would fail if first publication overwrote a destination created at its atomic boundary."""
    from ai_dlc.harness import workflow_bundles

    _, source, environment = _bundle_repository(tmp_path)
    project = _bundle_project(tmp_path)
    real_publish = getattr(workflow_bundles, "_rename_directory_noreplace", None)
    called = False

    def create_then_publish(parent: int, source_name: str, destination_name: str) -> None:
        nonlocal called
        called = True
        os.mkdir(destination_name, dir_fd=parent)
        assert real_publish is not None
        real_publish(parent, source_name, destination_name)

    monkeypatch.setattr(
        workflow_bundles, "_rename_directory_noreplace", create_then_publish, raising=False
    )
    with (
        workflow_bundles.resolve_bundle(
            source, "main", "example-bundle", environ=environment
        ) as candidate,
        pytest.raises(ValueError, match="bundle filesystem operation failed") as failure,
    ):
        workflow_bundles.import_bundle(
            project, candidate, apply=True, expected_commit=candidate.resolved_commit
        )

    destination = project / ".ai-dlc/bundles/example-bundle"
    assert called is True
    assert destination.is_dir()
    assert list(destination.iterdir()) == []
    _assert_import_residue_reported(project, failure.value)


def test_first_import_fails_closed_when_atomic_no_clobber_is_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Would fail if an unsupported host fell back to an overwriting directory rename."""
    from ai_dlc.harness import workflow_bundles

    _, source, environment = _bundle_repository(tmp_path)
    project = _bundle_project(tmp_path)
    before = _snapshot(project)
    monkeypatch.setattr(workflow_bundles.sys, "platform", "unsupported-test-platform")

    with (
        workflow_bundles.resolve_bundle(
            source, "main", "example-bundle", environ=environment
        ) as candidate,
        pytest.raises(ValueError, match="bundle filesystem operation failed") as failure,
    ):
        workflow_bundles.import_bundle(
            project, candidate, apply=True, expected_commit=candidate.resolved_commit
        )

    assert all(_snapshot(project)[name] == value for name, value in before.items())
    assert not (project / ".ai-dlc/bundles/example-bundle").exists()
    _assert_import_residue_reported(project, failure.value)


def _local_candidate(tmp_path: Path, revision: str):
    """A local service fixture; does not assert remote source qualification."""
    from ai_dlc.harness.workflow_bundles import BundleCandidate

    root = tmp_path / ("candidate-" + revision)
    root.mkdir()
    manifest = _write_bundle(
        root,
        templates={"product-brief": ("templates/product-brief.md", f"# {revision}\n".encode())},
    )
    return BundleCandidate(
        "https://example.test/bundle.git",
        "main",
        "example-bundle",
        revision * 40,
        root,
        manifest,
        _digest((root / "bundle.json").read_bytes()),
        manifest["files"],
    )


@pytest.mark.parametrize("mutation", ["entry", "edit", "replacement"])
def test_import_retains_authored_backup_occupants(tmp_path, monkeypatch, mutation):
    """A successful update must not recursively delete newly authored backup occupants."""
    from ai_dlc.harness import workflow_bundles as bundles

    project = _bundle_project(tmp_path)
    first, second = _local_candidate(tmp_path, "1"), _local_candidate(tmp_path, "2")
    bundles.import_bundle(project, first, apply=True, expected_commit=first.resolved_commit)
    parent = project / ".ai-dlc/bundles"
    original_verify = bundles._verify_named_directory
    authored = None
    inode = None

    def edit_backup_after_publication(parent_fd, name, descriptor):
        nonlocal authored, inode
        original_verify(parent_fd, name, descriptor)
        backups = list(parent.glob(".example-bundle.backup*"))
        if name == "example-bundle" and backups and authored is None:
            backup = backups[0]
            if mutation == "replacement":
                backup.rename(tmp_path / "displaced-backup")
                backup.mkdir()
            authored = backup / (
                "templates/product-brief.md" if mutation == "edit" else "authored.md"
            )
            authored.write_bytes(b"authored backup bytes\r\n")
            inode = authored.stat().st_ino

    monkeypatch.setattr(bundles, "_verify_named_directory", edit_backup_after_publication)
    result = bundles.import_bundle(
        project, second, apply=True, expected_commit=second.resolved_commit
    )
    assert authored is not None
    assert authored.exists(), "successful import deleted authored backup content"
    assert authored.read_bytes() == b"authored backup bytes\r\n"
    assert authored.stat().st_ino == inode
    assert any(authored.is_relative_to(project / path) for path in result["retained_paths"])
    assert (parent / "example-bundle/templates/product-brief.md").read_bytes() == b"# 2\n"


@pytest.mark.parametrize("update", [False, True])
@pytest.mark.parametrize("timing", ["staged", "published"])
@pytest.mark.parametrize("mutation", ["payload", "manifest", "lock", "entry", "replacement"])
def test_import_authenticates_complete_tree_and_retains_drift(
    tmp_path, monkeypatch, update, timing, mutation
):
    """Publishing a changed stage must fail visibly and preserve every authored byte."""
    from ai_dlc.harness import workflow_bundles as bundles

    project = _bundle_project(tmp_path)
    first, second = _local_candidate(tmp_path, "1"), _local_candidate(tmp_path, "2")
    destination = project / ".ai-dlc/bundles/example-bundle"
    if update:
        bundles.import_bundle(project, first, apply=True, expected_commit=first.resolved_commit)
    before = _snapshot(destination) if update else None
    authored_inode = None
    mutated = False

    def mutate(path):
        nonlocal mutated, authored_inode
        if mutation == "replacement":
            path.rename(tmp_path / "displaced-stage")
            path.mkdir()
        relative = {
            "payload": "templates/product-brief.md",
            "manifest": "bundle.json",
            "lock": "bundle.lock.json",
            "entry": "authored.md",
            "replacement": "authored.md",
        }[mutation]
        authored = path / relative
        authored.write_bytes(b"authored stage bytes\r\n")
        authored_inode = authored.stat().st_ino
        mutated = True

    if timing == "staged":
        original_stage = bundles._stage_bundle_at

        def stage_then_mutate(*args):
            result = original_stage(*args)
            mutate(destination.parent / result[0])
            return result

        monkeypatch.setattr(bundles, "_stage_bundle_at", stage_then_mutate)
    else:
        original_verify = bundles._verify_named_directory

        def verify_then_mutate(parent, name, descriptor):
            original_verify(parent, name, descriptor)
            if name == "example-bundle" and not mutated:
                mutate(destination)

        monkeypatch.setattr(bundles, "_verify_named_directory", verify_then_mutate)

    with pytest.raises(ValueError) as failure:
        bundles.import_bundle(project, second, apply=True, expected_commit=second.resolved_commit)
    assert mutated
    preserved = [
        path
        for path in project.rglob("*")
        if path.is_file() and path.read_bytes() == b"authored stage bytes\r\n"
    ]
    assert len(preserved) == 1
    assert preserved[0].stat().st_ino == authored_inode
    notes = "\n".join(getattr(failure.value, "__notes__", []))
    assert any(part in notes for part in preserved[0].parts if part.startswith(".example-bundle."))
    if update:
        assert _snapshot(destination) == before
    else:
        assert not destination.exists()


def test_import_rollback_preserves_concurrent_destination_and_reports_original_backup(
    tmp_path, monkeypatch
):
    """Recovery must not clobber an authored destination that appeared during publication."""
    from ai_dlc.harness import workflow_bundles as bundles

    project = _bundle_project(tmp_path)
    first, second = _local_candidate(tmp_path, "1"), _local_candidate(tmp_path, "2")
    bundles.import_bundle(project, first, apply=True, expected_commit=first.resolved_commit)
    destination = project / ".ai-dlc/bundles/example-bundle"
    before = _snapshot(destination)
    original_rename = bundles._rename_directory_noreplace

    def occupy_before_publish(parent, source, target):
        if ".stage-" in source and target == "example-bundle":
            destination.mkdir()
            (destination / "authored.md").write_bytes(b"concurrent destination\r\n")
        original_rename(parent, source, target)

    monkeypatch.setattr(bundles, "_rename_directory_noreplace", occupy_before_publish)
    with pytest.raises(ValueError) as failure:
        bundles.import_bundle(project, second, apply=True, expected_commit=second.resolved_commit)
    assert (destination / "authored.md").read_bytes() == b"concurrent destination\r\n"
    backup = next(destination.parent.glob(".example-bundle.backup-*"))
    assert _snapshot(backup) == before
    notes = "\n".join(failure.value.__notes__)
    assert backup.relative_to(project).as_posix() in notes
    assert ".ai-dlc/bundles/example-bundle;" in notes


@pytest.mark.parametrize("mutation", ["edit", "replacement"])
def test_failed_import_stage_creation_retains_authored_state(tmp_path, monkeypatch, mutation):
    """A partially constructed stage is never recursively removed after a write failure."""
    from ai_dlc.harness import workflow_bundles as bundles

    project = _bundle_project(tmp_path)
    candidate = _local_candidate(tmp_path, "1")
    authored = None
    original_write = bundles._write_regular_file_at

    def write_then_fail(root, path, content):
        nonlocal authored
        original_write(root, path, content)
        stage = next((project / ".ai-dlc/bundles").glob(".example-bundle.stage-*"))
        if mutation == "replacement":
            stage.rename(tmp_path / "displaced-partial-stage")
            stage.mkdir()
        authored = stage / "authored.md"
        authored.write_bytes(b"partial stage authored content\r\n")
        raise OSError("credential-sentinel")

    monkeypatch.setattr(bundles, "_write_regular_file_at", write_then_fail)
    with pytest.raises(ValueError) as failure:
        bundles.import_bundle(
            project, candidate, apply=True, expected_commit=candidate.resolved_commit
        )
    assert authored is not None
    assert authored.read_bytes() == b"partial stage authored content\r\n"
    assert authored.parent.relative_to(project).as_posix() in "\n".join(failure.value.__notes__)
    assert "credential-sentinel" not in str(failure.value)


def _assert_import_residue_reported(project, failure):
    retained = list((project / ".ai-dlc/bundles").glob(".example-bundle.*"))
    assert retained
    notes = "\n".join(failure.__notes__)
    assert all(path.relative_to(project).as_posix() in notes for path in retained)


@pytest.mark.parametrize("update", [False, True])
@pytest.mark.parametrize("timing", ["staged", "published"])
def test_import_rejects_unlisted_empty_directory_and_retains_it(
    tmp_path, monkeypatch, update, timing
):
    """Comparing only regular-file bytes must not accept an undeclared empty directory."""
    from ai_dlc.harness import workflow_bundles as bundles

    project = _bundle_project(tmp_path)
    first, second = _local_candidate(tmp_path, "1"), _local_candidate(tmp_path, "2")
    destination = project / ".ai-dlc/bundles/example-bundle"
    if update:
        bundles.import_bundle(project, first, apply=True, expected_commit=first.resolved_commit)
    mutated = False
    if timing == "staged":
        original_stage = bundles._stage_bundle_at

        def stage_then_add(*args):
            result = original_stage(*args)
            (destination.parent / result[0] / "authored-empty").mkdir()
            return result

        monkeypatch.setattr(bundles, "_stage_bundle_at", stage_then_add)
    else:
        original_verify = bundles._verify_named_directory

        def verify_then_add(parent, name, descriptor):
            nonlocal mutated
            original_verify(parent, name, descriptor)
            if name == "example-bundle" and not mutated:
                (destination / "authored-empty").mkdir()
                mutated = True

        monkeypatch.setattr(bundles, "_verify_named_directory", verify_then_add)
    with pytest.raises(ValueError) as failure:
        bundles.import_bundle(project, second, apply=True, expected_commit=second.resolved_commit)
    retained = list(project.rglob("authored-empty"))
    assert len(retained) == 1 and retained[0].is_dir()
    assert retained[0].parent.relative_to(project).as_posix() in "\n".join(failure.value.__notes__)
    if update:
        assert (destination / "templates/product-brief.md").read_bytes() == b"# 1\n"
    else:
        assert not destination.exists()


def test_import_cli_reports_retained_stage_paths_without_leaking_error_details(
    tmp_path, monkeypatch
):
    """The command must expose retained-file guidance rather than discard exception notes."""
    from typer.testing import CliRunner

    from ai_dlc.cli import app
    from ai_dlc.harness import workflow_bundles as bundles

    project = _bundle_project(tmp_path)
    candidate = _local_candidate(tmp_path, "1")
    monkeypatch.setattr(bundles, "resolve_bundle", lambda *args, **kwargs: candidate)
    original_write = bundles._write_regular_file_at

    def fail_after_write(*args):
        original_write(*args)
        error = OSError("credential-sentinel")
        error.add_note("credential-sentinel")
        raise error

    monkeypatch.setattr(bundles, "_write_regular_file_at", fail_after_write)
    result = CliRunner().invoke(
        app,
        [
            "agents",
            "bundle",
            "import",
            candidate.source,
            "--ref",
            "main",
            "--id",
            candidate.bundle_id,
            "--root",
            str(project),
            "--apply",
            "--expected-commit",
            candidate.resolved_commit,
        ],
    )
    assert result.exit_code == 2
    retained = next((project / ".ai-dlc/bundles").glob(".example-bundle.stage-*"))
    assert retained.relative_to(project).as_posix() in result.output
    assert "inspect before removal" in result.output
    assert "credential-sentinel" not in result.output


@pytest.mark.parametrize("timing", ["backup-check", "restore-check", "restore"])
@pytest.mark.parametrize("mutation", ["replacement", "edit", "entry"])
def test_import_recovery_authenticates_backup_source(tmp_path, monkeypatch, timing, mutation):
    """Recovery must refuse a known changed source and report a late changed restore."""
    from ai_dlc.harness import workflow_bundles as bundles

    project = _bundle_project(tmp_path)
    first, second = _local_candidate(tmp_path, "1"), _local_candidate(tmp_path, "2")
    bundles.import_bundle(project, first, apply=True, expected_commit=first.resolved_commit)
    parent = project / ".ai-dlc/bundles"
    destination = parent / "example-bundle"
    previous = _snapshot(destination)
    displaced = tmp_path / "externally-moved-backup"
    original_verify = bundles._verify_named_directory
    original_rename = bundles._rename_directory_noreplace
    authored = None
    authored_inode = None
    backup_name = None
    restore_attempted = False
    publication_failed = False

    def mutate(name):
        nonlocal authored, authored_inode, backup_name
        backup_name = name
        backup = parent / name
        if mutation == "replacement":
            backup.rename(displaced)
            backup.mkdir()
        authored = backup / ("templates/product-brief.md" if mutation == "edit" else "authored.md")
        authored.write_bytes(b"authored recovery source\r\n")
        authored_inode = authored.stat().st_ino

    def verify(parent_fd, name, descriptor):
        if (
            (timing == "backup-check" or (timing == "restore-check" and publication_failed))
            and ".backup-" in name
            and authored is None
        ):
            mutate(name)
        original_verify(parent_fd, name, descriptor)

    def rename(parent_fd, source, target):
        nonlocal restore_attempted, publication_failed
        if timing in {"restore-check", "restore"} and ".stage-" in source:
            publication_failed = True
            raise OSError("publication failed")
        if ".backup-" in source and target == "example-bundle":
            restore_attempted = True
            if timing == "restore" and authored is None:
                mutate(source)
        original_rename(parent_fd, source, target)

    monkeypatch.setattr(bundles, "_verify_named_directory", verify)
    monkeypatch.setattr(bundles, "_rename_directory_noreplace", rename)
    with pytest.raises(ValueError) as failure:
        bundles.import_bundle(project, second, apply=True, expected_commit=second.resolved_commit)

    assert authored is not None
    preserved = [
        path
        for path in project.rglob("*")
        if path.is_file() and path.read_bytes() == b"authored recovery source\r\n"
    ]
    assert len(preserved) == 1
    assert preserved[0].stat().st_ino == authored_inode
    notes = "\n".join(failure.value.__notes__)
    assert "recovery could not restore" in notes
    assert f".ai-dlc/bundles/{backup_name};" in notes
    assert ".ai-dlc/bundles/example-bundle;" in notes
    if timing != "restore":
        assert not restore_attempted, "known changed backup was moved into active ownership"
        assert not destination.exists()
        assert preserved[0] == authored
    else:
        assert restore_attempted
        assert preserved[0].is_relative_to(destination)
    if mutation == "replacement":
        assert _snapshot(displaced) == previous
