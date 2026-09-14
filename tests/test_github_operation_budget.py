"""A compound tracker operation must outlive one bounded network request."""

import json
import subprocess

import pytest

from ai_dlc.providers import Registry
from ai_dlc.providers.github_issues import GitHubIssuesProvider


@pytest.mark.parametrize(
    ("settings", "duration", "succeeds"),
    [({}, 35, True), ({"timeout": 30}, 35, False), ({}, 121, False)],
)
def test_compound_operation_budget_keeps_completion_bounded(
    monkeypatch, settings, duration, succeeds
):
    def elapsed_operation(command, **kwargs):
        if kwargs["timeout"] < duration:
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        return subprocess.CompletedProcess(
            command,
            0,
            json.dumps({"id": "87", "url": "https://github.com/a/b/issues/87", "state": "closed"}),
            "",
        )

    monkeypatch.setattr(subprocess, "run", elapsed_operation)
    provider = Registry(
        {"providers": {"issues": {"kind": "github-issues", "repository": "a/b", **settings}}}
    ).get("issues")
    payload = {"reference": "87", "operation_id": "retry"}
    if succeeds:
        assert provider.invoke("reconcile_closed", payload)["state"] == "closed"
    else:
        with pytest.raises(subprocess.TimeoutExpired):
            provider.invoke("reconcile_closed", payload)


@pytest.mark.parametrize("settings", [{}, {"timeout": 7}])
def test_operation_fallback_does_not_lengthen_individual_requests(monkeypatch, settings):
    provider = Registry(
        {"providers": {"issues": {"kind": "github-issues", "repository": "a/b", **settings}}}
    ).get("issues")
    child = GitHubIssuesProvider(json.loads(provider.command[-1]))

    def elapsed_request(command, **kwargs):
        if kwargs["timeout"] < 31:
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        return subprocess.CompletedProcess(command, 0, "{}", "")

    monkeypatch.setattr(subprocess, "run", elapsed_request)
    with pytest.raises(subprocess.TimeoutExpired):
        child.run(["api", "user"])


def test_other_bundled_provider_keeps_existing_default(monkeypatch):
    provider = Registry({"providers": {"jira": {"kind": "jira-cloud"}}}).get("jira")

    def elapsed_operation(command, **kwargs):
        if kwargs["timeout"] < 31:
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        return subprocess.CompletedProcess(
            command, 0, '{"id":"1","url":"https://example/1","state":"open"}', ""
        )

    monkeypatch.setattr(subprocess, "run", elapsed_operation)
    with pytest.raises(subprocess.TimeoutExpired):
        provider.invoke("read", {"reference": "1"})
