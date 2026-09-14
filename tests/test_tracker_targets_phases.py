"""Pure reconciliation phases: verification, evidence binding and report shaping."""

import pytest

from ai_dlc.config import digest
from ai_dlc.setup.tracker_targets import (
    _bind_creation_evidence,
    _creation_evidence,
    _reconciliation_result,
    _verify_migration_targets,
)


def _plan():
    return {
        "operation_id": "a" * 32,
        "digest": "intent-digest",
        "creates": {
            "w1": {"payload": {"operation_id": "op-1", "correlation": "<!-- ai-dlc:op-1 -->"}},
            "w2": {"payload": {"operation_id": "op-2", "correlation": "<!-- ai-dlc:op-2 -->"}},
        },
    }


def test_verify_migration_targets_accepts_matching_identities():
    results = {"w1": {"id": "1", "url": "u1", "state": "open"}}
    migration_plan = {"mappings": {"w1": {"target": {"id": "1", "url": "u1", "state": "x"}}}}
    _verify_migration_targets(migration_plan, results)


@pytest.mark.parametrize("target", [{"id": "2", "url": "u1"}, {"id": "1", "url": "other"}])
def test_verify_migration_targets_rejects_changed_identity(target):
    results = {"w1": {"id": "1", "url": "u1", "state": "open"}}
    with pytest.raises(ValueError, match="changed during final verification"):
        _verify_migration_targets({"mappings": {"w1": {"target": target}}}, results)


def test_creation_evidence_records_every_create_intent():
    assert _creation_evidence(_plan()) == {
        "operation_id": "a" * 32,
        "intent_digest": "intent-digest",
        "targets": {
            "w1": {"operation_id": "op-1", "correlation": "<!-- ai-dlc:op-1 -->"},
            "w2": {"operation_id": "op-2", "correlation": "<!-- ai-dlc:op-2 -->"},
        },
    }


def test_bind_creation_evidence_recomputes_digest_last():
    migration_plan = {"digest": "stale", "mappings": {}, "evidence": {"source": "local"}}
    bound = _bind_creation_evidence(migration_plan, _plan())
    assert bound is migration_plan
    assert list(bound) == ["mappings", "evidence", "digest"]
    assert bound["evidence"]["creation"] == _creation_evidence(_plan())
    assert bound["digest"] == digest({"mappings": {}, "evidence": bound["evidence"]})


def test_reconciliation_result_next_action_depends_on_migration_plan():
    plan = _plan()
    results = {"w1": {"id": "1", "url": "u1", "state": "open"}}
    with_plan = _reconciliation_result(plan, "resolved", results, results, {}, {"digest": "d"})
    assert list(with_plan) == [
        "status",
        "operation_id",
        "targets",
        "retained_targets",
        "unresolved",
        "migration_plan",
        "next_action",
    ]
    assert with_plan["operation_id"] == "a" * 32
    assert with_plan["next_action"].startswith("Review/save the local migration plan")
    without = _reconciliation_result(plan, "unresolved", {}, results, {"w1": "boom"}, None)
    assert without["status"] == "unresolved"
    assert without["retained_targets"] == results
    assert without["unresolved"] == {"w1": "boom"}
    assert without["next_action"].startswith("Retain the saved intent")
