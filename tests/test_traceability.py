from copy import deepcopy

import pytest


def test_dependency_graph_reports_cycles_missing_ids_and_stable_errors():
    from ai_dlc.traceability import validate_work_graph

    records = {
        "b": {"id": "b", "depends_on": ["a", "missing"]},
        "a": {"id": "a", "depends_on": ["b"]},
    }
    before = deepcopy(records)
    errors = validate_work_graph(records)
    assert any("cycle" in error.lower() and "a" in error and "b" in error for error in errors)
    assert any("missing" in error.lower() and "b" in error for error in errors)
    assert errors == validate_work_graph(dict(reversed(list(records.items()))))
    assert records == before


@pytest.mark.parametrize(
    "records,expected",
    [
        ({"one": {"id": "one", "depends_on": ["one"]}}, "self"),
        ({"one": {"id": "other"}}, "match"),
        ({"one": {"depends_on": []}}, "id"),
        ({"../escape": {"id": "../escape"}}, "Unsafe"),
        ({"one": {"id": "one", "depends_on": ["../escape"]}}, "Unsafe"),
        ({"one": {"id": "one", "depends_on": "two"}}, "list"),
        ({"one": {"id": "one", "depends_on": [None]}}, "Unsafe"),
    ],
)
def test_dependency_graph_refuses_invalid_records(records, expected):
    from ai_dlc.traceability import validate_work_graph

    assert any(expected in error for error in validate_work_graph(records))


def test_dependency_graph_accepts_shared_dependencies_legacy_defaults_and_deep_chains():
    from ai_dlc.traceability import validate_work_graph

    records = {"base": {"id": "base"}}
    for index in range(1500):
        key = f"item-{index}"
        records[key] = {"id": key, "depends_on": ["base", f"item-{index - 1}"] if index else []}
    assert validate_work_graph(records) == []


def test_ticket_body_renders_traceability_without_inventing_scope_or_changing_inputs():
    from ai_dlc.traceability import render_ticket_body

    work = {
        "id": "localized-export",
        "scope": "Add an opt-in localized export; default bytes stay unchanged.",
        "requirements": ["export-brief#RQ-001", "export-brief#RQ-002"],
        "depends_on": ["contract-baseline"],
        "requires_spec": True,
        "spec_reason": "Changes the explicit export mode.",
        "artifacts": {"spec": "openspec/changes/localized-export", "brief": "docs/brief.md"},
        "acceptance": ["Default bytes match the baseline.", "Explicit localization is verified."],
    }
    before = deepcopy(work)
    body = render_ticket_body(work)
    for value in [
        work["scope"],
        work["spec_reason"],
        *work["requirements"],
        *work["depends_on"],
        *work["artifacts"].values(),
        *work["acceptance"],
    ]:
        assert value in body
    for section in ["Scope", "Requirements", "Dependencies", "References", "Acceptance"]:
        assert f"## {section}" in body
    assert "<!-- ai-dlc:" not in body  # Correlation stays owned by WorkService and the provider.
    assert work == before
    work["artifacts"] = dict(reversed(list(work["artifacts"].items())))
    assert render_ticket_body(work) == body


def test_legacy_ticket_body_has_no_invented_dependencies_or_requirements():
    from ai_dlc.traceability import render_ticket_body

    body = render_ticket_body(
        {
            "scope": "Verify the existing behavior",
            "acceptance": ["Checks pass"],
            "requires_spec": False,
            "spec_reason": "Verification only",
        }
    )
    assert "Verification only" in body
    assert "RQ-001" not in body
    assert "## Scope" in body
