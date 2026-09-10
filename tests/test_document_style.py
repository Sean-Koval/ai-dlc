import json

import pytest


def api():
    from ai_dlc.documentation.document_style import check_style

    return check_style


def test_optional_vale_unavailable_does_not_install(tmp_path, monkeypatch):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/a.md").write_text("# Guide\n")
    monkeypatch.setenv("PATH", str(tmp_path))
    result = api()(tmp_path, paths=["docs/a.md"])
    assert result["status"] == "unavailable"
    assert result["tool"] == "vale"


def test_vale_adapter_reports_alerts_without_edits(tmp_path, monkeypatch):
    (tmp_path / "docs").mkdir()
    source = tmp_path / "docs/a.md"
    source.write_text("# Guide\nObviously amazing.\n")
    executable = tmp_path / "vale"
    alerts = {"docs/a.md": [{"Message": "Avoid vague praise", "Severity": "warning"}]}
    executable.write_text(
        '#!/bin/sh\n[ "$1" = "--output=JSON" ] || exit 2\nprintf \'%s\\n\' \''
        + json.dumps(alerts)
        + "'\nexit 1\n"
    )
    executable.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))
    result = api()(tmp_path, paths=["docs/a.md"])
    assert result["status"] == "findings"
    assert result["alerts"] == alerts
    assert source.read_text() == "# Guide\nObviously amazing.\n"
    with pytest.raises(ValueError):
        api()(tmp_path, paths=["../private.md"])
