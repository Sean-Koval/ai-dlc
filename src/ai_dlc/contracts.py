"""Versioned provider wire contracts. Completion is a workflow service operation."""

from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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
        "publish",
        "get",
        "search",
        "list_changed",
        "propose",
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


# The normalized lifecycle vocabulary trackers share. A provider supports a subset;
# in_review and needs_decision exist only where a tracker maps statuses to them.
TRANSITION_STATE = (
    "Normalized target state: in_progress, in_review, needs_decision or closed. "
    "A provider refuses a state it does not map."
)
ITEM_STATE = (
    "Normalized state: open, in_progress, in_review, needs_decision, closed, cancelled or unknown."
)


class Transition(Read):
    state: str = Field(min_length=1, description=TRANSITION_STATE)
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
    state: str = Field(min_length=1, description=ITEM_STATE)


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
    draft: bool = False


class Publish(Payload):
    """One reviewed note to one page (ADR 0003): create without ``page_id``, else update.

    ``expected_version`` is the version the note recorded; a provider refuses when the
    page's current version differs instead of overwriting a teammate's edit.
    """

    site: str = Field(min_length=1)
    space: str = Field(min_length=1)
    parent: str | None = None
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)
    page_id: str | None = None
    expected_version: int | None = Field(default=None, ge=1)
    operation_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def _update_needs_version(self) -> "Publish":
        if (self.page_id is None) != (self.expected_version is None):
            raise ValueError("an update names page_id and expected_version together")
        return self


class PublishResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    page_id: str = Field(min_length=1)
    version: int = Field(ge=1)
    url: str = Field(min_length=1)


class RecordGet(Payload):
    """One knowledge record by id or alias."""

    id: str = Field(min_length=1)


class RecordSearch(Payload):
    """Filter records; every given filter must match. ``text`` also reads bodies."""

    type: str | None = None
    scope: str | None = None
    labels: list[str] = Field(default_factory=list)
    status: str | None = None
    text: str | None = None


class RecordsChanged(Payload):
    """Record files changed since a revision of the knowledge store."""

    since: str = Field(min_length=1)


class ProposedRecord(Payload):
    path: str = Field(min_length=1, description="repository-relative .md path")
    text: str = Field(min_length=1, description="the whole record file")


class Propose(Payload):
    """Write records on a new branch and open a draft pull request; never main."""

    records: list[ProposedRecord] = Field(min_length=1)
    branch: str = Field(min_length=1)
    title: str = Field(min_length=1)
    body: str = ""


class RecordItem(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str = Field(min_length=1)
    path: str = Field(min_length=1)
    header: dict


class RecordResult(RecordItem):
    body: str


class RecordsFound(BaseModel):
    model_config = ConfigDict(extra="allow")
    items: list[RecordItem]
    invalid: list[dict] = Field(default_factory=list)


class ChangedFile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str = Field(min_length=1)
    change: Literal["added", "modified", "deleted"]
    id: str | None = None


class RecordsChangedResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    since: str = Field(min_length=1)
    head: str = Field(min_length=1)
    changed: list[ChangedFile]


class ProposeResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    branch: str = Field(min_length=1)
    commit: str = Field(min_length=1)
    files: list[str]
    pull_request: dict


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
        "publish": Publish,
        "get": RecordGet,
        "search": RecordSearch,
        "list_changed": RecordsChanged,
        "propose": Propose,
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
    "publish": PublishResult,
    "get": RecordResult,
    "search": RecordsFound,
    "list_changed": RecordsChangedResult,
    "propose": ProposeResult,
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
            "knowledge": {
                "mandatory": ["get", "search"],
                "optional": ["append", "list_changed", "propose", "publish"],
            },
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
