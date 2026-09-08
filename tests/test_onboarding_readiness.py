"""Real prerequisite distinctions for the standard scaffold roles."""

import pytest

from ai_dlc.readiness import inspect_readiness


def inspect(tmp_path, config, *, gh=True):
    return inspect_readiness(
        tmp_path,
        config,
        environ={},
        probe=lambda commands: {"available": gh or "gh" not in commands},
    )


@pytest.mark.parametrize(
    "repository", [None, "", " ", "owner", "owner/repo/extra", "https://github.com/owner/repo"]
)
def test_missing_or_malformed_root_scm_identity_has_actionable_refusal(tmp_path, repository):
    config = {
        "roles": {"scm": "github"},
        "providers": {"github": {"repository": "ignored/substitute"}},
    }
    if repository is not None:
        config["scm"] = {"repository": repository}
    result = inspect(tmp_path, config)
    assert result["ready"] is False
    assert any(
        c["dimension"] == "configuration"
        and c["status"] == "missing"
        and "scm.repository" in c["next_action"]
        for c in result["checks"]
    )
    assert not any("no component" in c["reason"] for c in result["checks"])


def test_available_scm_prerequisites_never_claim_authenticated_or_live_ci(tmp_path):
    config = {"roles": {"scm": "github"}, "scm": {"repository": "owner/repository"}}
    result = inspect(tmp_path, config)
    assert result["ready"] is True
    assert result["qualification"] == "not-assessed"
    assert any(
        c["dimension"] == "provider-health" and c["status"] == "unverified"
        for c in result["checks"]
    )
    assert any(c["dimension"] == "tool" and c["status"] == "ready" for c in result["checks"])
    assert any(c["dimension"] == "guidance" and c["status"] == "ready" for c in result["checks"])
    # This is the actual runtime configuration contract; construction makes no API call.
    from ai_dlc.providers.scm import GitHubSCM

    assert GitHubSCM(tmp_path, config, environ={}).repo == "owner/repository"


def test_valid_scm_identity_does_not_hide_missing_gh(tmp_path):
    result = inspect(
        tmp_path, {"roles": {"scm": "github"}, "scm": {"repository": "owner/repo"}}, gh=False
    )
    assert result["ready"] is False
    assert any(c["dimension"] == "tool" and c["status"] == "missing" for c in result["checks"])


def test_disabled_deploy_is_explicitly_inactive_without_health_or_tool_requirements(tmp_path):
    result = inspect(tmp_path, {"roles": {"deploy": "none"}}, gh=False)
    assert result["ready"] is True
    assert result["qualification"] == "not-assessed"
    assert any(
        c["dimension"] == "activation" and c["status"] == "inactive" for c in result["checks"]
    )
    assert not any(c["dimension"] in {"tool", "provider-health"} for c in result["checks"])


@pytest.mark.parametrize(
    "role,provider",
    [("scm", "unknown"), ("deploy", "unknown"), ("tracker", "none"), ("tracker", "github")],
)
def test_unknown_and_role_incompatible_selections_stay_blocked(tmp_path, role, provider):
    result = inspect(tmp_path, {"roles": {role: provider}})
    assert result["ready"] is False
    assert any(c["status"] == "blocked" for c in result["checks"])


def test_synthetic_definition_uses_shared_runtime_requirements_and_inactive_metadata(
    tmp_path, monkeypatch
):
    from ai_dlc.provider_definitions import DEFINITIONS, ProviderDefinition, RuntimeRequirement

    monkeypatch.setitem(
        DEFINITIONS,
        "github",
        ProviderDefinition(
            "github",
            ("scm",),
            runtime_requirements=(
                RuntimeRequirement("scm.fixture", r"chosen", "chosen fixture value"),
            ),
            inactive=True,
        ),
    )
    result = inspect(tmp_path, {"roles": {"scm": "github"}, "scm": {"fixture": "wrong"}})
    assert result["ready"] is False
    assert any("scm.fixture" in c["next_action"] for c in result["checks"])
    assert any(c["status"] == "inactive" for c in result["checks"])
    assert not any(c["dimension"] == "provider-health" for c in result["checks"])


@pytest.mark.parametrize("kind", ["github-issues", "unknown"])
@pytest.mark.parametrize("role,component", [("scm", "github"), ("deploy", "none")])
def test_component_override_cannot_disguise_unknown_or_incompatible_kind(
    tmp_path, kind, role, component
):
    from ai_dlc.config import resolve_layers

    config = resolve_layers(
        [
            (
                "project",
                {
                    "schema": 4,
                    "roles": {role: "work-provider"},
                    "providers": {"work-provider": {"kind": kind, "component": component}},
                },
            )
        ]
    ).values
    result = inspect(tmp_path, config)
    assert result["ready"] is False
    assert any(c["status"] == "blocked" and "kind" in c["reason"] for c in result["checks"])
    assert not any(c["status"] == "inactive" for c in result["checks"])
    if component == "github":
        assert any("scm.repository" in c["next_action"] for c in result["checks"])


@pytest.mark.parametrize("role,kind", [("scm", "github"), ("deploy", "none")])
def test_legitimate_builtin_kind_aliases_remain_ready(tmp_path, role, kind):
    result = inspect(
        tmp_path,
        {
            "roles": {role: "work-provider"},
            "providers": {"work-provider": {"kind": kind, "component": kind}},
            "scm": {"repository": "owner/repo"},
        },
    )
    assert result["ready"] is True
    assert result["qualification"] == "not-assessed"


def test_existing_github_scm_runtime_alias_keeps_borrowed_requirements(tmp_path):
    from ai_dlc.providers import Registry
    from ai_dlc.providers.scm import GitHubSCM

    config = {
        "roles": {"scm": "work-scm"},
        "providers": {"work-scm": {"kind": "github-scm", "component": "github"}},
        "scm": {"repository": "owner/repo"},
    }
    assert isinstance(Registry(config, root=tmp_path, environ={}).get("work-scm"), GitHubSCM)
    assert inspect(tmp_path, config)["ready"] is True
    del config["scm"]
    result = inspect(tmp_path, config)
    assert result["ready"] is False
    assert any("scm.repository" in c["next_action"] for c in result["checks"])


@pytest.mark.parametrize("kind", ["executable", "python"])
def test_explicit_extension_borrowing_builtin_component_keeps_root_requirements(tmp_path, kind):
    config = {
        "roles": {"scm": "custom"},
        "providers": {"custom": {"kind": kind, "component": "github"}},
    }
    result = inspect(tmp_path, config)
    assert result["ready"] is False
    assert any("scm.repository" in c["next_action"] for c in result["checks"])
    config["scm"] = {"repository": "owner/repo"}
    result = inspect(tmp_path, config)
    assert result["ready"] is True
    assert any(
        c["dimension"] == "provider-health" and c["status"] == "unverified"
        for c in result["checks"]
    )


@pytest.mark.parametrize("kind", ["executable", "python"])
def test_active_extension_cannot_borrow_disabled_deployment_identity(tmp_path, kind):
    result = inspect(
        tmp_path,
        {
            "roles": {"deploy": "custom"},
            "providers": {"custom": {"kind": kind, "component": "none"}},
        },
    )
    assert result["ready"] is False
    assert any(c["status"] == "blocked" for c in result["checks"])
    assert not any(c["status"] == "inactive" for c in result["checks"])


@pytest.mark.parametrize(
    "kind", ["executable", "python", "custom-unverified", "github-deployment", "cloudflare"]
)
def test_custom_manifest_extension_contract_stays_available_without_loading_provider(
    tmp_path, kind, monkeypatch
):
    import hashlib
    import json

    from ai_dlc.providers import Registry

    def no_provider(*args, **kwargs):
        raise AssertionError("offline metadata inspection loaded provider code")

    monkeypatch.setattr(Registry, "get", no_provider)
    (tmp_path / "guidance.md").write_text("# Custom SCM guidance\n")
    role = "deploy" if kind in {"github-deployment", "cloudflare"} else "scm"
    manifest = json.dumps(
        {
            "schema": 1,
            "components": [
                {
                    "id": "custom-scm",
                    "roles": [role],
                    "modules": [],
                    "guidance": ["guidance.md"],
                    "required_config": ["workspace"],
                }
            ],
        }
    )
    (tmp_path / "component.json").write_text(manifest)
    config = {
        "roles": {role: "custom"},
        "scm": {"repository": "owner/repo"},
        "providers": {
            "custom": {
                "kind": kind,
                "component": "custom-scm",
                "workspace": "chosen",
                "component_manifest": "component.json",
                "component_manifest_sha256": hashlib.sha256(manifest.encode()).hexdigest(),
            }
        },
    }
    result = inspect(tmp_path, config)
    assert result["ready"] is True
    assert result["qualification"] == "not-assessed"
    assert any(
        c["dimension"] == "provider-health" and c["status"] == "unverified"
        for c in result["checks"]
    )


def test_existing_knowledge_runtime_alias_retains_vault_requirement(tmp_path):
    config = {
        "roles": {"knowledge": "notes"},
        "providers": {"notes": {"kind": "knowledge", "component": "obsidian"}},
        "paths": {"vault": str(tmp_path)},
    }
    assert inspect(tmp_path, config)["ready"] is True
    del config["paths"]
    assert inspect(tmp_path, config)["ready"] is False
