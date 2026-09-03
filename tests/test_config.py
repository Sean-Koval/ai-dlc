from pathlib import Path

import pytest


def test_retained_named_entry_keeps_original_provenance():
    from ai_dlc.config import resolve_layers

    result = resolve_layers(
        [
            (
                "base",
                {
                    "schema": 4,
                    "agents": {"servers": [{"id": "a"}, {"id": "b", "command": "original"}]},
                },
            ),
            (
                "project",
                {"schema": 4, "agents": {"servers": {"remove": ["a"], "add": [{"id": "c"}]}}},
            ),
        ]
    )
    assert result.sources["agents.servers.0.command"] == "base"


def test_machine_cannot_weaken_project_checks():
    from ai_dlc.config import resolve_layers

    with pytest.raises(ValueError, match="machine.*checks"):
        resolve_layers(
            [
                ("project", {"schema": 4, "checks": {"required": ["test"]}}),
                ("machine", {"schema": 4, "checks": {"required": []}}),
            ]
        )


def test_named_collections_and_provenance():
    from ai_dlc.config import resolve_layers

    result = resolve_layers(
        [
            ("base", {"schema": 4, "agents": {"servers": [{"id": "context", "args": ["a", "b"]}]}}),
            (
                "project",
                {
                    "schema": 4,
                    "agents": {
                        "servers": {
                            "add": [{"id": "work", "args": ["serve"]}],
                            "remove": ["context"],
                        }
                    },
                },
            ),
        ]
    )
    assert result.values["agents"]["servers"] == [{"id": "work", "args": ["serve"]}]
    assert result.sources["agents.servers.0.args.0"] == "project"


def test_conflicting_collection_edit_and_unknown_version_rejected():
    from ai_dlc.config import resolve_layers

    with pytest.raises(ValueError, match="same ID"):
        resolve_layers(
            [
                (
                    "project",
                    {"schema": 4, "agents": {"servers": {"add": [{"id": "a"}], "remove": ["a"]}}},
                )
            ]
        )
    with pytest.raises(ValueError, match="schema"):
        resolve_layers([("project", {"schema": 99})])


def test_project_output_excludes_personal_settings(tmp_path: Path):
    from ai_dlc.config import load_project

    (tmp_path / "ai-dlc.toml").write_text('schema = 4\n[roles]\ntracker = "linear"\n')
    assert load_project(tmp_path)["roles"]["tracker"] == "linear"


def test_misplaced_secret_or_unknown_field_rejected():
    from ai_dlc.config import resolve_layers

    with pytest.raises(ValueError, match="unknown"):
        resolve_layers([("project", {"schema": 4, "typo": True})])
    with pytest.raises(ValueError, match="credential"):
        resolve_layers([("project", {"schema": 4, "providers": {"linear": {"token": "secret"}}})])
