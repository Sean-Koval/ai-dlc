"""GitHub wire fixtures exercise actual adapter and journaled service behavior."""

import copy
import json
from types import SimpleNamespace

import pytest

from ai_dlc.providers import Registry
from ai_dlc.providers.github_issues import GitHubIssuesProvider
from ai_dlc.work.workflow import WorkService

CONFIG = {
    "repository": "org/repo",
    "viewer_id": "USER_1",
    "project": {
        "id": "PROJECT_1",
        "status_field_id": "FIELD_1",
        "statuses": {"open": "TODO", "in_progress": "DOING", "closed": "DONE"},
    },
}


class GitHubWire:
    """Stateful remote fixture; subprocess boundary only is replaced."""

    def __init__(self):
        self.issue = {
            "id": "ISSUE_1",
            "number": 1,
            "url": "https://github.com/org/repo/issues/1",
            "state": "OPEN",
            "stateReason": None,
            "body": "",
        }
        self.exists = True
        self.member = False
        self.status = None
        self.viewer = "USER_1"
        self.fields = [
            {
                "__typename": "ProjectV2SingleSelectField",
                "id": "FIELD_1",
                "options": [{"id": x, "name": x} for x in ["TODO", "DOING", "DONE"]],
            }
        ]
        self.other_items = []
        self.events = []
        self.commands = []
        self.lose = set()
        self.fail = set()
        self.paginate = False

    def mutate(self, event):
        self.events.append(event)
        if event in self.lose:
            self.lose.remove(event)
            raise TimeoutError("response lost")

    @staticmethod
    def connection(rows, after=None, paginate=False):
        if paginate and not after:
            return {"nodes": [], "pageInfo": {"hasNextPage": True, "endCursor": "next"}}
        return {"nodes": rows, "pageInfo": {"hasNextPage": False, "endCursor": None}}

    def run(self, args, **kwargs):
        self.commands.append((args, kwargs))
        if args[1:3] == ["api", "graphql"]:
            assert "--repo" not in args
            request = json.loads(kwargs["input"])
            query, variables = request["query"], request["variables"]
            if "query Viewer" in query:
                data = {"viewer": {"id": self.viewer}}
            elif "query ProjectFields" in query:
                data = {
                    "node": {
                        "id": "PROJECT_1",
                        "__typename": "ProjectV2",
                        "fields": self.connection(
                            self.fields, variables.get("after"), self.paginate
                        ),
                    }
                }
            elif "query ProjectItems" in query:
                rows = copy.deepcopy(self.other_items)
                if self.member:
                    rows.append(
                        {
                            "id": "ITEM_1",
                            "content": {
                                "__typename": "Issue",
                                "id": "ISSUE_1",
                                "url": self.issue["url"],
                            },
                        }
                    )
                data = {
                    "node": {
                        "id": "PROJECT_1",
                        "__typename": "ProjectV2",
                        "items": self.connection(rows, variables.get("after"), self.paginate),
                    }
                }
            elif "query ItemFields" in query:
                rows = (
                    []
                    if self.status is None
                    else [
                        {
                            "__typename": "ProjectV2ItemFieldSingleSelectValue",
                            "optionId": self.status,
                            "field": {"id": "FIELD_1"},
                        }
                    ]
                )
                data = {
                    "node": {
                        "id": "ITEM_1",
                        "project": {"id": "PROJECT_1"},
                        "fieldValues": self.connection(rows, variables.get("after"), self.paginate),
                    }
                }
            elif "addProjectV2ItemById" in query:
                assert variables["project"] == "PROJECT_1" and variables["content"] == "ISSUE_1"
                if "attach" in self.fail:
                    raise RuntimeError("attachment unavailable")
                self.member = True
                self.mutate("attach")
                data = {"addProjectV2ItemById": {"item": {"id": "ITEM_1"}}}
            elif "updateProjectV2ItemFieldValue" in query:
                assert (
                    variables["project"] == "PROJECT_1"
                    and variables["item"] == "ITEM_1"
                    and variables["field"] == "FIELD_1"
                )
                if "status" in self.fail:
                    raise RuntimeError("status unavailable")
                self.status = variables["option"]
                self.mutate("status:" + self.status)
                data = {"updateProjectV2ItemFieldValue": {"projectV2Item": {"id": "ITEM_1"}}}
            else:
                raise AssertionError(query)
            return SimpleNamespace(returncode=0, stdout=json.dumps({"data": data}), stderr="")
        assert args[1] == "issue"
        action = args[2]
        if action == "view":
            result = self.issue
        elif action == "list":
            result = [self.issue] if self.exists else []
        elif action == "create":
            self.exists = True
            self.issue["body"] = args[args.index("--body") + 1]
            self.mutate("create")
            return SimpleNamespace(returncode=0, stdout=self.issue["url"], stderr="")
        elif action == "close":
            self.issue.update(state="CLOSED", stateReason="COMPLETED")
            self.mutate("close")
            result = None
        elif action == "reopen":
            self.issue.update(state="OPEN", stateReason="REOPENED")
            self.mutate("reopen")
            result = None
        else:
            raise AssertionError(args)
        return SimpleNamespace(returncode=0, stdout=json.dumps(result), stderr="")


@pytest.fixture
def wire(monkeypatch):
    result = GitHubWire()
    monkeypatch.setattr("ai_dlc.providers.github_issues.subprocess.run", result.run)
    return result


def provider():
    return GitHubIssuesProvider(copy.deepcopy(CONFIG))


def transition(adapter, state):
    return adapter.invoke("transition", {"reference": "1", "state": state, "operation_id": "op"})


def test_project_start_exposes_planning_without_closing_issue(wire):
    wire.member = True
    wire.paginate = True
    adapter = provider()
    assert adapter.invoke("capabilities", {})["lifecycle"]["in_progress"] is True
    item = transition(adapter, "in_progress")
    assert item["state"] == "in_progress"
    assert item["issue_state"] == "open"
    assert item["project"]["status_option_id"] == "DOING"
    assert wire.events == ["status:DOING"]


@pytest.mark.parametrize(
    "reason,want", [("COMPLETED", "closed"), ("NOT_PLANNED", "cancelled"), (None, "unknown")]
)
def test_terminal_issue_reason_authoritative_and_start_refuses(wire, reason, want):
    wire.member = True
    wire.status = "DOING"
    wire.issue.update(state="CLOSED", stateReason=reason)
    adapter = provider()
    assert adapter.invoke("read", {"reference": "1"})["state"] == want
    with pytest.raises(ValueError, match="terminal"):
        transition(adapter, "in_progress")
    assert wire.events == []


def test_board_done_alone_does_not_establish_completion(wire):
    wire.member = True
    wire.status = "DONE"
    assert provider().invoke("read", {"reference": "1"})["state"] == "open"


def test_close_sets_verified_board_done_before_native_close(wire):
    wire.member = True
    assert transition(provider(), "closed")["state"] == "closed"
    assert wire.events == ["status:DONE", "close"]


@pytest.mark.parametrize("reason", ["NOT_PLANNED", None])
def test_cancelled_issue_cannot_be_completed(wire, reason):
    wire.issue.update(state="CLOSED", stateReason=reason)
    with pytest.raises(ValueError, match="cancel"):
        transition(provider(), "closed")
    assert wire.events == []


@pytest.mark.parametrize(
    "fault",
    [
        "field",
        "option",
        "duplicate_mapping",
        "incomplete",
        "project",
        "hidden_item",
        "duplicate_item",
        "origin",
        "viewer",
    ],
)
def test_invalid_selected_identity_or_mapping_refuses_write(wire, fault):
    cfg = copy.deepcopy(CONFIG)
    if fault == "field":
        cfg["project"]["status_field_id"] = "wrong"
    elif fault == "option":
        cfg["project"]["statuses"]["closed"] = "wrong"
    elif fault == "duplicate_mapping":
        cfg["project"]["statuses"]["closed"] = "TODO"
    elif fault == "incomplete":
        del cfg["project"]["statuses"]["open"]
    elif fault == "project":
        cfg["project"]["id"] = "wrong"
    elif fault == "hidden_item":
        wire.other_items = [{"id": "HIDDEN", "content": None}]
    elif fault == "duplicate_item":
        wire.member = True
        wire.other_items = [
            {
                "id": "OTHER",
                "content": {"__typename": "Issue", "id": "ISSUE_1", "url": wire.issue["url"]},
            }
        ]
    elif fault == "origin":
        wire.issue["url"] = "https://github.com/other/repo/issues/1"
    else:
        wire.viewer = "wrong"
    with pytest.raises((ValueError, RuntimeError)):
        transition(GitHubIssuesProvider(cfg), "closed")
    assert wire.events == []


def test_prepare_recovers_attachment_without_resetting_existing_status(wire):
    adapter = provider()
    wire.lose.add("attach")
    payload = {"reference": "1", "operation_id": "prepare"}
    with pytest.raises(TimeoutError):
        adapter.invoke("prepare", payload)
    wire.status = "DOING"
    assert adapter.invoke("prepare", payload)["project"]["item_id"] == "ITEM_1"
    assert wire.events == ["attach"]


def test_host_is_pinned_for_issue_and_graphql_transport(wire, monkeypatch):
    monkeypatch.setenv("GH_HOST", "unrelated.example")
    transition(provider(), "closed")
    for args, kwargs in wire.commands:
        assert kwargs["env"]["GH_HOST"] == "github.com"
        if args[1] == "api":
            assert args[args.index("--hostname") + 1] == "github.com"
        else:
            assert args[args.index("--repo") + 1] == "github.com/org/repo"


def service(tmp_path, wire, *, blocked=False):
    folder = tmp_path / ".ai-dlc/work"
    folder.mkdir(parents=True)
    (folder / "one.toml").write_text(
        'schema=1\nid="one"\ntitle="One"\nscope="small"\nrequires_spec=false\nspec_reason="fixture"\nacceptance=["done"]\nreviewed=true\n[providers]\ntracker="tickets"\nscm="scm"\n'
    )
    registry = Registry()
    registry.register("tickets", provider(), operations=("capabilities",))

    class SCM:
        def merged(self, reference):
            if blocked:
                raise ValueError("unmerged")
            return {"sha": "merge", "pr": {}}

        def ci(self, sha):
            return {"sha": sha, "run_id": 1, "receipt": {}}

    registry.register("scm", SCM())
    return WorkService(tmp_path, {}, state_path=tmp_path / "state", registry=registry)


def test_publish_saves_issue_before_failed_attach_and_reuses_on_retry(tmp_path, wire):
    wire.exists = False
    wire.fail.add("attach")
    app = service(tmp_path, wire)
    with pytest.raises(RuntimeError, match="attachment"):
        app.publish("one")
    assert app.load("one")["artifacts"]["tracker"] == "1"
    wire.fail.clear()
    result = app.publish("one")
    assert result["tracker"]["project"]["item_id"] == "ITEM_1"
    assert wire.events.count("create") == 1
    assert wire.events.count("attach") == 1


@pytest.mark.parametrize("lost", ["status:DONE", "close"])
def test_finish_reconciles_partial_close_without_duplicate_issue_writes(tmp_path, wire, lost):
    app = service(tmp_path, wire)
    app.publish("one")
    wire.events.clear()
    wire.lose.add(lost)
    with pytest.raises(TimeoutError):
        app.finish("one")
    result = app.finish("one")
    assert result["status"] == "completed"
    assert wire.events == ["status:DONE", "close"]


def test_finish_reconciles_already_completed_issue_even_after_journal_success(tmp_path, wire):
    app = service(tmp_path, wire)
    app.publish("one")
    app.finish("one")
    wire.status = "TODO"
    wire.events.clear()
    result = app.finish("one")
    assert result["tracker"]["project"]["status_option_id"] == "DONE"
    assert wire.events == ["status:DONE"]


def test_finish_gates_precede_terminal_board_reconciliation(tmp_path, wire):
    app = service(tmp_path, wire, blocked=True)
    app.publish("one")
    wire.issue.update(state="CLOSED", stateReason="COMPLETED")
    wire.events.clear()
    assert app.finish("one")["status"] == "blocked"
    assert wire.events == []


def test_public_terminal_reconciliation_cannot_bypass_finish(wire):
    registry = Registry()
    registry.register("tickets", provider(), operations=("capabilities",))
    with pytest.raises(ValueError, match="work.finish"):
        registry.invoke("tickets", "reconcile_closed", {"reference": "1", "operation_id": "op"})
    assert wire.events == []


def test_publish_rechecks_membership_after_previous_success(tmp_path, wire):
    app = service(tmp_path, wire)
    app.publish("one")
    wire.member = False
    wire.events.clear()
    assert app.publish("one")["tracker"]["project"]["item_id"] == "ITEM_1"
    assert wire.events.count("attach") == 1


def test_prepare_does_not_overwrite_concurrently_attached_planning(wire, monkeypatch):
    original = wire.run

    def concurrent(args, **kwargs):
        result = original(args, **kwargs)
        if args[1] == "api" and "mutation AttachIssue" in kwargs["input"]:
            wire.status = "DOING"
        return result

    monkeypatch.setattr("ai_dlc.providers.github_issues.subprocess.run", concurrent)
    item = provider().invoke("prepare", {"reference": "1", "operation_id": "op"})
    assert item["project"]["status_option_id"] == "DOING"
    assert wire.events == ["attach"]


def test_close_refuses_success_if_closing_changes_board_away_from_done(wire, monkeypatch):
    original = wire.run

    def automation(args, **kwargs):
        result = original(args, **kwargs)
        if args[1:3] == ["issue", "close"]:
            wire.status = "TODO"
        return result

    monkeypatch.setattr("ai_dlc.providers.github_issues.subprocess.run", automation)
    with pytest.raises(RuntimeError, match="uncertain"):
        transition(provider(), "closed")
    assert wire.issue["state"] == "CLOSED"


def test_reconcile_closed_refuses_concurrent_reopen_without_reclosing(wire, monkeypatch):
    wire.member = True
    wire.issue.update(state="CLOSED", stateReason="COMPLETED")
    original = wire.run

    def reopened(args, **kwargs):
        result = original(args, **kwargs)
        if args[1] == "api" and "mutation SetStatus" in kwargs["input"]:
            wire.issue.update(state="OPEN", stateReason="REOPENED")
        return result

    monkeypatch.setattr("ai_dlc.providers.github_issues.subprocess.run", reopened)
    with pytest.raises(RuntimeError, match="terminal|closed"):
        provider().invoke("reconcile_closed", {"reference": "1", "operation_id": "op"})
    assert "close" not in wire.events


@pytest.mark.parametrize(
    "failure", ["errors", "cursor", "hidden_content", "missing_value_type", "wrong_item_project"]
)
def test_incomplete_graphql_read_cannot_authorize_mutation(wire, monkeypatch, failure):
    wire.member = True
    original = wire.run

    def malformed(args, **kwargs):
        result = original(args, **kwargs)
        if args[1] != "api":
            return result
        query = json.loads(kwargs["input"])["query"]
        response = json.loads(result.stdout)
        if failure == "errors" and "query ProjectFields" in query:
            response["errors"] = [{"message": "denied"}]
        if failure == "cursor" and "query ProjectItems" in query:
            response["data"]["node"]["items"]["pageInfo"] = {"hasNextPage": True, "endCursor": None}
        if failure == "hidden_content" and "query ProjectItems" in query:
            response["data"]["node"]["items"]["nodes"].append(
                {"id": "unknown", "content": {"id": "other"}}
            )
        if failure == "missing_value_type" and "query ItemFields" in query:
            response["data"]["node"]["fieldValues"]["nodes"] = [{}]
        if failure == "wrong_item_project" and "query ItemFields" in query:
            response["data"]["node"]["project"]["id"] = "other"
        result.stdout = json.dumps(response)
        return result

    monkeypatch.setattr("ai_dlc.providers.github_issues.subprocess.run", malformed)
    with pytest.raises((ValueError, TypeError, RuntimeError)):
        transition(provider(), "closed")
    assert wire.events == []


def test_post_write_start_refuses_concurrent_terminal_issue(wire, monkeypatch):
    wire.member = True
    original = wire.run

    def cancelled(args, **kwargs):
        result = original(args, **kwargs)
        if args[1] == "api" and "mutation SetStatus" in kwargs["input"]:
            wire.issue.update(state="CLOSED", stateReason="NOT_PLANNED")
        return result

    monkeypatch.setattr("ai_dlc.providers.github_issues.subprocess.run", cancelled)
    with pytest.raises(RuntimeError, match="terminal"):
        transition(provider(), "in_progress")
    assert wire.events == ["status:DOING"]


def test_issue_creation_response_loss_recovers_correlation_and_attaches(tmp_path, wire):
    wire.exists = False
    app = service(tmp_path, wire)
    wire.lose.add("create")
    with pytest.raises(TimeoutError):
        app.publish("one")
    result = app.publish("one")
    assert result["tracker"]["project"]["item_id"] == "ITEM_1"
    assert wire.events == ["create", "attach"]


def test_work_start_rechecks_terminal_state_after_successful_start_journal(
    tmp_path, wire, monkeypatch
):
    app = service(tmp_path, wire)
    monkeypatch.setattr(app, "branch", lambda work: "work/one")
    assert app.start("one")["tracker"]["state"] == "in_progress"
    wire.issue.update(state="CLOSED", stateReason="NOT_PLANNED")
    wire.events.clear()
    with pytest.raises(ValueError, match="terminal"):
        app.start("one")
    assert wire.events == []


def test_graphql_uses_explicit_post_with_json_variables_in_body(wire):
    provider().invoke("capabilities", {})
    args, kwargs = wire.commands[0]
    assert "--method" in args and args[args.index("--method") + 1] == "POST"
    assert json.loads(kwargs["input"])["variables"] == {"project": "PROJECT_1", "after": None}
    assert "PROJECT_1" not in args
