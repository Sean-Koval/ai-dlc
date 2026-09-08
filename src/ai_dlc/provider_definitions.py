"""Trusted connection capabilities, independent from lifecycle provider registration."""

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class ConnectionHandler:
    """Read-only discovery and pure patch selection; the service owns all writes."""

    discover: Callable[..., dict]
    configure: Callable[[dict, dict[str, str]], dict]


@dataclass(frozen=True)
class ProviderDefinition:
    kind: str
    roles: tuple[str, ...]
    selection_keys: frozenset[str] = frozenset()
    handler: ConnectionHandler | None = None
    compatibility_connect: Callable[..., dict] | None = None
    aliases: bool = True
    boolean_keys: frozenset[str] = frozenset()


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
    ),
    "linear": ProviderDefinition(
        "linear",
        ("tracker",),
        frozenset({"organization", "team", "in_progress", "closed"}),
        compatibility_connect=_linear,
        aliases=False,
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
