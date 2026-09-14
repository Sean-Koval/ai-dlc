"""Pure GitHub Project setup phases: identity derivation and drift checks."""

import json

import pytest

from ai_dlc.config import digest
from ai_dlc.setup.github_project_setup import (
    _check_connection_identity,
    _check_remote_identity,
    _recorded_project,
    _setup_identity,
)

SAVED = {
    "host": "GitHub.com",
    "repository_id": "REPO_1",
    "owner": {"id": "OWNER_1", "login": "org"},
    "viewer": {"id": "USER_1", "login": "me"},
    "title": "Default",
}


def test_setup_identity_lowercases_host_and_derives_operation():
    identity, operation = _setup_identity(SAVED)
    assert identity == {
        "host": "github.com",
        "repository_id": "REPO_1",
        "owner_id": "OWNER_1",
        "title": "Default",
    }
    assert operation == "github-project-create:" + digest(identity)


def test_check_remote_identity_accepts_unchanged_remote():
    current = {"viewer": SAVED["viewer"], "repository": {"id": "REPO_1"}}
    _check_remote_identity(current, SAVED["owner"], SAVED)


@pytest.mark.parametrize(
    ("current", "owner"),
    [
        (
            {"viewer": {"id": "USER_2", "login": "me"}, "repository": {"id": "REPO_1"}},
            SAVED["owner"],
        ),
        ({"viewer": SAVED["viewer"], "repository": {"id": "REPO_2"}}, SAVED["owner"]),
        ({"viewer": SAVED["viewer"], "repository": {"id": "REPO_1"}}, None),
    ],
)
def test_check_remote_identity_rejects_drift(current, owner):
    with pytest.raises(ValueError, match="remote identity changed"):
        _check_remote_identity(current, owner, SAVED)


def test_recorded_project_reuses_successful_result():
    selected = {"id": "P1", "url": "https://github.com/orgs/org/projects/1", "title": "Default"}
    assert _recorded_project(("succeeded", json.dumps(selected))) == selected


@pytest.mark.parametrize("record", [("uncertain", None), ("succeeded", ""), ("begun", "{}")])
def test_recorded_project_refuses_uncertain_records(record):
    with pytest.raises(RuntimeError, match="Refusing duplicate create"):
        _recorded_project(record)


def _connection(project_id="P1", viewer=None, repository_id="REPO_1"):
    return {
        "plan": {
            "patch": {"project": {"id": project_id}},
            "discovery": {
                "viewer": SAVED["viewer"] if viewer is None else viewer,
                "repository": {"id": repository_id},
            },
        }
    }


def test_check_connection_identity_accepts_matching_connection():
    _check_connection_identity(_connection(), SAVED, {"id": "P1"})


@pytest.mark.parametrize(
    "connection",
    [
        _connection(project_id="P2"),
        _connection(viewer={"id": "USER_2", "login": "me"}),
        _connection(repository_id="REPO_2"),
    ],
)
def test_check_connection_identity_rejects_drift(connection):
    with pytest.raises(ValueError, match="setup identity changed"):
        _check_connection_identity(connection, SAVED, {"id": "P1"})
