import pytest

from ai_dlc.workstation import activate_workstation


def test_activation_preserves_user_config_and_converges(tmp_path):
    rc = tmp_path / ".zshrc"
    rc.write_text("export MY_SETTING=yes\n")
    config = tmp_path / ".config/mise/config.toml"
    config.parent.mkdir(parents=True)
    config.write_text('[settings]\nverbose=true\n[tools]\nnode="20.0.0"\n')
    args = (
        tmp_path,
        {"python": "3.12.11", "node": "22.0.0"},
        "/bin/mise",
        tmp_path / "bootstrap/bin",
    )
    result = activate_workstation(*args)
    assert not result["ready"]
    assert "20.0.0" in config.read_text()
    assert "verbose = true" in config.read_text()
    before = (rc.read_bytes(), config.read_bytes())
    activate_workstation(*args)
    assert before == (rc.read_bytes(), config.read_bytes())
    assert rc.read_text().startswith("export MY_SETTING=yes")
    rc.write_text(rc.read_text().replace("activate zsh", "activate bash"))
    with pytest.raises(ValueError, match="conflict"):
        activate_workstation(*args)


def test_native_installer_rejects_mismatch_before_execution(tmp_path, monkeypatch):
    from ai_dlc import workstation

    monkeypatch.setattr(workstation.shutil, "which", lambda name: None)
    monkeypatch.setattr(workstation.Path, "exists", lambda path: False)

    class Response:
        content = b"tampered"

        def raise_for_status(self):
            pass

    monkeypatch.setattr(workstation.httpx, "get", lambda *a, **kw: Response())
    invoked = []
    monkeypatch.setattr(workstation.subprocess, "run", lambda *a, **kw: invoked.append(a))
    with pytest.raises(ValueError, match="digest mismatch"):
        workstation.ensure_brew(tmp_path, "arm64")
    assert not invoked
