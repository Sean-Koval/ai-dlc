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


# Trusted code registrations only: no project file can load an executable handler.
DEFINITIONS = {
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
