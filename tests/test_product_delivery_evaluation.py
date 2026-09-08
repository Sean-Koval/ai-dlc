"""Preparation invariants; these checks do not score model quality or enforce a harness."""

import json
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[1] / "agents/evaluations/product-delivery"


def corpus():
    return json.loads((ASSETS / "cases.json").read_text())


def test_case_identity_partition_and_pending_human_boundary():
    data = corpus()
    assert data["schema"] == 1
    assert data["status"] == "prepared_pending_human_review"
    cases = data["cases"]
    ids = [case["id"] for case in cases]
    assert len(ids) == len(set(ids)) == 6
    assert sum(case["held_out"] is True for case in cases) == 2
    assert sum(case["held_out"] is False for case in cases) == 4
    assert set(data["held_out_case_ids"]) == {
        case["id"] for case in cases if case["held_out"] is True
    }
    assert not (set(data["held_out_case_ids"]) & set(data["calibration_case_ids"]))
    for held_out in [False, True]:
        assert {case["mode"] for case in cases if case["held_out"] is held_out} == {
            "greenfield",
            "brownfield",
        }
    for case in cases:
        assert case["human_labels"] is None
        assert case["human_label_status"] == "pending"
        assert case["expected_decisions"]["authored_by"] == "model"
        assert case["expected_decisions"]["status"] == "proposal_not_ground_truth"
        assert case["material_unknowns"] and case["disallowed_assumptions"]
        assert case["requirement_ids"]
        assert set(case["requirement_ids"]) <= {
            "PS-01",
            "PS-02",
            "PS-03",
            "TR-01",
            "TR-02",
            "TR-03",
        }
        evidence_ids = [row["id"] for row in case["evidence"]]
        assert len(evidence_ids) == len(set(evidence_ids))
        assert all(row["synthetic"] is True for row in case["evidence"])
    assert {case["expected_decisions"]["route"] for case in cases} >= {
        "investigate",
        "stop",
        "no_spec",
        "proceed_with_spec",
    }


def test_documented_calibration_projection_excludes_holdout_and_scoring_keys():
    data = corpus()
    assert data["participant_fields"] == ["id", "mode", "prompt", "evidence"]
    calibration = [
        {key: case[key] for key in data["participant_fields"]}
        for case in data["cases"]
        if case["held_out"] is False
    ]
    assert len(calibration) == 4
    assert {row["id"] for row in calibration} == set(data["calibration_case_ids"])
    exposed = json.dumps(calibration)
    for case in data["cases"]:
        if case["held_out"]:
            assert case["id"] not in {row["id"] for row in calibration}
            assert case["prompt"] not in exposed
    for row in calibration:
        assert not (
            {
                "expected_decisions",
                "human_labels",
                "material_unknowns",
                "requirement_ids",
                "disallowed_assumptions",
            }
            & row.keys()
        )
