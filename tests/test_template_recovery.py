"""Recovery preserves writers that change files after template staging."""

import os
import subprocess

import pytest

from ai_dlc.setup.templates import apply_files


@pytest.mark.skipif(
    os.name == "nt",
    reason="POSIX publisher fault injection; native recovery has handle-backed cases",
)
def test_template_rollback_preserves_late_authored_bytes(tmp_path, monkeypatch):
    before = {"a.txt": b"old a", "b.txt": b"old b"}
    after = {"a.txt": b"new a", "b.txt": b"new b"}
    for name, body in before.items():
        (tmp_path / name).write_bytes(body)
    from ai_dlc.harness import agents

    publish = agents._publish_render_change

    def fail_second(state, change, content):
        if change.path == "b.txt":
            (tmp_path / "a.txt").write_bytes(b"authored a")
            (tmp_path / "b.txt").write_bytes(b"authored b")
            raise OSError("injected publication failure")
        return publish(state, change, content)

    monkeypatch.setattr(agents, "_publish_render_change", fail_second)
    with pytest.raises(OSError, match="injected"):
        apply_files(tmp_path, before, after)
    assert (tmp_path / "a.txt").read_bytes() == b"authored a"
    assert (tmp_path / "b.txt").read_bytes() == b"authored b"


@pytest.mark.skipif(
    os.name == "nt",
    reason="POSIX publisher fault injection; native recovery has handle-backed cases",
)
def test_template_rollback_restores_unchanged_published_file(tmp_path, monkeypatch):
    before = {"a.txt": b"old a", "b.txt": b"old b"}
    for name, body in before.items():
        (tmp_path / name).write_bytes(body)
    from ai_dlc.harness import agents

    publish = agents._publish_render_change

    def fail_second(state, change, content):
        if change.path == "b.txt":
            raise OSError("injected publication failure")
        return publish(state, change, content)

    monkeypatch.setattr(agents, "_publish_render_change", fail_second)
    with pytest.raises(OSError, match="injected"):
        apply_files(tmp_path, before, {"a.txt": b"new a", "b.txt": b"new b"})
    assert (tmp_path / "a.txt").read_bytes() == b"old a"
    assert (tmp_path / "b.txt").read_bytes() == b"old b"


@pytest.mark.skipif(os.name != "nt", reason="requires the real native Windows storage backend")
def test_native_template_update_retains_recovery_bytes(tmp_path):
    before = {"a.txt": b"before", "removed.txt": b"remove"}
    for name, body in before.items():
        (tmp_path / name).write_bytes(body)
    changed = apply_files(tmp_path, before, {"a.txt": b"after", "new/guide.md": b"new"})
    assert changed == ["a.txt", "new/guide.md", "removed.txt"]
    assert (tmp_path / "a.txt").read_bytes() == b"after"
    assert not (tmp_path / "removed.txt").exists()
    assert (tmp_path / "new/guide.md").read_bytes() == b"new"
    retained = [p.read_bytes() for p in tmp_path.glob(".ai-dlc-*")]
    assert b"before" in retained and b"remove" in retained


@pytest.mark.skipif(os.name != "nt", reason="requires native Windows junctions")
@pytest.mark.parametrize("linked_root", [False, True])
def test_native_template_snapshot_refuses_junction(tmp_path, linked_root):
    from ai_dlc.setup.templates import checkout_files

    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "authored.txt").write_bytes(b"retain")
    root = tmp_path / "project"
    root.mkdir()
    junction = root / "linked"
    subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(outside)],
        check=True,
        capture_output=True,
    )
    with pytest.raises(ValueError, match="reparse"):
        checkout_files(junction if linked_root else root)
    assert (outside / "authored.txt").read_bytes() == b"retain"
