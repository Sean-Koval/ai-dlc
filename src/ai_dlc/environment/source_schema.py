"""Portable subscriptions and machine-local source pins."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SourceSubscription(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    git: str = Field(min_length=1)
    ref: str = Field(min_length=1)
    roles: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    layout: Literal["ai-dlc", "teamai"] = "ai-dlc"

    @field_validator("roles", "tags")
    @classmethod
    def selectors(cls, values: list[str]) -> list[str]:
        import re

        if len(set(values)) != len(values) or any(
            re.fullmatch(r"[a-z0-9][a-z0-9_-]*", value) is None for value in values
        ):
            raise ValueError("source roles and tags must be unique safe lowercase identifiers")
        return values


class SourceLock(SourceSubscription):
    resolved_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


def subscriptions(value: object) -> list[SourceSubscription]:
    if not isinstance(value, list):
        raise ValueError("sources must be a list of source subscriptions")  # noqa: TRY004 -- reject untrusted document content
    result = [SourceSubscription.model_validate(entry) for entry in value]
    if len({entry.id for entry in result}) != len(result):
        raise ValueError("sources must not contain duplicate IDs")
    if len(result) > 16:
        raise ValueError("sources must contain at most 16 subscriptions")
    return result
