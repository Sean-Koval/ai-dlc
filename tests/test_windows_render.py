"""Native render transaction semantics; POSIX shim tests do not qualify Windows."""

import contextlib
import os
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def storage(monkeypatch):
    from ai_dlc.harness import windows_render

    if os.name == "nt":
        return windows_render._storage()

    # Exercise transaction logic on real temporary files. Native CI uses real handles.
    def snapshot(path):
        info = path.lstat()
        if path.is_symlink() or not path.is_file():
            raise ValueError("unsafe file")
        return path.read_bytes(), (info.st_dev, info.st_ino, 0)

    @contextlib.contextmanager
    def guard(path, *, create_parents=False):
        if create_parents:
            path.mkdir(parents=True, exist_ok=True)
        if not path.is_dir() or path.is_symlink():
            raise ValueError("unsafe directory")
        yield None

    def publish(path, data, *, create_only=False, **_):
        with path.open("xb" if create_only else "wb") as stream:
            stream.write(data)
        return True

    def create(path, data):
        publish(path, data, create_only=True)
        return snapshot(path)

    def move(source, destination, *, expected, expected_identity):
        if snapshot(source) != (expected, expected_identity):
            raise ValueError("source changed")
        if destination.exists():
            raise FileExistsError(destination)
        # This shim is not a native security primitive and makes no race guarantee.
        source.rename(destination)

    def relative(value):
        if ".." in Path(value).parts or Path(value).is_absolute():
            raise ValueError("unsafe relative path")
        return value

    backend = SimpleNamespace(
        safe_snapshot=snapshot,
        guarded_path=guard,
        atomic_publish=publish,
        create_owned=create,
        move_owned=move,
        validate_relative=relative,
    )
    monkeypatch.setattr(windows_render, "_storage", lambda: backend)
    return backend


def test_native_transaction_updates_removes_and_retains_backups(tmp_path, storage):
    from ai_dlc.harness.windows_render import WindowsRenderState

    (tmp_path / "old.md").write_bytes(b"old")
    with WindowsRenderState(tmp_path) as state:
        assert state.read("old.md") == b"old"
        assert state.read("new/guide.md") is None
        retained = state.apply({"new/guide.md": b"new"}, ["old.md"], ["new/guide.md", "old.md"])
    assert not (tmp_path / "old.md").exists()
    assert (tmp_path / "new/guide.md").read_bytes() == b"new"
    assert len(retained) == 1
    assert (tmp_path / retained[0]).read_bytes() == b"old"


def test_native_transaction_refuses_same_bytes_replaced_after_planning(tmp_path, storage):
    from ai_dlc.harness.windows_render import WindowsRenderState

    target = tmp_path / "guide.md"
    target.write_bytes(b"before")
    with WindowsRenderState(tmp_path) as state:
        state.read("guide.md")
        target.rename(tmp_path / "original.md")
        target.write_bytes(b"before")
        with pytest.raises(ValueError, match="changed"):
            state.apply({"guide.md": b"after"}, [], ["guide.md"])
    assert target.read_bytes() == b"before"


def test_native_recovery_preserves_late_authored_occupant(tmp_path, storage, monkeypatch):
    from ai_dlc.harness.windows_render import WindowsRenderState

    target = tmp_path / "guide.md"
    target.write_bytes(b"before")
    move = storage.move_owned

    def inject(source, destination, **kwargs):
        if destination == target:
            destination.write_bytes(b"late author")
        return move(source, destination, **kwargs)

    monkeypatch.setattr(storage, "move_owned", inject)
    with WindowsRenderState(tmp_path) as state:
        state.read("guide.md")
        with pytest.raises(FileExistsError) as error:
            state.apply({"guide.md": b"after"}, [], ["guide.md"])
    assert target.read_bytes() == b"late author"
    assert any(p.read_bytes() == b"before" for p in tmp_path.glob(".ai-dlc-*"))
    assert "retained" in " ".join(error.value.__notes__)


def test_native_recovery_restores_previous_files_without_overwrite(tmp_path, storage, monkeypatch):
    from ai_dlc.harness.windows_render import WindowsRenderState

    for name in ("a.md", "b.md"):
        (tmp_path / name).write_bytes(b"before")
    move = storage.move_owned
    failed = False

    def inject(source, destination, **kwargs):
        nonlocal failed
        if destination == tmp_path / "b.md" and kwargs["expected"] == b"after" and not failed:
            failed = True
            raise OSError("injected failure")
        return move(source, destination, **kwargs)

    monkeypatch.setattr(storage, "move_owned", inject)
    with WindowsRenderState(tmp_path) as state:
        for name in ("a.md", "b.md"):
            state.read(name)
        with pytest.raises(OSError, match="injected"):
            state.apply({"a.md": b"after", "b.md": b"after"}, [], ["a.md", "b.md"])
    assert (tmp_path / "a.md").read_bytes() == b"before"
    assert (tmp_path / "b.md").read_bytes() == b"before"


def test_native_team_source_render_is_idempotent_and_preserves_authored_conflict(
    tmp_path, storage, monkeypatch
):
    from ai_dlc.environment.source_content import SourceItem
    from ai_dlc.environment.team_sources import SelectedSources
    from ai_dlc.harness import agents
    from ai_dlc.harness.windows_render import render_windows

    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[roles]\nagent-client=["codex"]\n[agents]\nskills=[]\n'
    )
    body = "---\nname: team-guide\ndescription: Team checks\n---\nRun the team check.\n"
    selected = SelectedSources(
        items=[
            ("team", SourceItem("skill", "team-guide", "skills/team-guide/SKILL.md", body=body))
        ],
        enrolled=True,
    )
    monkeypatch.setattr(agents, "enrolled_sources", lambda: selected)
    assert render_windows(tmp_path, apply=True)["applied"]
    assert render_windows(tmp_path)["clean"]
    skill = tmp_path / ".agents/skills/team-guide/SKILL.md"
    assert skill.read_text() == body
    skill.write_text("authored modification")
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    with pytest.raises(ValueError, match="conflict"):
        render_windows(tmp_path, apply=True)
    assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}


def test_native_vendored_bundle_refusal_precedes_any_render_writes(tmp_path, storage):
    from ai_dlc.harness.windows_render import render_windows

    config = tmp_path / "ai-dlc.toml"
    config.write_text('schema=4\n[agents]\nbundles=["company"]\n')
    with pytest.raises(ValueError, match="vendored.*Windows"):
        render_windows(tmp_path, apply=True)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["ai-dlc.toml"]


def test_native_recovery_preserves_late_authored_deletion(tmp_path, storage, monkeypatch):
    from ai_dlc.harness.windows_render import WindowsRenderState

    for name in ("a.md", "b.md"):
        (tmp_path / name).write_bytes(b"before")
    move = storage.move_owned

    def inject(source, destination, **kwargs):
        if destination == tmp_path / "b.md" and kwargs["expected"] == b"after":
            (tmp_path / "a.md").unlink()
            raise OSError("later publication failed")
        return move(source, destination, **kwargs)

    monkeypatch.setattr(storage, "move_owned", inject)
    with WindowsRenderState(tmp_path) as state:
        for name in ("a.md", "b.md"):
            state.read(name)
        with pytest.raises(OSError, match="later publication"):
            state.apply({"a.md": b"after", "b.md": b"after"}, [], ["a.md", "b.md"])
    assert not (tmp_path / "a.md").exists()
    assert any(p.read_bytes() == b"before" for p in tmp_path.glob(".ai-dlc-*"))


def test_native_stage_replacement_is_not_adopted_as_owned(tmp_path, storage, monkeypatch):
    from ai_dlc.harness.windows_render import WindowsRenderState

    create = storage.create_owned

    def replace_stage(path, body):
        created = create(path, body)
        path.rename(path.with_suffix(".authentic"))
        path.write_bytes(body)
        return created

    monkeypatch.setattr(storage, "create_owned", replace_stage)
    with WindowsRenderState(tmp_path) as state:
        state.read("guide.md")
        with pytest.raises(ValueError, match="stage changed"):
            state.apply({"guide.md": b"after"}, [], ["guide.md"])
    assert not (tmp_path / "guide.md").exists()
    assert all(p.read_bytes() == b"after" for p in tmp_path.glob(".ai-dlc-*"))
