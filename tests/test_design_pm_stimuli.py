"""Constructed-stimulus integrity; no claims about experimental model quality."""

import hashlib
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "agents/evaluations/design-pm"


def test_manifest_binds_original_artifacts_without_exposing_static_source():
    manifest_path = ROOT / "stimuli/manifest.json"
    assert manifest_path.is_file(), "Constructed design stimuli are not available"
    manifest = json.loads(manifest_path.read_text())
    corpus = json.loads((ROOT / "cases.json").read_text())
    assert {case["case_id"] for case in manifest["cases"]} == {
        case["id"] for case in corpus["cases"]
    }
    for case in manifest["cases"]:
        assert case["classification"] == "constructed_input_not_experiment_output"
        assert case["human_labels"] is None
        artifacts = case["artifacts"]
        assert len({row["path"] for row in artifacts}) == len(artifacts)
        for row in artifacts:
            path = ROOT / row["path"]
            assert path.resolve().is_relative_to(ROOT.resolve())
            assert path.is_file() and not path.is_symlink()
            content = path.read_bytes()
            assert hashlib.sha256(content).hexdigest() == row["sha256"]
        exposed = [row for row in artifacts if row["participant_access"]]
        assert exposed
        if case["case_id"] == "DC04":
            assert len(exposed) == 3
            for row in exposed:
                assert row["media_type"] == "image/png"
                content = (ROOT / row["path"]).read_bytes()
                assert content[:8] == b"\x89PNG\r\n\x1a\n"
                assert struct.unpack(">II", content[16:24]) == (390, 844)
        else:
            assert any(row["media_type"] == "text/html" for row in exposed)
        assert not any(row["role"] in {"construction_source", "verification"} for row in exposed)
