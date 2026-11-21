"""KAN-364: readiness, doctor and onboard print a short summary a person can act on."""

import json
import shutil

import pytest
from typer.testing import CliRunner

from ai_dlc.setup.summaries import render_doctor, render_onboarding, render_readiness

JIRA_FIELDS = [
    "account_id",
    "auth_mode",
    "cloud_id",
    "project_key",
    "statuses.open",
    "token_env",
]


def check(component, dimension, status, next_action, reason="reason"):
    return {
        "component": component,
        "dimension": dimension,
        "status": status,
        "reason": reason,
        "next_action": next_action,
    }


def unconfigured_jira():
    """Readiness of a repository adopted with --tracker jira-cloud and nothing else done."""
    guidance = (
        "Declare the selected providers in shared ai-dlc.toml, then run "
        "ai-dlc agents render --apply after resolving authored-file conflicts."
    )
    return {
        "schema": 1,
        "ready": False,
        "qualification": "not-assessed",
        "checks": [
            check("claude-code", "guidance", "missing", guidance),
            check("codex", "guidance", "missing", guidance),
            check("claude-code", "tool", "ready", "No action required."),
            check("github", "configuration", "missing", "Configure scm.repository as owner/repo."),
            check("github", "provider-health", "unverified", "Run doctor."),
            *[
                check(
                    "jira-cloud", "configuration", "missing", f"Configure providers.jira-cloud.{f}."
                )
                for f in JIRA_FIELDS
            ],
            check(
                "jira-cloud",
                "credential",
                "blocked",
                "Bind credential provider.jira-cloud in machine configuration.",
            ),
            check("openspec", "tool", "missing", "Install module openspec."),
            check("none", "activation", "inactive", "No action required."),
        ],
    }


UNCONFIGURED_TEXT = """\
Not ready: 5 items to fix in this project, most important first.
- openspec tool: Install module openspec.
- github configuration: Configure scm.repository as owner/repo.
- jira-cloud configuration: Run `ai-dlc provider connect jira-cloud`; it sets account_id, auth_mode, cloud_id, project_key, statuses.open, token_env.
- jira-cloud credential: Bind credential provider.jira-cloud in machine configuration.
- claude-code guidance, codex guidance: Declare the selected providers in shared ai-dlc.toml, then run ai-dlc agents render --apply after resolving authored-file conflicts.
Run with --json for the full report.
"""

READY = {
    "schema": 1,
    "ready": True,
    "qualification": "not-assessed",
    "checks": [
        check("claude-code", "guidance", "ready", "No action required."),
        check("github", "provider-health", "unverified", "Run doctor."),
    ],
}


def test_unconfigured_jira_cloud_readiness_text():
    assert render_readiness(unconfigured_jira()) == UNCONFIGURED_TEXT


def test_ready_readiness_text():
    assert render_readiness(READY) == (
        "Ready: nothing blocks this project.\nRun with --json for the full report.\n"
    )


def test_provider_fields_collapse_into_one_connect_command_naming_the_root():
    text = render_readiness(unconfigured_jira(), "work/repo")
    assert text.count("ai-dlc provider connect") == 1
    assert "`ai-dlc provider connect jira-cloud --root work/repo`" in text
    for field in JIRA_FIELDS:
        assert text.count(field) == 1


@pytest.fixture
def cli(monkeypatch):
    from ai_dlc.cli import app

    def run(args, *, terminal):
        monkeypatch.setattr("ai_dlc.cli._stdout_is_terminal", lambda: terminal)
        return CliRunner().invoke(app, args)

    return run


def test_readiness_prints_text_at_a_terminal_and_json_otherwise(cli, monkeypatch, tmp_path):
    report = unconfigured_jira()
    monkeypatch.setattr("ai_dlc.setup.provision.readiness_config", lambda root: {})
    monkeypatch.setattr(
        "ai_dlc.setup.provision.project_readiness", lambda root, config, environ: report
    )
    args = ["project", "readiness", "--root", "."]

    text = cli(args, terminal=True)
    assert text.exit_code == 1
    assert text.stdout == UNCONFIGURED_TEXT
    for result in (cli([*args, "--json"], terminal=True), cli(args, terminal=False)):
        assert result.exit_code == 1
        assert json.loads(result.stdout) == report


def test_doctor_preflight_prints_text_at_a_terminal(cli, monkeypatch, tmp_path):
    preflight = {
        "schema": 1,
        "mode": "machine-preflight",
        "ready": False,
        "checks": [
            {
                "id": "git",
                "status": "ready",
                "required": True,
                "next_action": "No action required.",
            },
            {"id": "gh", "status": "missing", "required": True, "next_action": "Install gh."},
            {"id": "mise", "status": "info", "required": False, "next_action": "Optional."},
            {
                "id": "client:codex",
                "status": "missing",
                "required": True,
                "next_action": "Install codex.",
            },
        ],
        "next": "Install gh.",
    }
    monkeypatch.setattr(
        "ai_dlc.environment.preflight.machine_preflight", lambda root, **kwargs: preflight
    )
    args = ["doctor", "--root", str(tmp_path)]

    text = cli(args, terminal=True)
    assert text.exit_code == 1
    assert text.stdout == (
        "Not ready: 2 items to fix on this machine, most important first.\n"
        "- gh: Install gh.\n"
        "- client:codex: Install codex.\n"
        "Run with --json for the full report.\n"
    )
    machine = cli(["machine", "doctor", "--root", str(tmp_path)], terminal=True)
    assert machine.stdout == text.stdout
    assert json.loads(cli([*args, "--json"], terminal=True).stdout) == preflight


def test_ready_preflight_names_the_next_step():
    text = render_doctor(
        {"mode": "machine-preflight", "ready": True, "checks": [], "next": "Adopt a repository."}
    )
    assert text == (
        "Ready: nothing blocks this machine.\nAdopt a repository.\n"
        "Run with --json for the full report.\n"
    )


def test_project_doctor_summary_orders_and_deduplicates():
    result = {
        "ready": False,
        "missing": ["git"],
        "runtime_drift": [],
        "signins": [
            "gh auth login",
            "Bind credential provider.jira-cloud in machine configuration",
        ],
        "configuration": ["scm.repository is required", "scm.workflow is required"],
        "managed_conflicts": ["AGENTS.md", "CLAUDE.md", "a.md", "b.md"],
        "hooks": {"ready": True},
        "provider_health": [],
        "provider_capabilities": [
            {"provider": "jira-cloud", "ready": False, "reason": "Check access"}
        ],
        "user_agents": {"clean": True},
        "machine_status": {"ready": False, "next": "Enroll a profile."},
        "project_readiness": unconfigured_jira(),
    }
    lines = render_doctor(result).splitlines()
    assert lines[0] == "Not ready: 11 items to fix in this project, most important first."
    assert lines[1:4] == [
        "- git: Install git, then rerun `ai-dlc doctor`.",
        "- sign-in: Run `gh auth login`.",
        "- sign-in, jira-cloud credential: Bind credential provider.jira-cloud in machine configuration.",
    ]
    # scm.repository is already named by readiness; scm.workflow is doctor's own.
    assert sum("scm.repository" in line for line in lines) == 1
    assert "- project configuration: Set scm.workflow in ai-dlc.toml." in lines
    assert (
        "- managed files: AGENTS.md, CLAUDE.md, a.md and 1 more differ from the rendered "
        "guidance; review them, then run `ai-dlc agents render --apply`."
    ) in lines
    assert lines[-3:] == [
        "- jira-cloud: Check access.",
        "- machine: Enroll a profile.",
        "Run with --json for the full report.",
    ]


PLAN = {
    "schema": 1,
    "state": "actionable",
    "findings": [],
    "actions": [
        {
            "id": "render-preview",
            "argv": ["ai-dlc", "agents", "render", "--root", "repo"],
            "requires_review": False,
            "effects": ["Previews generated guidance."],
        },
        {
            "id": "render-apply",
            "argv": ["ai-dlc", "agents", "render", "--root", "repo", "--apply"],
            "requires_review": True,
            "effects": ["Writes reviewed guidance."],
        },
        {"id": "target-check", "argv": [], "requires_review": True, "effects": ["Runs checks."]},
    ],
}


def test_onboarding_text_lists_ordered_commands_and_marks_review():
    assert render_onboarding(PLAN) == (
        "Actionable: run the commands below in order.\n"
        "Commands, in order ([review] = read its preview before running it):\n"
        "  1. ai-dlc agents render --root repo  # render-preview: Previews generated guidance.\n"
        "  2. [review] ai-dlc agents render --root repo --apply  # render-apply: Writes reviewed guidance.\n"
        "  3. [review] (input required)  # target-check: Runs checks.\n"
        "Run with --json for the full report.\n"
    )


def test_onboard_prints_text_at_a_terminal_and_json_otherwise(cli, monkeypatch, tmp_path):
    blocked = {
        **PLAN,
        "state": "blocked",
        "findings": [{"component": "clients", "reason": "Select an agent client."}],
    }
    monkeypatch.setattr("ai_dlc.setup.onboarding.plan_onboarding", lambda root, **kwargs: blocked)
    args = ["project", "onboard", "--root", str(tmp_path)]

    text = cli(args, terminal=True)
    assert text.exit_code == 1
    assert text.stdout.splitlines()[:2] == [
        "Not actionable (blocked): 1 finding to resolve first.",
        "- clients: Select an agent client.",
    ]
    for result in (cli([*args, "--json"], terminal=True), cli(args, terminal=False)):
        assert result.exit_code == 1
        assert json.loads(result.stdout) == blocked


def test_a_real_jira_cloud_repository_gets_one_connect_line(cli, monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    tools = tmp_path / "bin"
    tools.mkdir()
    (tools / "git").symlink_to(shutil.which("git"))
    monkeypatch.setenv("PATH", str(tools))
    root = tmp_path / "repo"
    created = cli(["project", "init", str(root), "--tracker", "jira-cloud"], terminal=False)
    assert created.exit_code == 0, created.output

    report = json.loads(cli(["project", "readiness", "--root", str(root)], terminal=False).stdout)
    fields = [
        row["next_action"].removeprefix("Configure providers.jira-cloud.").rstrip(".")
        for row in report["checks"]
        if row["next_action"].startswith("Configure providers.jira-cloud.")
    ]
    assert len(fields) > 1
    text = cli(["project", "readiness", "--root", str(root)], terminal=True)
    assert text.exit_code == 1
    assert text.stdout.startswith("Not ready: ")
    connect = [line for line in text.stdout.splitlines() if "ai-dlc provider connect" in line]
    command = f"ai-dlc provider connect jira-cloud --root {root}"
    assert connect == [f"- jira-cloud configuration: Run `{command}`; it sets {', '.join(fields)}."]
    assert len(text.stdout.splitlines()) < len(report["checks"])
