"""Safe file boundaries for effective-environment reports."""

import os
import stat
from contextlib import contextmanager
from pathlib import Path

import pytest
from test_environment_report import report

from ai_dlc.environment.report_io import ReportIOError, read_report, write_report
from ai_dlc.environment.report_schema import MAX_BYTES, report_bytes


@pytest.fixture
def canonical_tmp_path(tmp_path):
    """Avoid macOS /var -> /private/var aliases without weakening no-follow traversal."""
    return Path(os.path.realpath(tmp_path))


def test_report_file_roundtrip_is_canonical_private_and_exclusive(canonical_tmp_path):
    """Would fail if publication were noncanonical, broadly readable, or replace-capable."""
    target = canonical_tmp_path / "report.json"
    value = report()

    write_report(target, value)

    assert target.read_bytes() == report_bytes(value)
    assert read_report(target) == value
    if os.name != "nt":
        assert stat.S_IMODE(target.stat().st_mode) == 0o600

    original = target.read_bytes()
    with pytest.raises(ReportIOError, match="already exists"):
        write_report(target, report(observed_at="2026-09-26T13:00:00Z"))
    assert target.read_bytes() == original


def test_publication_refuses_existing_symlink_without_touching_target(canonical_tmp_path):
    """Would fail if an existing destination link could redirect or be replaced."""
    outside = canonical_tmp_path / "outside.json"
    outside.write_bytes(b"authored")
    destination = canonical_tmp_path / "report.json"
    try:
        destination.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    with pytest.raises(ReportIOError, match="already exists"):
        write_report(destination, report())

    assert destination.is_symlink()
    assert outside.read_bytes() == b"authored"


def test_invalid_report_is_validated_before_destination_access(canonical_tmp_path):
    """Would fail if publication created ancestors or staging bytes before validation."""
    destination = canonical_tmp_path / "absent" / "report.json"

    with pytest.raises(ValueError, match="Invalid effective environment report"):
        write_report(destination, {"schema_version": 1})

    assert not destination.parent.exists()


def test_read_is_bounded_and_errors_do_not_disclose_the_path(canonical_tmp_path):
    """Would fail if a selected report could exceed the schema byte budget or leak its name."""
    secret_name = "SECRET-private-report.json"
    target = canonical_tmp_path / secret_name
    target.write_bytes(b"{" + b" " * MAX_BYTES + b"}")

    with pytest.raises(ReportIOError) as raised:
        read_report(target)

    assert secret_name not in str(raised.value)


def test_malformed_input_uses_a_fixed_path_free_error(canonical_tmp_path):
    """Would fail if JSON/parser diagnostics or selected paths reached the user boundary."""
    secret_name = "SECRET-malformed.json"
    target = canonical_tmp_path / secret_name
    target.write_bytes(b'{"private":"SECRET-input"')

    with pytest.raises(ReportIOError) as raised:
        read_report(target)

    message = str(raised.value)
    assert secret_name not in message
    assert "SECRET-input" not in message


@pytest.mark.skipif(os.name == "nt", reason="POSIX no-follow descriptor traversal")
def test_read_refuses_symlink_ancestor_and_final_symlink(canonical_tmp_path):
    """Would fail if report import followed any selected path component."""
    outside = canonical_tmp_path / "outside"
    outside.mkdir()
    (outside / "report.json").write_bytes(report_bytes(report()))
    (outside / "link.json").symlink_to(outside / "report.json")
    linked_parent = canonical_tmp_path / "linked"
    linked_parent.symlink_to(outside, target_is_directory=True)

    with pytest.raises(ReportIOError):
        read_report(linked_parent / "report.json")
    with pytest.raises(ReportIOError):
        read_report(outside / "link.json")


@pytest.mark.skipif(os.name == "nt", reason="POSIX descriptor reads")
def test_read_collects_partial_regular_file_reads(canonical_tmp_path, monkeypatch):
    """Would fail if a short OS read were mistaken for a complete report."""
    from ai_dlc.environment import report_io

    target = canonical_tmp_path / "report.json"
    expected = report()
    target.write_bytes(report_bytes(expected))
    real_read = report_io.os.read

    def partial_read(descriptor, size):
        return real_read(descriptor, min(size, 7))

    monkeypatch.setattr(report_io.os, "read", partial_read)

    assert read_report(target) == expected


@pytest.mark.skipif(os.name == "nt", reason="POSIX FIFO boundary")
def test_read_refuses_fifo_without_blocking(canonical_tmp_path):
    """Would fail if a report path could block comparison by naming a FIFO."""
    fifo = canonical_tmp_path / "report.json"
    os.mkfifo(fifo)

    with pytest.raises(ReportIOError):
        read_report(fifo)


@pytest.mark.skipif(os.name == "nt", reason="POSIX descriptor-relative publication")
def test_publication_refuses_detected_parent_substitution(canonical_tmp_path, monkeypatch):
    """Would fail if a replaced parent path were accepted before the exclusive link."""
    from ai_dlc.environment import report_io

    parent = canonical_tmp_path / "reports"
    parent.mkdir()
    moved = canonical_tmp_path / "moved"
    outside = canonical_tmp_path / "outside"
    outside.mkdir()
    real_open = report_io._open_directory
    opens = 0

    @contextmanager
    def substitute_on_recheck(path):
        nonlocal opens
        opens += 1
        if opens == 2:
            parent.rename(moved)
            parent.symlink_to(outside, target_is_directory=True)
        with real_open(path) as descriptor:
            yield descriptor

    monkeypatch.setattr(report_io, "_open_directory", substitute_on_recheck)

    with pytest.raises(ReportIOError):
        write_report(parent / "report.json", report())

    assert not (outside / "report.json").exists()
    assert not (moved / "report.json").exists()
    assert not list(moved.glob(".ai-dlc-report-*"))


@pytest.mark.skipif(os.name == "nt", reason="POSIX descriptor-relative publication")
def test_publication_cleans_private_stage_after_link_failure(canonical_tmp_path, monkeypatch):
    """Would fail if failed publication left report bytes in a discoverable stage."""
    from ai_dlc.environment import report_io

    def fail_link(*args, **kwargs):
        raise OSError("SECRET raw failure")

    monkeypatch.setattr(report_io.os, "link", fail_link)
    target = canonical_tmp_path / "report.json"

    with pytest.raises(ReportIOError) as raised:
        write_report(target, report())

    assert "SECRET" not in str(raised.value)
    assert not target.exists()
    assert not list(canonical_tmp_path.glob(".ai-dlc-report-*"))
