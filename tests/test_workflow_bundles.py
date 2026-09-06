"""Workflow bundle manifest and payload validation."""

from __future__ import annotations

import hashlib
import json
import os
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


def test_loads_duplicate_key_free_utf8_bundle_manifest(tmp_path: Path):
    """Would fail if the raw loader did not return the complete JSON object."""
    from ai_dlc.workflow_bundles import load_bundle_manifest

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
    from ai_dlc.workflow_bundles import load_bundle_manifest

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
    from ai_dlc.workflow_bundles import load_bundle_manifest

    (tmp_path / "bundle.json").write_bytes(content)

    with pytest.raises(ValueError, match=message):
        load_bundle_manifest(tmp_path)


def test_raw_loader_rejects_manifest_larger_than_one_mib(tmp_path: Path):
    """Would fail if an oversized manifest were read and decoded."""
    from ai_dlc.workflow_bundles import load_bundle_manifest

    (tmp_path / "bundle.json").write_bytes(b" " * (1024 * 1024 + 1))

    with pytest.raises(ValueError, match="at most 1 MiB"):
        load_bundle_manifest(tmp_path)


@pytest.mark.parametrize("replacement", ["symlink", "directory"])
def test_raw_loader_requires_a_regular_bundle_json(tmp_path: Path, replacement: str):
    """Would fail if the manifest boundary followed a link or accepted a non-file."""
    from ai_dlc.workflow_bundles import load_bundle_manifest

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
    from ai_dlc.workflow_bundles import validate_bundle

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
            "schema must be 1",
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
    from ai_dlc.workflow_bundles import validate_bundle

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
    from ai_dlc.workflow_bundles import validate_bundle

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
    from ai_dlc.workflow_bundles import validate_bundle

    manifest = _write_bundle(tmp_path)
    old_path = manifest["skills"]["day-start"]
    manifest["skills"]["day-start"] = path
    manifest["files"][path] = manifest["files"].pop(old_path)
    _write_manifest(tmp_path, manifest)

    with pytest.raises(ValueError, match="relative normalized safe ASCII path"):
        validate_bundle(tmp_path, manifest)


def test_rejects_paths_deeper_than_sixteen_segments(tmp_path: Path):
    """Would fail if bundle traversal admitted an over-deep payload."""
    from ai_dlc.workflow_bundles import validate_bundle

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
    from ai_dlc.workflow_bundles import validate_bundle

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
    from ai_dlc.workflow_bundles import validate_bundle

    manifest = _write_bundle(tmp_path, skills={}, templates={})

    with pytest.raises(ValueError, match="at least one skill or template"):
        validate_bundle(tmp_path, manifest)


@pytest.mark.parametrize("collision", ["name", "path"])
def test_skill_and_template_exports_form_one_namespace(tmp_path: Path, collision: str):
    """Would fail if two exports could claim the same name or payload path."""
    from ai_dlc.workflow_bundles import validate_bundle

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
    from ai_dlc.workflow_bundles import validate_bundle

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
    from ai_dlc.workflow_bundles import validate_bundle

    manifest = _write_bundle(tmp_path)
    manifest["files"]["skills/day/SKILL.md"] = digest
    _write_manifest(tmp_path, manifest)

    with pytest.raises(ValueError, match="lowercase SHA-256"):
        validate_bundle(tmp_path, manifest)


def test_rejects_more_than_1024_payload_files(tmp_path: Path):
    """Would fail if a manifest could exceed the payload-count resource bound."""
    from ai_dlc.workflow_bundles import validate_bundle

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
    from ai_dlc.workflow_bundles import validate_bundle

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
    from ai_dlc.workflow_bundles import validate_bundle

    manifest = _write_bundle(tmp_path)
    path = tmp_path / "skills/day/SKILL.md"
    path.unlink()
    path.mkdir()

    with pytest.raises(ValueError, match="regular file"):
        validate_bundle(tmp_path, manifest)


def test_rejects_missing_and_extra_checkout_entries_without_writing(tmp_path: Path):
    """Would fail if incomplete or undeclared checkout content passed, or validation wrote."""
    from ai_dlc.workflow_bundles import validate_bundle

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
    from ai_dlc.workflow_bundles import validate_bundle

    manifest = _write_bundle(tmp_path)
    (tmp_path / ".git/objects").mkdir(parents=True)
    (tmp_path / ".git/HEAD").write_text("ref: refs/heads/main\n")

    assert validate_bundle(tmp_path, manifest)["id"] == "example-bundle"


def test_rejects_a_nested_git_entry_as_undeclared_content(tmp_path: Path):
    """Would fail if nested Git metadata received the checkout-root exception."""
    from ai_dlc.workflow_bundles import validate_bundle

    manifest = _write_bundle(tmp_path)
    (tmp_path / "skills/day/.git").mkdir()

    with pytest.raises(ValueError, match="checkout tree"):
        validate_bundle(tmp_path, manifest)


def test_rejects_a_payload_digest_mismatch(tmp_path: Path):
    """Would fail if tampered Markdown bytes passed authenticated validation."""
    from ai_dlc.workflow_bundles import validate_bundle

    manifest = _write_bundle(tmp_path)
    (tmp_path / "templates/product-brief.md").write_text("# Tampered\n")

    with pytest.raises(ValueError, match="digest mismatch"):
        validate_bundle(tmp_path, manifest)


def test_rejects_non_utf8_markdown(tmp_path: Path):
    """Would fail if payload bytes were authenticated but not portable UTF-8 Markdown."""
    from ai_dlc.workflow_bundles import validate_bundle

    manifest = _write_bundle(
        tmp_path,
        skills={},
        templates={"invalid": ("templates/invalid.md", b"\xff")},
    )

    with pytest.raises(ValueError, match="UTF-8 Markdown"):
        validate_bundle(tmp_path, manifest)


def test_rejects_a_payload_larger_than_two_mib(tmp_path: Path):
    """Would fail if a single payload could exceed its resource bound."""
    from ai_dlc.workflow_bundles import validate_bundle

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
    from ai_dlc.workflow_bundles import validate_bundle

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
    from ai_dlc.workflow_bundles import validate_bundle

    manifest = _write_bundle(
        tmp_path,
        skills={"day-start": ("skills/day/SKILL.md", content)},
        templates={},
    )

    with pytest.raises(ValueError, match=message):
        validate_bundle(tmp_path, manifest)


def test_accepts_the_maximum_skill_description_length(tmp_path: Path):
    """Would fail on an off-by-one error at the 1,024-character boundary."""
    from ai_dlc.workflow_bundles import validate_bundle

    content = b"---\nname: day-start\ndescription: " + b"a" * 1024 + b"\n---\n\n# Start\n"
    manifest = _write_bundle(
        tmp_path,
        skills={"day-start": ("skills/day/SKILL.md", content)},
        templates={},
    )

    assert validate_bundle(tmp_path, manifest)["skills"] == {"day-start": "skills/day/SKILL.md"}


def test_rejects_an_empty_template(tmp_path: Path):
    """Would fail if a template contained no usable Markdown body."""
    from ai_dlc.workflow_bundles import validate_bundle

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
    from ai_dlc import workflow_bundles

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
    from ai_dlc import workflow_bundles

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
    from ai_dlc import workflow_bundles

    manifest = _write_bundle(tmp_path)
    real_checkout_tree = workflow_bundles._checkout_tree
    mutated = False

    def mutate_after_scan(root: Path):
        nonlocal mutated
        snapshot = real_checkout_tree(root)
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
    from ai_dlc.workflow_bundles import validate_bundle

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
    from ai_dlc import workflow_bundles

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
    from ai_dlc.workflow_bundles import load_bundle_manifest

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
    from ai_dlc import workflow_bundles

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
    from ai_dlc.workflow_bundles import validate_bundle

    manifest = _write_bundle(tmp_path)
    overdeep = tmp_path
    for _ in range(17):
        overdeep /= "d"
    overdeep.mkdir(parents=True)

    with pytest.raises(ValueError, match="at most 16 path segments"):
        validate_bundle(tmp_path, manifest)
