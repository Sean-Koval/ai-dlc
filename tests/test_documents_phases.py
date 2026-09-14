"""Focused tests for the pure phase helpers behind ``check_documents``."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from ai_dlc.documentation.documents import (
    _catalogued_path,
    _document_file_findings,
    _duplicate_content_findings,
    _identity_findings,
    _link_findings,
    _markdown_documents,
    _metadata_findings,
    _read_catalog_entries,
    _replacement_findings,
    _review_findings,
    _scan_docs,
    _source_findings,
    _validate_entries,
)

TODAY = date(2026, 9, 8)


def _entry(**overrides) -> dict:
    entry = {
        "id": "guide",
        "path": "docs/guide.md",
        "kind": "runbook",
        "owner": "maintainers",
        "status": "active",
        "reviewed_on": "2026-09-01",
        "review_after_days": 90,
    }
    entry.update(overrides)
    return entry


def _codes(findings: list[dict]) -> list[str]:
    return [finding["code"] for finding in findings]


def test_read_catalog_entries_requires_schema_and_documents_array(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "catalog.toml").write_text('schema = 1\n[[documents]]\nid = "a"\npath = "docs/a.md"\n')
    assert _read_catalog_entries(tmp_path) == [{"id": "a", "path": "docs/a.md"}]

    (docs / "catalog.toml").write_text("schema = 2\ndocuments = []\n")
    with pytest.raises(ValueError, match="schema = 1"):
        _read_catalog_entries(tmp_path)

    (docs / "catalog.toml").unlink()
    with pytest.raises(FileNotFoundError):
        _read_catalog_entries(tmp_path)


def test_identity_findings_track_new_and_duplicate_ids():
    ids: set[str] = set()
    assert _identity_findings(_entry(), ids) == []
    assert ids == {"guide"}
    duplicate = _identity_findings(_entry(), ids)
    assert _codes(duplicate) == ["duplicate-id"]
    assert duplicate[0]["severity"] == "error"
    assert duplicate[0]["path"] == "docs/guide.md"
    blank = _identity_findings(_entry(id="  "), ids)
    assert _codes(blank) == ["invalid-metadata"]
    assert ids == {"guide"}


@pytest.mark.parametrize(
    ("relative", "expected"),
    [
        ("docs/guide.md", True),
        ("openspec/changes/x/proposal.md", True),
        ("src/module.py", False),
        ("", False),
        (None, False),
        (7, False),
    ],
)
def test_catalogued_path_accepts_only_docs_and_openspec(relative, expected):
    assert _catalogued_path(relative) is expected


def test_metadata_findings_report_kind_owner_and_review():
    assert _metadata_findings(_entry(), "docs/guide.md", TODAY) == []
    findings = _metadata_findings(
        _entry(kind="novel", owner="Unknown", reviewed_on="never"), "docs/guide.md", TODAY
    )
    assert _codes(findings) == ["invalid-metadata", "owner-missing", "review-unknown"]
    assert findings[0]["severity"] == "error"
    assert findings[1]["severity"] == "warning"


def test_metadata_findings_skip_review_for_retired_documents():
    entry = _entry(status="archived", reviewed_on="never", review_after_days=None)
    assert _metadata_findings(entry, "docs/guide.md", TODAY) == []


def test_review_findings_distinguish_overdue_from_unknown():
    assert _review_findings(_entry(), "docs/guide.md", TODAY) == []
    overdue = _review_findings(_entry(reviewed_on="2026-01-01"), "docs/guide.md", TODAY)
    assert _codes(overdue) == ["review-overdue"]
    for bad in (
        _entry(review_after_days=0),
        _entry(review_after_days="90"),
        _entry(review_after_days=True),
        _entry(reviewed_on="2026-12-31"),
        _entry(reviewed_on=None),
    ):
        assert _codes(_review_findings(bad, "docs/guide.md", TODAY)) == ["review-unknown"]


def test_source_findings_cover_shape_summary_url_and_date():
    assert _source_findings(_entry(), "docs/guide.md", TODAY) == []
    assert _codes(_source_findings(_entry(sources="x"), "docs/guide.md", TODAY)) == [
        "invalid-metadata"
    ]
    assert _codes(_source_findings(_entry(kind="summary"), "docs/guide.md", TODAY)) == [
        "source-missing"
    ]
    good = {"url": "https://example.com", "retrieved_on": "2026-09-01"}
    assert _source_findings(_entry(sources=[good]), "docs/guide.md", TODAY) == []
    bad = {"url": "http://example.com", "retrieved_on": "2027-01-01"}
    findings = _source_findings(_entry(sources=[good, bad]), "docs/guide.md", TODAY)
    assert _codes(findings) == ["source-invalid", "source-date-unknown"]
    assert findings[0]["severity"] == "error"


def test_document_file_findings_report_missing_and_refused_paths(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "guide.md").write_text("# Guide\n")
    assert _document_file_findings(tmp_path, "docs/guide.md") == []
    assert _codes(_document_file_findings(tmp_path, "docs/absent.md")) == ["missing-document"]
    (docs / "link.md").symlink_to(docs / "guide.md")
    assert _codes(_document_file_findings(tmp_path, "docs/link.md")) == ["invalid-path"]
    assert _codes(_document_file_findings(tmp_path, "../outside.md")) == ["invalid-path"]


def test_replacement_findings_require_a_different_catalogued_id():
    entries = [
        _entry(id="old", status="superseded", superseded_by="guide"),
        _entry(id="self", status="superseded", superseded_by="self"),
        _entry(id="gone", status="superseded", superseded_by="nowhere"),
        _entry(id="untyped", status="superseded", superseded_by=3),
        _entry(id="guide"),
    ]
    findings = _replacement_findings(entries, {"old", "self", "gone", "untyped", "guide"})
    assert _codes(findings) == ["replacement-missing"] * 3
    assert all(finding["severity"] == "error" for finding in findings)


def test_validate_entries_returns_findings_ids_and_paths_in_order(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "guide.md").write_text("# Guide\n")
    entries = [
        _entry(),
        _entry(id="stray", path="src/stray.md"),
        _entry(id="twin", path="docs/./guide.md"),
        _entry(id="lost", path="docs/lost.md", status="superseded", superseded_by="nowhere"),
    ]
    findings, ids, paths = _validate_entries(entries, tmp_path, TODAY)
    assert ids == {"guide", "stray", "twin", "lost"}
    assert paths == {"docs/guide.md", "docs/lost.md"}
    assert [(f["code"], f["path"]) for f in findings] == [
        ("invalid-path", "src/stray.md"),
        ("duplicate-path", "docs/./guide.md"),
        ("missing-document", "docs/lost.md"),
        ("replacement-missing", "docs/lost.md"),
    ]


def test_link_findings_classify_local_link_targets(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "other.md").write_text("# Other\n")
    body = (
        b"[ok](other.md) [remote](https://example.com/x) [anchor](#top) "
        b"[gone](nope.md) [escape](../../outside.md) [bad](http://[::1)\n"
    )
    findings = _link_findings(tmp_path, docs / "guide.md", "docs/guide.md", body)
    assert [f["message"] for f in findings] == [
        "Missing local link target: nope.md",
        "Local link escapes the project or traverses a symlink: ../../outside.md",
        "Malformed link target: http://[::1",
    ]
    assert {f["code"] for f in findings} == {"broken-link"}


def test_duplicate_content_findings_record_first_and_report_repeat():
    hashes: dict[str, str] = {}
    assert _duplicate_content_findings(hashes, b"   \n", "docs/blank.md") == []
    assert hashes == {}
    assert _duplicate_content_findings(hashes, b"# Same\n", "docs/a.md") == []
    repeat = _duplicate_content_findings(hashes, b"# Same\n", "docs/b.md")
    assert _codes(repeat) == ["duplicate-content"]
    assert "docs/a.md" in repeat[0]["message"]
    assert list(hashes.values()) == ["docs/a.md"]


def test_markdown_documents_walk_sorted_and_skip_hidden_or_symlinked(tmp_path):
    docs = tmp_path / "docs"
    (docs / "b").mkdir(parents=True)
    (docs / ".hidden").mkdir()
    (docs / "z.md").write_text("z")
    (docs / "a.md").write_text("a")
    (docs / "notes.txt").write_text("skip")
    (docs / "b" / "inner.md").write_text("inner")
    (docs / ".hidden" / "secret.md").write_text("hidden")
    (docs / "linked").symlink_to(docs / "b", target_is_directory=True)
    found = [p.relative_to(tmp_path).as_posix() for p in _markdown_documents(tmp_path, docs)]
    assert found == ["docs/a.md", "docs/z.md", "docs/b/inner.md"]


def test_scan_docs_reports_uncatalogued_and_symlinked_docs_directory(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.md").write_text("# Index\n")
    (docs / "guide.md").write_text("# Guide\n")
    (docs / "extra.md").write_text("# Extra\n")
    findings = _scan_docs(tmp_path, {"docs/guide.md"})
    assert [(f["code"], f["path"]) for f in findings] == [("uncatalogued", "docs/extra.md")]

    other = tmp_path / "other"
    other.mkdir()
    (other / "docs").symlink_to(Path("..") / "docs")
    symlinked = _scan_docs(other, set())
    assert [(f["code"], f["path"]) for f in symlinked] == [("invalid-path", "docs")]
