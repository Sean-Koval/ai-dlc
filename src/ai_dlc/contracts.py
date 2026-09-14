"""Versioned provider wire contracts. Completion is a workflow service operation."""

from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Request(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    operation: Literal[
        "capabilities",
        "prepare",
        "reconcile_closed",
        "create",
        "find",
        "read",
        "link",
        "transition",
        "current",
        "merged",
        "ci",
        "deployment",
        "append",
        "pull_request_create",
    ]
    payload: dict
    operation_id: str | None = None


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Create(Payload):
    title: str = Field(min_length=1)
    correlation: str = Field(min_length=1)
    operation_id: str = Field(min_length=1)
    body: str = ""


class Find(Payload):
    correlation: str = Field(min_length=1)


class Read(Payload):
    reference: str = Field(min_length=1)


class Prepare(Read):
    operation_id: str = Field(min_length=1)


class Link(Read):
    url: str = Field(min_length=1)
    operation_id: str = Field(min_length=1)


class Transition(Read):
    state: str = Field(min_length=1)
    operation_id: str = Field(min_length=1)


class Capabilities(Payload):
    pass


class LifecycleCapabilities(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    in_progress: bool
    closed: bool


class CapabilityResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal[1] = Field(alias="schema")
    lifecycle: LifecycleCapabilities
    optional_operations: list[str]

    @field_validator("schema_version", mode="before")
    @classmethod
    def exact_schema_one(cls, value):
        if type(value) is not int or value != 1:
            raise ValueError("Capability schema must be the integer 1")
        return value


PAYLOADS = {
    "capabilities": Capabilities,
    "prepare": Prepare,
    "reconcile_closed": Prepare,
    "create": Create,
    "find": Find,
    "read": Read,
    "link": Link,
    "transition": Transition,
}


class Item(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str = Field(min_length=1)
    url: str = Field(min_length=1)
    state: str = Field(min_length=1)


class Found(BaseModel):
    items: list[Item]


class Current(Payload):
    work: dict
    revision: str | None = None


class Revision(Payload):
    sha: str = Field(min_length=1)


class Append(Payload):
    path: str = Field(min_length=1)
    body: str = Field(min_length=1)
    operation_id: str = Field(min_length=1)


class CurrentResult(BaseModel):
    current: bool
    revision: str | None = None
    archive: str = Field(min_length=1)


class MergedResult(BaseModel):
    sha: str = Field(min_length=1)
    pr: dict


class CIResult(BaseModel):
    sha: str = Field(min_length=1)
    run_id: int | str
    receipt: dict


class DeploymentResult(BaseModel):
    sha: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    deployment_id: int | str


class AppendResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    path: str = Field(min_length=1)


class PullRequestCreate(Payload):
    title: str = Field(min_length=1)
    body: str = ""
    base: str = Field(min_length=1)
    head: str = Field(min_length=1)


class PullRequestResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    url: str = Field(min_length=1)
    number: int = Field(ge=1)


PAYLOADS.update(
    {
        "current": Current,
        "merged": Read,
        "ci": Revision,
        "deployment": Revision,
        "append": Append,
        "pull_request_create": PullRequestCreate,
    }
)
RESPONSES = {
    "capabilities": CapabilityResult,
    "prepare": Item,
    "reconcile_closed": Item,
    "create": Item,
    "find": Found,
    "read": Item,
    "link": Item,
    "transition": Item,
    "current": CurrentResult,
    "merged": MergedResult,
    "ci": CIResult,
    "deployment": DeploymentResult,
    "append": AppendResult,
    "pull_request_create": PullRequestResult,
}


OPERATIONS = set(PAYLOADS)

FAILURE_STATUSES = frozenset(
    {
        "blocked",
        "failed",
        "refused",
        "unavailable",
        "runtime-unavailable",
        "rolled-back",
        "recovery-required",
    }
)
VERDICT_KEYS = ("valid", "ready", "passed", "clean")


class ServiceResult(BaseModel):
    """Envelope every application service result satisfies; see docs/architecture.md."""

    model_config = ConfigDict(extra="allow")

    status: str | None = Field(
        default=None,
        description="Canonical outcome. Members of FAILURE_STATUSES are failures; any other value succeeded.",
    )
    valid: bool | None = Field(
        default=None, description="Legacy verdict key; authoritative when present."
    )
    ready: bool | None = Field(
        default=None, description="Legacy verdict key; authoritative when present."
    )
    passed: bool | None = Field(
        default=None, description="Legacy verdict key; authoritative when present."
    )
    clean: bool | None = Field(
        default=None, description="Legacy verdict key; authoritative when present."
    )


def succeeded(result: Mapping[str, Any]) -> bool:
    """Whether a service result reports success under the shared envelope."""
    for key in VERDICT_KEYS:
        if key in result:
            return bool(result[key])
    status = result.get("status")
    return not (isinstance(status, str) and status in FAILURE_STATUSES)


def validate_request(operation, payload):
    if operation not in OPERATIONS:
        raise ValueError(f"Unsupported provider operation: {operation}")
    payload = PAYLOADS[operation].model_validate(payload).model_dump()
    return Request(operation=operation, payload=payload, operation_id=payload.get("operation_id"))


def validate_response(operation, result):
    return RESPONSES[operation].model_validate(result).model_dump(by_alias=True)


def manifest():
    return {
        "schema": 1,
        "contract": "ai-dlc.providers/v1",
        "roles": {
            "tracker": {
                "mandatory": ["create", "find", "read", "transition"],
                "optional": ["capabilities", "link", "prepare", "reconcile_closed"],
            },
            "specs": {"mandatory": ["current"], "optional": []},
            "scm": {"mandatory": ["merged", "ci"], "optional": ["pull_request_create"]},
            "deploy": {"mandatory": ["deployment"], "optional": []},
            "knowledge": {"mandatory": ["append"], "optional": []},
        },
        "operations": {
            op: {
                "required": op in {"create", "find", "read", "transition"},
                "request": Request.model_json_schema(),
                "payload": PAYLOADS[op].model_json_schema(),
                "response": RESPONSES[op].model_json_schema(),
            }
            for op in sorted(OPERATIONS)
        },
    }
