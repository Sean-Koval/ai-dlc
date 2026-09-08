"""Corpus integrity and packet boundaries, not measured design quality."""

import json
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[1] / "agents/evaluations/design-pm"


def corpus():
    path = ASSETS / "cases.json"
    assert path.is_file(), "Design calibration corpus has not been prepared"
    return json.loads(path.read_text())


def test_case_references_and_pending_evidence_are_not_invented_results():
    data = corpus()
    ids = [case["id"] for case in data["cases"]]
    assert len(ids) == len(set(ids))
    calibration = set(data["calibration_case_ids"])
    held_out = set(data["held_out_case_ids"])
    assert calibration and held_out and not calibration & held_out
    assert calibration | held_out == set(ids)
    for case in data["cases"]:
        assert case["held_out"] == (case["id"] in held_out)
        requirement_ids = [row["id"] for row in case["requirements"]]
        assert len(requirement_ids) == len(set(requirement_ids))
        assert requirement_ids
        criterion_ids = [row["id"] for row in case["evaluation_proposal"]["criteria"]]
        assert len(criterion_ids) == len(set(criterion_ids))
        for row in case["evaluation_proposal"]["criteria"]:
            assert row["requirement_ids"]
            assert set(row["requirement_ids"]) <= set(requirement_ids)
        assert case["evaluation_proposal"]["authored_by"] == "model"
        assert case["evaluation_proposal"]["status"] == "proposal_not_ground_truth"
        assert case["human_labels"] is None
        assert case["human_label_status"] == "pending"
        assert case["stimulus_plan"]["status"] == "specified_not_built"
        assert case["stimulus_plan"]["candidate_manifest"] is None
        assert case["stimulus_plan"]["actual_observations"] is None


def test_calibration_packet_excludes_holdout_and_evaluator_material():
    data = corpus()
    fields = data["participant_fields"]
    assert set(fields) == {"id", "task", "requirements", "fixtures", "access_constraints"}
    packet = [
        {key: case[key] for key in fields} for case in data["cases"] if case["held_out"] is False
    ]
    assert {row["id"] for row in packet} == {"DC01", "DC02", "DC03", "DC04"}
    serialized = json.dumps(packet)
    for case in data["cases"]:
        if case["held_out"]:
            assert case["task"] not in serialized
        assert case["evaluation_proposal"]["decision_rationale"] not in serialized
        assert case["stimulus_plan"]["construction_recipe"] not in serialized
    assert all("human_labels" not in row and "evaluation_proposal" not in row for row in packet)
