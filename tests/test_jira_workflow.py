"""Real WorkService, registry, journal and HTTP transport; SCM evidence is a fixture."""

import subprocess

import pytest
import tomli_w
from test_jira_provider import Jira


@pytest.fixture
def lifecycle(tmp_path):
    from ai_dlc.providers import Registry
    from ai_dlc.workflow import WorkService

    jira = Jira()
    config = {
        "schema": 4,
        "roles": {"tracker": "work", "scm": "fixture-scm"},
        "providers": {"work": jira.config},
        "scm": {"repository": "fixture/repo"},
    }
    (tmp_path / "ai-dlc.toml").write_text(tomli_w.dumps(config))
    directory = tmp_path / ".ai-dlc/work"
    directory.mkdir(parents=True)
    (directory / "one.toml").write_text(
        tomli_w.dumps(
            {
                "schema": 1,
                "id": "one",
                "title": "New work",
                "scope": "New Jira work",
                "requires_spec": False,
                "spec_reason": "Fixture only",
                "acceptance": ["Reviewed acceptance"],
                "reviewed": True,
                "providers": {"tracker": "work", "scm": "fixture-scm"},
            }
        )
    )
    subprocess.run(
        ["git", "init", "-b", "work/one", str(tmp_path)], check=True, capture_output=True
    )

    class SCM:
        allowed = False

        def merged(self, reference):
            if not self.allowed:
                raise ValueError("Fixture PR is unmerged")
            return {"sha": "fixture-merge", "pr": {"merged": True}}

        def ci(self, sha):
            return {"sha": sha, "run_id": 1, "receipt": {"fixture_only": True}}

    scm = SCM()
    registry = Registry(config, root=tmp_path)
    registry.register("work", jira.provider(), operations=["capabilities"])
    registry.register("fixture-scm", scm)
    service = WorkService(
        tmp_path, config, state_path=tmp_path / ".ai-dlc/local/state", registry=registry
    )
    return service, jira, scm


def test_shared_jira_publish_start_pr_link_and_fresh_gated_finish(lifecycle):
    service, jira, scm = lifecycle
    assert service.publish("one")["tracker"]["state"] == "open"
    assert service.start("one")["tracker"]["state"] == "in_progress"
    url = "https://github.com/fixture/repo/pull/1"
    service.link("one", "pr", url)
    service.link("one", "pr", url)
    assert len(jira.writes("/remotelink")) == 1
    before = len(jira.requests)
    assert service.finish("one")["status"] == "blocked"
    assert len(jira.requests) == before
    scm.allowed = True
    assert service.finish("one")["tracker"]["state"] == "closed"
    assert service.finish("one")["status"] == "completed"
    assert len(jira.writes("/transitions")) == 2


def test_shared_uncertain_create_never_retries_while_search_is_delayed(lifecycle):
    service, jira, _ = lifecycle
    jira.lost_create = True
    jira.hidden = True
    with pytest.raises(RuntimeError, match="uncertain") as caught:
        service.publish("one")
    assert "credential-sentinel" not in str(caught.value)
    with pytest.raises(RuntimeError, match="refusing duplicate retry"):
        service.publish("one")
    assert len(jira.writes("/issue")) == 1
    jira.hidden = False
    assert service.publish("one")["tracker"]["id"] == "101"
    assert len(jira.writes("/issue")) == 1


def test_generic_registry_cannot_bypass_finish_with_native_terminal_id(lifecycle):
    service, jira, _ = lifecycle
    for state in ["closed", "cancelled", "3", "4"]:
        with pytest.raises(ValueError, match="finish"):
            service.registry.invoke(
                "work", "transition", {"reference": "101", "state": state, "operation_id": "bypass"}
            )
    assert jira.writes() == []


def test_cancelled_result_never_completes_or_repeats_transition(lifecycle):
    service, jira, scm = lifecycle
    service.publish("one")
    scm.allowed = True
    jira.transition_resolution = "2000"
    with pytest.raises(RuntimeError, match="requested state"):
        service.finish("one")
    assert service.status("one")["tracker"]["state"] == "cancelled"
    with pytest.raises(ValueError, match="terminal"):
        service.finish("one")
    assert len(jira.writes("/transitions")) == 1
