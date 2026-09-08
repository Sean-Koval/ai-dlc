"""Trusted connection capabilities, independent from lifecycle provider registration."""

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class ConnectionHandler:
    """Read-only discovery and pure patch selection; the service owns all writes."""

    discover: Callable[..., dict]
    configure: Callable[[dict, dict[str, str]], dict]


@dataclass(frozen=True)
class EnvironmentRequirement:
    """Trusted provider field naming a required local environment input."""

    field: str
    default: str | None = None
    when: tuple[str, str] | None = None


@dataclass(frozen=True)
class RuntimeRequirement:
    """Trusted root configuration path and its bounded full-match text contract."""

    path: str
    pattern: str
    description: str


@dataclass(frozen=True)
class ProviderDefinition:
    kind: str
    roles: tuple[str, ...]
    selection_keys: frozenset[str] = frozenset()
    handler: ConnectionHandler | None = None
    compatibility_connect: Callable[..., dict] | None = None
    aliases: bool = True
    boolean_keys: frozenset[str] = frozenset()
    scaffold_defaults: tuple[tuple[str, str], ...] = ()
    lifecycle_available: bool = True
    local_directory: str | None = None
    optional_viewer: str | None = None
    environment_requirements: tuple[EnvironmentRequirement, ...] = ()
    runtime_requirements: tuple[RuntimeRequirement, ...] = ()
    inactive: bool = False


def _linear(root, *, alias, environ, **options):
    from ai_dlc.provider_onboarding import connect_linear_provider

    return connect_linear_provider(root, environ=environ, **options)


def _github(root, *, alias, environ, **options):
    from ai_dlc.github_onboarding import connect_github_provider

    return connect_github_provider(root, alias=alias, environ=environ, **options)


def _jira_discover(config, alias, *, environ):
    from ai_dlc.jira_onboarding import discover

    return discover(config, alias, environ=environ)


def _jira_configure(discovery, selected):
    from ai_dlc.jira_onboarding import configure

    return configure(discovery, selected)


def _plane_discover(config, alias, *, environ):
    from ai_dlc.plane_onboarding import discover

    return discover(config, alias, environ=environ)


def _plane_configure(discovery, selected):
    from ai_dlc.plane_onboarding import configure

    return configure(discovery, selected)


# Trusted code registrations only: no project file can load an executable handler.
DEFINITIONS = {
    "github": ProviderDefinition(
        "github",
        ("scm",),
        runtime_requirements=(
            RuntimeRequirement("scm.repository", r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", "owner/repo"),
        ),
    ),
    "none": ProviderDefinition("none", ("deploy",), inactive=True),
    "obsidian": ProviderDefinition(
        "obsidian", ("knowledge",), local_directory="paths.vault", optional_viewer="obsidian"
    ),
    "plane": ProviderDefinition(
        "plane",
        ("tracker",),
        frozenset({"project", "open", "in_progress", "closed", "cancelled"}),
        handler=ConnectionHandler(_plane_discover, _plane_configure),
    ),
    "jira-cloud": ProviderDefinition(
        "jira-cloud",
        ("tracker",),
        frozenset(
            {
                "project",
                "issue_type",
                "open",
                "in_progress",
                "closed",
                "cancelled",
                "closed_resolution",
                "cancelled_resolution",
            }
        ),
        handler=ConnectionHandler(_jira_discover, _jira_configure),
        environment_requirements=(
            EnvironmentRequirement("token_env"),
            EnvironmentRequirement("email_env", when=("auth_mode", "personal_scoped_token_basic")),
        ),
    ),
    "linear": ProviderDefinition(
        "linear",
        ("tracker",),
        frozenset({"organization", "team", "in_progress", "closed"}),
        compatibility_connect=_linear,
        aliases=False,
        scaffold_defaults=(("token_env", "LINEAR_API_KEY"),),
        environment_requirements=(EnvironmentRequirement("token_env", default="LINEAR_API_KEY"),),
    ),
    "github-issues": ProviderDefinition(
        "github-issues",
        ("tracker",),
        frozenset(
            {
                "host",
                "repository",
                "project",
                "issues_only",
                "status_field",
                "open",
                "in_progress",
                "closed",
            }
        ),
        compatibility_connect=_github,
        boolean_keys=frozenset({"issues_only"}),
    ),
}
