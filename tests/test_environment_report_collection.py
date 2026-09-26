"""Read-only report collection at the privacy boundary."""

import hashlib
import json
import os
import socket
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import tomli_w

from ai_dlc.environment.report import collect_report
from ai_dlc.environment.report_schema import completeness, parse_report, report_bytes


@pytest.fixture
def project(tmp_path):
    root, home = tmp_path / "project", tmp_path / "home"
    root.mkdir()
    home.mkdir()
    (root / "ai-dlc.toml").write_text(
        'schema = 4\n[roles]\nscm = "github"\nagent-client = ["codex"]\n', encoding="utf-8"
    )
    return root, home


def collect(project, **kwargs):
    root, home = project
    return collect_report(root, home=home, environ={"PATH": ""}, **kwargs)


def items(report, field):
    return {item["id"]: item for item in report[field]}


def enroll(project, *, private="SECRET-one"):
    _, home = project
    content = f'schema = 4\nprofile_id = "team"\n[preferences]\nlabel = "{private}"\n'.encode()
    config = home / ".config/ai-dlc"
    cache = home / (".cache/ai-dlc/profiles/team/" + "a" * 40)
    cache.mkdir(parents=True, exist_ok=True)
    config.mkdir(parents=True, exist_ok=True)
    (config / "machines").mkdir(exist_ok=True)
    (cache / "ai-dlc-profile.toml").write_bytes(content)
    raw_digest = hashlib.sha256(
        b"ai-dlc-profile.toml\0" + str(len(content)).encode() + b"\0" + content
    ).hexdigest()
    (config / "enrollment.toml").write_text(
        tomli_w.dumps(
            {
                "schema": 1,
                "profile_id": "team",
                "source": f"https://{private}@example.test/team",
                "requested_ref": private,
                "resolved_commit": "a" * 40,
                "content_sha256": raw_digest,
                "machine_id": "personal-machine",
            }
        ),
        encoding="utf-8",
    )
    (config / "machines/personal-machine.toml").write_text(
        f'schema = 4\n[paths]\nvault = "/private/{private}"\n', encoding="utf-8"
    )
    return config, cache, raw_digest


def test_default_collection_is_read_only_and_excludes_private_values(project, monkeypatch):
    root, home = project
    _, _, raw_digest = enroll(project)
    (home / ".codex").mkdir()
    (home / ".codex/config.toml").write_text('private = "SECRET-client"', encoding="utf-8")
    (root / "ai-dlc.toml").write_text(
        'schema=4\n[roles]\nscm="github"\nagent-client=["codex"]\n'
        '[checks.commands]\nprivate="echo SECRET-command"\n',
        encoding="utf-8",
    )
    before = {p: p.read_bytes() for p in root.parent.rglob("*") if p.is_file()}
    original_open = Path.open
    original_descriptor_open = os.open

    def checked_open(path, mode="r", *args, **kwargs):
        assert not set(mode) & set("wax+")
        assert ".codex" not in path.parts
        return original_open(path, mode, *args, **kwargs)

    def checked_descriptor_open(path, flags, *args, **kwargs):
        assert not flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
        assert ".codex" not in Path(path).parts
        return original_descriptor_open(path, flags, *args, **kwargs)

    def forbidden(*args, **kwargs):
        raise AssertionError("default collection caused an effect")

    with monkeypatch.context() as patch:
        patch.setattr(Path, "open", checked_open)
        patch.setattr(os, "open", checked_descriptor_open)
        patch.setattr(subprocess, "Popen", forbidden)
        patch.setattr(socket, "socket", forbidden)
        result = collect_report(root, home=home, environ={"PATH": "", "TOKEN": "SECRET-env"})
    assert parse_report(report_bytes(result)) == result
    raw = json.dumps(result)
    assert "SECRET" not in raw and str(home) not in raw and raw_digest not in raw
    assert before == {p: p.read_bytes() for p in root.parent.rglob("*") if p.is_file()}
    assert result["profile"]["id"] == "team"
    assert result["profile"]["content_sha256"] is None
    assert result["project"]["roles"] == [
        {"role": "scm", "provider": "github", "component": "github"}
    ]
    assert completeness(result) == (False, False)


def test_excluded_profile_bytes_do_not_change_report_identities(project):
    enroll(project, private="SECRET-one")
    first = collect(project)
    enroll(project, private="SECRET-two")
    second = collect(project)
    assert first["configuration_identity"] == second["configuration_identity"]
    assert first["observation_identity"] == second["observation_identity"]


def test_no_enrollment_and_missing_project_are_distinct(project):
    result = collect(project)
    assert result["profile"]["state"] == "not-applicable"
    assert result["project"]["state"] == "known"
    (project[0] / "ai-dlc.toml").unlink()
    result = collect(project)
    assert result["project"]["state"] == "missing"
    assert completeness(result) == (False, False)


def test_corrupt_enrollment_preserves_independent_project_selection(project):
    config, _, _ = enroll(project)
    (config / "enrollment.toml").write_text("SECRET-invalid [", encoding="utf-8")
    result = collect(project)
    assert result["profile"]["state"] == "unknown"
    assert result["project"]["roles"][0]["provider"] == "github"
    assert items(result, "clients")["codex"]["configured"] == "yes"
    assert any(item["field"] == "profile" for item in result["limitations"])
    assert "SECRET" not in json.dumps(result)


def test_missing_profile_cache_preserves_lock_pin_and_project(project):
    _, cache, _ = enroll(project)
    (cache / "ai-dlc-profile.toml").unlink()
    result = collect(project)
    assert result["profile"]["commit"] == "a" * 40
    assert result["profile"]["state"] in {"missing", "unknown"}
    assert result["project"]["roles"][0]["provider"] == "github"


def test_runtime_pins_map_executable_names_and_explicit_client_conflicts(project):
    root, _ = project
    (root / "ai-dlc.toml").write_text(
        'schema=4\n[roles]\nscm="github"\nspecs="openspec"\nagent-client=["codex", "antigravity"]\n'
        '[agents.clients.codex]\nversion="0.152.0"\n',
        encoding="utf-8",
    )
    (root / ".mise.toml").write_text(
        '[tools]\nnode="24.1.0"\nrust="1.90.0"\n"npm:@openai/codex"="0.153.0"\n', encoding="utf-8"
    )
    result = collect(project)
    runtimes = items(result, "runtimes")
    assert runtimes["node"]["version"]["intended"] == "24.1.0"
    assert runtimes["cargo"]["version"]["intended"] == "1.90.0"
    assert runtimes["rustc"]["version"]["intended"] == "1.90.0"
    assert runtimes.get("npm", {"version": {"intended": None}})["version"]["intended"] is None
    assert items(result, "clients")["codex"]["version"]["intended"] is None
    assert any(item["reason_code"] == "conflicting-declarations" for item in result["limitations"])
    assert "antigravity" in items(result, "clients")
    assert result["project"]["components"][0]["platform_support"]["os"] is None


def test_unsupported_pin_and_identifier_are_not_echoed(project):
    root, _ = project
    (root / "ai-dlc.toml").write_text(
        'schema=4\n[roles]\nagent-client=["/private/SECRET"]\n', encoding="utf-8"
    )
    (root / ".mise.toml").write_text('[tools]\npython="SECRET-url"\n', encoding="utf-8")
    result = collect(project)
    assert "SECRET" not in json.dumps(result)
    assert result["clients"][0]["id"] is None
    assert items(result, "runtimes")["python"]["version"]["intended"] is None
    assert completeness(result) == (False, False)


@pytest.mark.parametrize(
    "body,state",
    [
        (None, "missing"),
        ("authored only", "missing"),
        (
            "<!-- ai-dlc:begin " + "a" * 64 + " -->\nSECRET-modified\n<!-- ai-dlc:end -->",
            "mismatch",
        ),
    ],
)
def test_guidance_observes_missing_and_edits_without_exporting_bytes(project, body, state):
    if body is not None:
        (project[0] / "AGENTS.md").write_text(body, encoding="utf-8")
    result = collect(project)
    guidance = {g["id"]: g for g in result["project"]["guidance"]}["agents"]
    assert guidance["state"] == state
    assert guidance["expected_sha256"] is None and guidance["observed_sha256"] is None
    assert "SECRET" not in json.dumps(result)


def test_intact_guidance_marker_is_not_proof_of_desired_freshness(project):
    (project[0] / "ai-dlc.toml").write_text(
        'schema=4\n[roles]\nagent-client=["codex"]\n[agents]\nskills=[]\n', encoding="utf-8"
    )
    body = "arbitrary old instructions\n"
    digest = hashlib.sha256(body.encode()).hexdigest()
    (project[0] / "AGENTS.md").write_text(
        f"<!-- ai-dlc:begin {digest} -->\n{body}<!-- ai-dlc:end -->", encoding="utf-8"
    )
    result = collect(project)
    assert (
        next(g for g in result["project"]["guidance"] if g["id"] == "agents")["state"] == "unknown"
    )
    assert items(result, "clients")["codex"]["rendered"] == "unknown"


def test_native_alias_projection_excludes_recipe_and_credentials(project):
    root, home = project
    (root / "ai-dlc.toml").write_text(
        """schema=4
[roles]
tracker="linear"
agent-client=["codex"]
[providers.linear]
token_env="PRIVATE_TOKEN"
[agents]
servers=[{id="tracker", provider="linear", transport="http", url="https://SECRET-endpoint", env={PRIVATE="SECRET-value"}}]
""",
        encoding="utf-8",
    )
    result = collect_report(root, home=home, environ={"PATH": "", "PRIVATE_TOKEN": "SECRET-token"})
    assert "SECRET" not in json.dumps(result) and "PRIVATE_TOKEN" not in json.dumps(result)
    assert (
        next(a for a in result["auth"] if a["id"] == "linear")["credential_presence"] == "present"
    )
    native = next(g for g in result["project"]["guidance"] if g["kind"] == "native-server")[
        "native_server"
    ]
    assert native["alias"] == "tracker" and native["recipe_identity"] is None


def test_shell_environment_is_not_active_shell_evidence(project):
    result = collect_report(project[0], home=project[1], environ={"PATH": "", "SHELL": "/bin/zsh"})
    assert result["platform"]["shell_family"] is None
    assert result["engine"]["current_process"]["package_version"] is not None
    assert result["engine"]["current_process"]["source_revision"] is None


def test_selected_skills_and_provider_guidance_preserve_missing_or_edited_state(project):
    root, _ = project
    (root / "ai-dlc.toml").write_text(
        'schema=4\n[roles]\nscm="github"\nagent-client=["codex"]\n[agents]\nskills=["day-start"]\n',
        encoding="utf-8",
    )
    provider = root / ".ai-dlc/providers/github.md"
    provider.parent.mkdir(parents=True)
    provider.write_text("SECRET-edited provider content", encoding="utf-8")
    (root / ".ai-dlc/agent-ownership.json").write_text(
        json.dumps({"schema": 2, "files": {".ai-dlc/providers/github.md": "a" * 64}}),
        encoding="utf-8",
    )
    result = collect(project)
    guidance = {item["id"]: item for item in result["project"]["guidance"]}
    assert guidance["provider.github"]["state"] == "mismatch"
    assert guidance["skill.day-start"]["state"] == "missing"
    assert "SECRET" not in json.dumps(result)


def test_bundles_and_skill_selection_affect_desired_identity(project):
    root, _ = project
    prefix = 'schema=4\n[roles]\nagent-client=["codex"]\n[agents]\nskills=[]\n'
    (root / "ai-dlc.toml").write_text(prefix + 'bundles=["frontend"]\n', encoding="utf-8")
    first = collect(project)
    (root / "ai-dlc.toml").write_text(prefix + 'bundles=["backend"]\n', encoding="utf-8")
    second = collect(project)
    assert first["configuration_identity"] != second["configuration_identity"]


def test_unknown_valid_runtime_is_unsupported_not_missing(project):
    (project[0] / ".mise.toml").write_text('[tools]\ncustom="1.2.3"\n', encoding="utf-8")
    result = collect(project)
    assert items(result, "runtimes")["custom"]["version"]["state"] == "unsupported"


def test_missing_claude_guidance_marks_selected_client_unrendered(project):
    root, _ = project
    body = "old managed body\n"
    digest = hashlib.sha256(body.encode()).hexdigest()
    (root / "AGENTS.md").write_text(
        f"<!-- ai-dlc:begin {digest} -->\n{body}<!-- ai-dlc:end -->", encoding="utf-8"
    )
    (root / "ai-dlc.toml").write_text(
        'schema=4\n[roles]\nagent-client=["claude-code"]\n', encoding="utf-8"
    )
    assert items(collect(project), "clients")["claude-code"]["rendered"] == "no"


def test_ambiguous_native_transport_is_unknown(project):
    (project[0] / "ai-dlc.toml").write_text(
        'schema=4\n[roles]\nagent-client=[]\n[agents]\nservers=[{id="example", command="SECRET", url="https://SECRET", transport="http"}]\n',
        encoding="utf-8",
    )
    result = collect(project)
    native = result["project"]["guidance"][0]["native_server"]
    assert native["transport"] is None
    assert any(l["reason_code"] == "conflicting-declarations" for l in result["limitations"])


def test_host_lookup_errors_become_safe_scoped_unknowns(project, monkeypatch):
    from ai_dlc.environment import report

    def fail(*args):
        raise OSError("SECRET-diagnostic /private/home")

    monkeypatch.setattr(report, "find_executable", fail)
    result = collect(project)
    assert result["engine"]["path_selected"]["state"] == "unknown"
    assert "SECRET" not in json.dumps(result)


def test_malformed_client_values_are_scoped_not_crashes(project):
    (project[0] / "ai-dlc.toml").write_text(
        'schema=4\n[roles]\nagent-client=[{private="SECRET"}]\n', encoding="utf-8"
    )
    result = collect(project)
    assert result["clients"][0]["id"] is None
    assert "SECRET" not in json.dumps(result)


def test_explicit_probe_flag_observes_selected_executable_only(project, monkeypatch):
    from ai_dlc.environment import report

    called = []

    def probe(name, *, environ):
        called.append(name)
        return {"observed": "1.2.3", "state": "observed", "reason": None}

    monkeypatch.setattr(report, "probe_version", probe)
    result = collect(project, probe_versions=True)
    assert set(called) == {"ai-dlc", "git", "gh", "codex"}
    assert len(called) == len(set(called))
    assert items(result, "clients")["codex"]["version"]["observed"] == "1.2.3"
    assert items(result, "clients")["codex"]["edition"] == "cli"


def test_unavailable_profile_does_not_claim_base_clients_effectively_configured(project):
    root, _ = project
    (root / "ai-dlc.toml").write_text("schema=4\n", encoding="utf-8")
    config, _, _ = enroll(project)
    (config / "enrollment.toml").write_text("[SECRET-invalid", encoding="utf-8")
    result = collect(project)
    assert all(c["configured"] == "unknown" for c in result["clients"])


def test_auth_presence_and_excluded_project_commands_do_not_change_identity(project):
    root, home = project
    template = 'schema=4\n[roles]\ntracker="linear"\nagent-client=[]\n[providers.linear]\ntoken_env="PRIVATE_TOKEN"\n[checks.commands]\ncheck="{command}"\n'
    (root / "ai-dlc.toml").write_text(template.format(command="SECRET-one"), encoding="utf-8")
    first = collect_report(root, home=home, environ={"PATH": "", "PRIVATE_TOKEN": "secret"})
    (root / "ai-dlc.toml").write_text(template.format(command="SECRET-two"), encoding="utf-8")
    second = collect(project)
    assert first["auth"][0]["credential_presence"] == "present"
    assert second["auth"][0]["credential_presence"] == "missing"
    for key in ("configuration_identity", "observation_identity"):
        assert first[key] == second[key]


def test_explicit_client_pin_overrides_default_without_conflict(project):
    (project[0] / "ai-dlc.toml").write_text(
        'schema=4\n[roles]\nagent-client=["codex"]\n[agents.clients.codex]\nversion="0.155.0"\n',
        encoding="utf-8",
    )
    result = collect(project)
    assert items(result, "clients")["codex"]["version"]["intended"] == "0.155.0"
    assert items(result, "runtimes")["codex"]["version"]["intended"] == "0.155.0"
    assert not any(l["reason_code"] == "conflicting-declarations" for l in result["limitations"])


def test_independent_source_pin_survives_missing_cache(project):
    config, _, _ = enroll(project)
    lock = tomllib.loads((config / "enrollment.toml").read_text(encoding="utf-8"))
    lock["sources"] = [
        {
            "id": "team-docs",
            "git": "https://SECRET-source",
            "ref": "SECRET-ref",
            "resolved_commit": "b" * 40,
            "content_sha256": "c" * 64,
        }
    ]
    (config / "enrollment.toml").write_text(tomli_w.dumps(lock), encoding="utf-8")
    result = collect(project)
    assert result["sources"][0]["id"] == "team-docs"
    assert result["sources"][0]["commit"] == "b" * 40
    assert result["sources"][0]["state"] == "missing"
    assert result["sources"][0]["content_sha256"] is None
    assert "SECRET" not in json.dumps(result)


def test_native_alias_cannot_replace_instruction_observation(project):
    (project[0] / "ai-dlc.toml").write_text(
        'schema=4\n[roles]\nagent-client=["codex"]\n[agents]\nskills=[]\nservers=[{id="agents", command="tool"}]\n',
        encoding="utf-8",
    )
    result = collect(project)
    assert any(
        g["kind"] == "instruction" and g["id"] == "agents" and g["state"] == "missing"
        for g in result["project"]["guidance"]
    )
    assert any(
        g["kind"] == "native-server" and g["native_server"]["alias"] == "agents"
        for g in result["project"]["guidance"]
    )


@pytest.mark.parametrize(
    "failed_client,failed_prefix,other_client,other_prefix",
    [
        ("claude-code", ".claude", "codex", ".agents"),
        ("codex", ".agents", "claude-code", ".claude"),
    ],
)
@pytest.mark.parametrize("failure", ["missing", "mismatch"])
def test_skill_failures_only_mark_the_owning_client_unrendered(
    project, failed_client, failed_prefix, other_client, other_prefix, failure
):
    root, _ = project
    (root / "ai-dlc.toml").write_text(
        'schema=4\n[roles]\nagent-client=["codex", "claude-code"]\n'
        '[agents]\nskills=["day-start"]\n',
        encoding="utf-8",
    )
    body = "intact but freshness unknown\n"
    digest = hashlib.sha256(body.encode()).hexdigest()
    for name in ("AGENTS.md", "CLAUDE.md"):
        (root / name).write_text(
            f"<!-- ai-dlc:begin {digest} -->\n{body}<!-- ai-dlc:end -->",
            encoding="utf-8",
        )
    other_skill = root / other_prefix / "skills/day-start/SKILL.md"
    other_skill.parent.mkdir(parents=True)
    other_skill.write_text("present but freshness unknown", encoding="utf-8")
    if failure == "mismatch":
        relative = f"{failed_prefix}/skills/day-start/SKILL.md"
        failed_skill = root / relative
        failed_skill.parent.mkdir(parents=True)
        failed_skill.write_text("locally modified skill", encoding="utf-8")
        (root / ".ai-dlc").mkdir()
        (root / ".ai-dlc/agent-ownership.json").write_text(
            json.dumps({"schema": 2, "files": {relative: "a" * 64}}), encoding="utf-8"
        )

    result = collect(project)
    clients = items(result, "clients")
    assert clients[failed_client]["rendered"] == "no"
    assert clients[other_client]["rendered"] == "unknown"
    assert clients[other_client]["reasons"]["rendered"] == "not-assessed"
    skill = next(g for g in result["project"]["guidance"] if g["id"] == "skill.day-start")
    assert skill["state"] == failure
    assert completeness(result) == (False, False)


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="POSIX named pipes required")
@pytest.mark.parametrize(
    "location,relative,field",
    [
        ("project", "ai-dlc.toml", "project"),
        ("project", ".mise.toml", "runtimes"),
        ("home", ".config/ai-dlc/enrollment.toml", "profile"),
        ("project", "AGENTS.md", "project.guidance"),
        ("project", ".ai-dlc/agent-ownership.json", "project.guidance"),
        ("project", ".ai-dlc/providers/github.md", "project.guidance"),
        ("project", ".agents/skills/day-start/SKILL.md", "project.guidance"),
    ],
)
def test_special_metadata_is_refused_without_hanging_collection(project, location, relative, field):
    root, home = project
    target = (root if location == "project" else home) / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.unlink(missing_ok=True)
    os.mkfifo(target)
    # subprocess.run kills and waits for its child on TimeoutExpired. A blocking
    # regression fails promptly without leaving a reader or hanging the suite.
    script = """
import json, sys
from pathlib import Path
from ai_dlc.environment.report import collect_report
print(json.dumps(collect_report(Path(sys.argv[1]), home=Path(sys.argv[2]), environ={"PATH": ""})))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script, str(root), str(home)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=3,
        check=True,
    )
    result = json.loads(completed.stdout)
    assert any(item["field"] == field for item in result["limitations"])
    assert result["engine"]["current_process"]["package_version"] is not None
    assert str(root) not in completed.stdout and str(home) not in completed.stdout
    if relative == "ai-dlc.toml":
        assert result["project"]["state"] == "unknown"
    else:
        assert result["project"]["roles"] == [
            {"role": "scm", "provider": "github", "component": "github"}
        ]
    if relative == "AGENTS.md":
        assert (
            next(g for g in result["project"]["guidance"] if g["id"] == "agents")["state"]
            == "unknown"
        )
    assert completeness(result) == (False, False)


def test_regular_metadata_utf8_and_size_bound_are_preserved(tmp_path):
    from ai_dlc.environment.report import _read

    path = tmp_path / "metadata"
    for content in (b"", "caf\u00e9\n".encode("utf-8"), b"x" * (1024 * 1024)):
        path.write_bytes(content)
        assert _read(path) == content.decode("utf-8")
    path.write_bytes(b"x" * (1024 * 1024 + 1))
    with pytest.raises(ValueError, match="exceeds report inspection bound"):
        _read(path)


@pytest.mark.skipif(os.name != "posix", reason="Unprivileged POSIX symlink fixture")
def test_collection_preserves_project_root_alias_and_regular_config_symlink(project):
    root, home = project
    original = collect(project)
    target = root / "project-settings.toml"
    (root / "ai-dlc.toml").rename(target)
    (root / "ai-dlc.toml").symlink_to(target.name)
    alias = root.parent / "project-alias"
    alias.symlink_to(root, target_is_directory=True)
    result = collect_report(alias, home=home, environ={"PATH": ""})
    assert result["configuration_identity"] == original["configuration_identity"]
    assert result["observation_identity"] == original["observation_identity"]


@pytest.mark.parametrize("newline", [b"\r\n", b"\r"], ids=["crlf", "cr"])
@pytest.mark.parametrize("modified", [False, True], ids=["intact", "modified"])
def test_managed_guidance_uses_renderer_newline_contract(project, newline, modified):
    root, _ = project
    (root / "ai-dlc.toml").write_text(
        'schema=4\n[roles]\nagent-client=["codex"]\n[agents]\nskills=[]\n',
        encoding="utf-8",
    )
    body = b"managed instructions\nsecond line\n"
    digest = hashlib.sha256(body).hexdigest().encode("ascii")
    observed = body.replace(b"second", b"edited") if modified else body
    content = b"<!-- ai-dlc:begin " + digest + b" -->\n" + observed + b"<!-- ai-dlc:end -->\n"
    (root / "AGENTS.md").write_bytes(content.replace(b"\n", newline))
    result = collect(project)
    guidance = next(g for g in result["project"]["guidance"] if g["id"] == "agents")
    assert guidance["state"] == ("mismatch" if modified else "unknown")
    assert items(result, "clients")["codex"]["rendered"] == ("no" if modified else "unknown")


@pytest.mark.parametrize("recorded_raw", [True, False], ids=["raw-digest", "normalized-digest"])
def test_owned_guidance_integrity_retains_raw_newline_bytes(project, recorded_raw):
    root, _ = project
    relative = ".ai-dlc/providers/github.md"
    content = b"owned provider instructions\r\nsecond line\r\n"
    path = root / relative
    path.parent.mkdir(parents=True)
    path.write_bytes(content)
    digest_input = content if recorded_raw else content.replace(b"\r\n", b"\n")
    (root / ".ai-dlc/agent-ownership.json").write_text(
        json.dumps({"schema": 2, "files": {relative: hashlib.sha256(digest_input).hexdigest()}}),
        encoding="utf-8",
    )
    result = collect(project)
    guidance = next(g for g in result["project"]["guidance"] if g["id"] == "provider.github")
    assert guidance["state"] == ("unknown" if recorded_raw else "mismatch")
