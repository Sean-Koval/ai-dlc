"""Phase-level tests for the pure helpers behind agents rendering and bundle inspection."""

import hashlib

import pytest

from ai_dlc.harness.agents import (
    _collect_render_changes,
    _plan_client_skills,
    _plan_codex_config,
    _plan_guidance_files,
    _plan_mcp_servers,
    _plan_provider_guidance,
    _resolve_render_clients,
    _shared_guidance_lines,
    _summarize_bundle_states,
    read_managed_section,
)


def _digest(body: str) -> str:
    return hashlib.sha256(body.encode()).hexdigest()


def _reader(files: dict[str, str]):
    def read(name: str) -> bytes | None:
        return files[name].encode() if name in files else None

    return read


def _text_reader(files: dict[str, str]):
    def text(name: str) -> str:
        return files.get(name, "")

    return text


# --- inspect_bundle_guidance: summarize phase ---------------------------------


def test_summarize_bundle_states_reports_ready_when_nothing_collected():
    states = {"flow": {"blocked": [], "missing": []}}
    assert _summarize_bundle_states(["flow"], states) == [
        {
            "bundle_id": "flow",
            "status": "ready",
            "reason": "bundle guidance is intact and rendered for configured clients",
            "next_action": "No action required.",
        }
    ]


def test_summarize_bundle_states_prefers_blocked_and_first_sorted_detail():
    states = {
        "flow": {"blocked": ["zeta conflict", "alpha conflict", "alpha conflict"], "missing": ["x"]}
    }
    (result,) = _summarize_bundle_states(["flow"], states)
    assert result["status"] == "blocked"
    assert result["reason"] == "alpha conflict"
    assert result["next_action"].startswith("Resolve bundle guidance conflicts")


def test_summarize_bundle_states_prefers_vendored_path_reason_when_missing():
    states = {
        "flow": {
            "blocked": [],
            "missing": [
                "rendered bundle output is missing: docs/templates/a.md",
                "vendored bundle path is missing: skills/a",
            ],
        }
    }
    (result,) = _summarize_bundle_states(["flow"], states)
    assert result["status"] == "missing"
    assert result["reason"] == "vendored bundle path is missing: skills/a"
    assert "Restore missing vendored content" in result["next_action"]


def test_summarize_bundle_states_keeps_bundle_id_order():
    states = {name: {"blocked": [], "missing": []} for name in ["two", "one"]}
    results = _summarize_bundle_states(["two", "one"], states)
    assert [result["bundle_id"] for result in results] == ["two", "one"]


# --- _render_agents: client resolution ---------------------------------------


def test_resolve_render_clients_defaults_and_accepts_strings():
    assert _resolve_render_clients({}, None) == ["claude-code", "codex"]
    assert _resolve_render_clients({"roles": {"agent-client": "codex"}}, None) == ["codex"]
    assert _resolve_render_clients({"roles": {"agent-client": ["codex"]}}, "antigravity") == [
        "antigravity"
    ]


def test_resolve_render_clients_rejects_unknown_client():
    with pytest.raises(ValueError, match="unsupported agent client"):
        _resolve_render_clients({"roles": {"agent-client": ["vim"]}}, None)


# --- _render_agents: guidance composition ------------------------------------


def test_shared_guidance_lines_lists_required_checks_and_indexes():
    checks = {"required": ["lint", "ghost"], "commands": {"lint": "ruff check"}}
    lines = _shared_guidance_lines({"checks": checks}, "## Providers", "## Bundles")
    assert lines[0] == "# Shared project guidance"
    assert "- lint: `ruff check`" in lines
    assert "- ghost: `MISSING COMMAND`" in lines
    assert lines[-2:] == ["## Providers", "## Bundles"]


def test_shared_guidance_lines_omits_empty_bundle_index():
    lines = _shared_guidance_lines({}, "## Providers", "")
    assert lines[-1] == "## Providers"
    assert "" not in lines[-1:]


_SPECIFICATION = "Use specification artifacts for implementation tasks"
_TRACKER = "Use the selected tracker for priority and status"
_ARCHIVE = "ai-dlc work archive"
_MERGE = "Immediately before merge"
_FINISH = "ai-dlc work finish"
_RECOVERY = "temporary detached worktree"


def _guidance(config: dict) -> str:
    return "\n".join(_shared_guidance_lines(config, "## Providers", ""))


@pytest.mark.parametrize(
    ("roles", "providers", "present", "absent"),
    [
        ({}, {}, (), (_SPECIFICATION, _TRACKER, _ARCHIVE, _MERGE, _FINISH, _RECOVERY)),
        (
            {"specs": "openspec"},
            {},
            (_SPECIFICATION, _ARCHIVE),
            (_TRACKER, _MERGE, _FINISH, _RECOVERY, "before merge with"),
        ),
        (
            {"scm": "github"},
            {},
            (_MERGE,),
            (_SPECIFICATION, _TRACKER, _ARCHIVE, _FINISH, _RECOVERY),
        ),
        (
            {"tracker": "issues", "scm": "hub"},
            {"issues": {"kind": "github-issues"}, "hub": {"type": "github-scm"}},
            (_TRACKER, _MERGE, _FINISH),
            (_SPECIFICATION, _ARCHIVE, _RECOVERY),
        ),
        (
            {"specs": "openspec", "scm": "github"},
            {},
            (_SPECIFICATION, _ARCHIVE, _MERGE),
            (_TRACKER, _FINISH, _RECOVERY),
        ),
        (
            {"specs": "custom", "tracker": "issues", "scm": "hub"},
            {
                "custom": {"kind": "executable", "component": "openspec"},
                "issues": {"kind": "linear"},
                "hub": {"kind": "github", "component": "github"},
            },
            (_SPECIFICATION, _TRACKER, _MERGE, _FINISH),
            (_ARCHIVE, _RECOVERY),
        ),
        (
            {"specs": "spec-alias", "tracker": "tracker-alias", "scm": "scm-alias"},
            {
                "spec-alias": {"kind": "openspec", "type": "executable"},
                "tracker-alias": {"kind": "plane", "type": "custom"},
                "scm-alias": {"kind": "github-scm", "type": "custom"},
            },
            (_SPECIFICATION, _TRACKER, _ARCHIVE, _MERGE, _FINISH, _RECOVERY),
            (),
        ),
        (
            {"tracker": "custom-tracker", "scm": "custom-scm"},
            {
                "custom-tracker": {"kind": "executable", "component": "linear"},
                "custom-scm": {"kind": "python", "component": "github"},
            },
            (_TRACKER,),
            (_SPECIFICATION, _ARCHIVE, _MERGE, _FINISH, _RECOVERY),
        ),
    ],
)
def test_shared_guidance_follows_selected_runtime_capabilities(roles, providers, present, absent):
    """Each capability sentence must follow runtime identity, never component metadata."""
    body = _guidance({"roles": roles, "providers": providers})
    for phrase in present:
        assert phrase in body
    for phrase in absent:
        assert phrase not in body


@pytest.mark.parametrize("tracker", ["linear", "github-issues", "jira-cloud", "plane"])
def test_shared_guidance_supports_each_builtin_tracker_with_and_without_github(tracker):
    tracker_only = _guidance({"roles": {"tracker": tracker}})
    assert _TRACKER in tracker_only
    assert all(phrase not in tracker_only for phrase in (_MERGE, _FINISH, _RECOVERY))

    full = _guidance(
        {
            "roles": {"specs": "openspec", "tracker": tracker, "scm": "github"},
            "gates": {"finish": []},
        }
    )
    assert all(
        phrase in full
        for phrase in (_SPECIFICATION, _TRACKER, _ARCHIVE, _MERGE, _FINISH, _RECOVERY)
    )


def test_shared_guidance_scopes_knowledge_and_documentation_gate_advice():
    selected = _guidance(
        {
            "roles": {"knowledge": "obsidian", "scm": "github"},
            "checks": {
                "required": ["documentation", "test"],
                "commands": {"documentation": "ai-dlc docs gate", "test": "pytest"},
            },
        }
    )
    assert "selected knowledge provider" in selected
    assert "documentation gate reports stale" in selected
    assert selected.index("- documentation: `ai-dlc docs gate`") < selected.index(
        "- test: `pytest`"
    )

    no_documentation_gate = _guidance(
        {
            "roles": {"scm": "github"},
            "checks": {"required": ["test"], "commands": {"test": "pytest"}},
            "providers": {
                "profile-only-knowledge": {"kind": "obsidian"},
                "profile-only-specs": {"kind": "openspec"},
            },
        }
    )
    assert "selected knowledge provider" not in no_documentation_gate
    assert "documentation gate reports stale" not in no_documentation_gate
    assert _SPECIFICATION not in no_documentation_gate
    assert _ARCHIVE not in no_documentation_gate


def test_plan_guidance_files_wraps_agents_and_writes_claude_reference():
    planned = _plan_guidance_files(_text_reader({}), "body\n", ["claude-code", "codex"])
    assert list(planned) == ["AGENTS.md", "CLAUDE.md"]
    assert read_managed_section(planned["AGENTS.md"])["body"] == "body\n"
    assert planned["CLAUDE.md"] == "@AGENTS.md\n"


def test_plan_guidance_files_skips_claude_without_claude_client_and_wraps_authored_claude():
    assert "CLAUDE.md" not in _plan_guidance_files(_text_reader({}), "body\n", ["codex"])
    planned = _plan_guidance_files(
        _text_reader({"CLAUDE.md": "# Mine\n"}), "body\n", ["claude-code"]
    )
    assert planned["CLAUDE.md"].startswith("# Mine\n\n<!-- ai-dlc:begin ")
    assert read_managed_section(planned["CLAUDE.md"])["body"] == "@AGENTS.md\n"


# --- _render_agents: MCP server shaping --------------------------------------


def test_plan_mcp_servers_shapes_each_client_representation():
    config = {
        "agents": {
            "servers": [
                {"id": "docs", "url": "https://example.test/mcp"},
                {"id": "local", "command": "tool", "args": ["serve"], "env": ["TOKEN"]},
            ]
        }
    }
    servers, codex, antigravity = _plan_mcp_servers(config, ["claude-code", "codex"])
    assert servers == {
        "docs": {"url": "https://example.test/mcp", "type": "http"},
        "local": {"command": "tool", "args": ["serve"], "env": {"TOKEN": "${TOKEN}"}},
    }
    assert codex == {
        "docs": {"url": "https://example.test/mcp"},
        "local": {"command": "tool", "args": ["serve"], "env_vars": ["TOKEN"]},
    }
    assert antigravity == {}


def test_plan_mcp_servers_shapes_antigravity_transports():
    config = {
        "agents": {
            "servers": [
                {"id": "docs", "url": "https://example.test/mcp"},
                {"id": "local", "command": "tool", "args": ["serve"]},
            ]
        }
    }
    _, _, antigravity = _plan_mcp_servers(config, ["antigravity"])
    assert antigravity == {
        "docs": {"serverUrl": "https://example.test/mcp"},
        "local": {"command": "tool", "args": ["serve"]},
    }


@pytest.mark.parametrize(
    ("servers", "clients", "message"),
    [
        ([{"id": "a", "command": "x"}, {"id": "a", "command": "y"}], ["codex"], "duplicate MCP"),
        ([{"id": "a"}], ["codex"], "requires command or URL"),
        ([{"id": "a", "command": "/Users/" + "me/tool"}], ["codex"], "personal paths"),
        ([{"id": "a", "command": "x", "env": ["secret=1"]}], ["codex"], "environment variable"),
        ([{"id": "a", "command": "x", "env": "TOKEN"}], ["codex"], "environment variable"),
        ([{"id": "a", "command": "x", "url": "u"}], ["antigravity"], "unambiguous transport"),
        ([{"id": "a", "command": "x", "env": ["TOKEN"]}], ["antigravity"], "interpolation"),
    ],
)
def test_plan_mcp_servers_rejects_invalid_configuration(servers, clients, message):
    with pytest.raises(ValueError, match=message):
        _plan_mcp_servers({"agents": {"servers": servers}}, clients)


# --- _render_agents: owned provider guidance and skills ----------------------


def test_plan_provider_guidance_retires_obsolete_and_plans_desired():
    files = {".ai-dlc/providers/old.md": "old\n", ".ai-dlc/providers/keep.md": "keep\n"}
    owned = {name: _digest(body) for name, body in files.items()}
    owned["unrelated"] = "x"
    planned: dict[str, str] = {}
    removed: list[str] = []
    copies = {".ai-dlc/providers/keep.md": "keep v2\n", ".ai-dlc/providers/new.md": "new\n"}
    _plan_provider_guidance(_reader(files), copies, owned, planned, removed)
    assert removed == [".ai-dlc/providers/old.md"]
    assert planned == copies
    assert owned == {
        "unrelated": "x",
        ".ai-dlc/providers/keep.md": _digest("keep v2\n"),
        ".ai-dlc/providers/new.md": _digest("new\n"),
    }


def test_plan_provider_guidance_rejects_edited_or_authored_files():
    edited = {".ai-dlc/providers/keep.md": "edited\n"}
    with pytest.raises(ValueError, match="managed provider guidance conflict"):
        _plan_provider_guidance(
            _reader(edited), {}, {".ai-dlc/providers/keep.md": _digest("keep\n")}, {}, []
        )
    authored = {".ai-dlc/providers/new.md": "mine\n"}
    with pytest.raises(ValueError, match="authored provider guidance conflict"):
        _plan_provider_guidance(
            _reader(authored), {".ai-dlc/providers/new.md": "ours\n"}, {}, {}, []
        )


def test_plan_client_skills_leaves_bundle_owned_paths_alone():
    prefix = ".codex/skills/"
    bundle_path = prefix + "flow/SKILL.md"
    stale_path = prefix + "stale/SKILL.md"
    files = {bundle_path: "bundle\n", stale_path: "stale\n"}
    owned = {bundle_path: _digest("bundle\n"), stale_path: _digest("stale\n")}
    planned: dict[str, str] = {}
    removed: list[str] = []
    desired = {prefix + "day-start/SKILL.md": "shipped\n"}
    _plan_client_skills(
        _reader(files),
        prefix,
        desired,
        {bundle_path: {"owner": "flow", "sha256": owned[bundle_path]}},
        owned,
        planned,
        removed,
    )
    assert removed == [stale_path]
    assert planned == desired
    assert owned == {
        bundle_path: _digest("bundle\n"),
        **{k: _digest(v) for k, v in desired.items()},
    }


def test_plan_client_skills_rejects_conflicts():
    prefix = ".codex/skills/"
    path = prefix + "day-start/SKILL.md"
    with pytest.raises(ValueError, match="managed skill conflict"):
        _plan_client_skills(
            _reader({path: "edited\n"}), prefix, {}, {}, {path: _digest("old\n")}, {}, []
        )
    with pytest.raises(ValueError, match="authored skill conflict"):
        _plan_client_skills(_reader({path: "mine\n"}), prefix, {path: "ours\n"}, {}, {}, {}, [])


# --- _render_agents: codex config, change collection -------------------------


def test_plan_codex_config_renders_servers_or_placeholder():
    planned: dict[str, str] = {}
    _plan_codex_config(_text_reader({}), {}, planned)
    section = read_managed_section(planned[".codex/config.toml"], toml=True)
    assert section["body"] == "# No project MCP servers configured.\n"
    _plan_codex_config(_text_reader({}), {"docs": {"url": "https://example.test"}}, planned)
    assert '[mcp_servers.docs]\nurl = "https://example.test"' in planned[".codex/config.toml"]


def test_plan_codex_config_rejects_invalid_unmanaged_toml():
    with pytest.raises(ValueError):
        _plan_codex_config(_text_reader({".codex/config.toml": "[broken\n"}), {}, {})


def test_collect_render_changes_lists_differences_and_removals():
    files = {"same.md": "same\n", "other.md": "old\n"}
    planned = {"same.md": "same\n", "other.md": "new\n", "fresh.md": "x\n"}
    changed = _collect_render_changes(_reader(files), planned, ["gone.md"], set())
    assert changed == ["other.md", "fresh.md", "gone.md"]


def test_collect_render_changes_rejects_removing_referenced_guidance():
    with pytest.raises(ValueError, match="still referenced"):
        _collect_render_changes(
            _reader({}), {}, [".ai-dlc/providers/x.md"], {".ai-dlc/providers/x.md"}
        )
