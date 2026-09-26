"""Windows document access delegates to the guarded native storage boundary."""

import sys
from types import SimpleNamespace

import pytest

from ai_dlc.documentation import document_files


@pytest.mark.parametrize("operation", ["read", "create", "bounded"])
def test_native_documents_use_guarded_backend(monkeypatch, tmp_path, operation):
    calls = []
    backend = SimpleNamespace(
        safe_read=lambda path, **kwargs: calls.append(("read", path, kwargs)) or b"safe\n",
        atomic_publish=lambda path, body, **kwargs: (
            calls.append(("create", path, body, kwargs)) or True
        ),
    )
    monkeypatch.setitem(sys.modules, "ai_dlc._windows_storage", backend)
    monkeypatch.setattr(document_files, "os", SimpleNamespace(name="nt"))
    path = tmp_path / "note.md"
    if operation == "read":
        assert document_files.read_document(path) == b"safe\n"
    elif operation == "bounded":
        assert document_files.read_bounded(tmp_path, "note.md", 5)["content"] == "safe\n"
        assert calls[0][2] == {"max_bytes": 5}
    else:
        assert document_files.create_document(path, b"safe\n")
        assert calls[0][3] == {"create_only": True}
    assert len(calls) == 1
