"""Versioned provider wire contracts. Completion is a workflow service operation."""

from collections.abc import Mapping
from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator


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
        "update",
        "query",
        "comment",
        "current",
        "merged",
        "ci",
        "deployment",
        "append",
        "pull_request_create",
        "pull_requests",
        "get",
        "search",
        "list_changed",
        "propose",
        "upsert_page",
        "get_page_by_key",
        "list_children",
        "list_since",
        "fetch",
    ]
    payload: dict
    operation_id: str | None = None


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


LABELS = (
    "Native tracker labels to set. A provider that cannot write labels does not list "
    "update among its optional operations, and callers refuse labels before writing."
)


class Create(Payload):
    title: str = Field(min_length=1)
    correlation: str = Field(min_length=1)
    operation_id: str = Field(min_length=1)
    body: str = ""
    labels: list[str] = Field(default_factory=list, description=LABELS)


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


class Update(Read):
    """Replace the given fields of an open item; omitted fields stay as they are."""

    operation_id: str = Field(min_length=1)
    title: str | None = Field(default=None, min_length=1)
    body: str | None = None
    labels: list[str] | None = Field(default=None, description=LABELS)


class Query(Payload):
    """Read-only item search; every filter given must match."""

    text: str | None = Field(default=None, min_length=1)
    labels: list[str] = Field(default_factory=list)
    state: str | None = Field(default=None, description=ITEM_STATE)
    limit: int = Field(default=20, ge=1, le=50)


class Comment(Read):
    body: str = Field(min_length=1, description="Plain text; each non-blank line is one paragraph.")
    operation_id: str = Field(min_length=1)


class CommentResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str = Field(min_length=1)
    url: str = Field(min_length=1)


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
    "update": Update,
    "query": Query,
    "comment": Comment,
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


class RecordGet(Payload):
    """One knowledge record by id or alias."""

    id: str = Field(min_length=1)
    project: str | None = Field(
        default=None,
        description="customer project the caller works in; boundary: customer records "
        "of other projects are never returned",
    )


class RecordSearch(Payload):
    """Filter records; every given filter must match. ``text`` also reads bodies."""

    type: str | None = None
    scope: str | None = None
    labels: list[str] = Field(default_factory=list)
    status: str | None = None
    text: str | None = None
    project: str | None = Field(
        default=None,
        description="customer project the caller works in; boundary: customer records "
        "of other projects are never returned",
    )


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


class PullRequestsSince(Payload):
    """Pull requests opened at or after ``since``, newest first (``knowledge stats``)."""

    since: AwareDatetime
    limit: int = Field(default=200, ge=1, le=1000)


class PullRequestSummary(BaseModel):
    """One pull request as ``knowledge stats`` measures it; read-only, no bodies."""

    model_config = ConfigDict(extra="allow")
    number: int = Field(ge=1)
    title: str
    state: Literal["open", "merged", "closed"] = Field(
        description="closed means closed without merging"
    )
    created_at: AwareDatetime
    merged_at: AwareDatetime | None = None
    closed_at: AwareDatetime | None = None
    files: list[str] = Field(default_factory=list, description="repository-relative paths")
    first_commit: str | None = Field(default=None, description="the pull request's first commit")
    merge_commit: str | None = Field(default=None, description="the commit it merged as")
    first_push_checks: Literal["success", "failure", "pending", "none"] = Field(
        default="none",
        description="combined checks on the earliest pull request commit that has any",
    )


class PullRequestList(BaseModel):
    pull_requests: list[PullRequestSummary]


WIKI_KEY = r"^[A-Za-z0-9][A-Za-z0-9._:-]*$"


class UpsertPage(Payload):
    """Write one rendered page, found by ``key`` (KAN-430). Only ``knowledge render`` calls it.

    ``expected_version`` is the page's version as ``get_page_by_key`` read it, or null when
    no page has the key. A provider refuses when the page's current version differs, so a
    concurrent write is never overwritten.
    """

    key: str = Field(pattern=WIKI_KEY, description="stable page key, such as a record id")
    title: str = Field(min_length=1)
    body: str = Field(min_length=1, description="markdown")
    properties: dict[str, str] = Field(default_factory=dict)
    labels: list[str] = Field(default_factory=list)
    parent: str | None = Field(default=None, description="parent page key; null is the root")
    expected_version: int | None = Field(default=None, ge=1)
    operation_id: str = Field(min_length=1)


class PageKey(Payload):
    key: str = Field(pattern=WIKI_KEY)


class Children(Payload):
    parent: str | None = Field(default=None, description="parent page key; null is the root")


class Page(BaseModel):
    """A page's metadata. The wiki role never returns a page body."""

    model_config = ConfigDict(extra="allow")
    key: str = Field(min_length=1)
    page_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    version: int = Field(ge=1)
    rendered_version: int | None = Field(
        default=None, description="the version the last upsert wrote; differs after a hand edit"
    )
    properties: dict[str, str] = Field(default_factory=dict)
    labels: list[str] = Field(default_factory=list)
    url: str = Field(min_length=1)


class PageFound(BaseModel):
    model_config = ConfigDict(extra="allow")
    page: Page | None


class PageList(BaseModel):
    model_config = ConfigDict(extra="allow")
    pages: list[Page]


class TranscriptsSince(Payload):
    """Transcripts of meetings that started at or after ``since`` (the transcripts role)."""

    since: AwareDatetime


class TranscriptRef(Payload):
    id: str = Field(min_length=1, description="the provider's transcript id")


class TranscriptSummary(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str = Field(min_length=1, description="stable per provider; capture is idempotent by it")
    title: str = Field(min_length=1)
    start: AwareDatetime
    participants: list[str] = Field(default_factory=list, description="display names")
    emails: list[str] = Field(default_factory=list, description="routing only; never stored")
    url: str | None = None


class TranscriptList(BaseModel):
    model_config = ConfigDict(extra="allow")
    items: list[TranscriptSummary]


class Utterance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    speaker: str = Field(min_length=1)
    at: str = Field(pattern=r"^[0-9]{1,3}:[0-5][0-9]:[0-5][0-9]$", description="HH:MM:SS offset")
    text: str = Field(min_length=1)


class Transcript(TranscriptSummary):
    segments: list[Utterance] = Field(min_length=1)


PAYLOADS.update(
    {
        "current": Current,
        "merged": Read,
        "ci": Revision,
        "deployment": Revision,
        "append": Append,
        "pull_request_create": PullRequestCreate,
        "pull_requests": PullRequestsSince,
        "get": RecordGet,
        "search": RecordSearch,
        "list_changed": RecordsChanged,
        "propose": Propose,
        "upsert_page": UpsertPage,
        "get_page_by_key": PageKey,
        "list_children": Children,
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
    "update": Item,
    "query": Found,
    "comment": CommentResult,
    "current": CurrentResult,
    "merged": MergedResult,
    "ci": CIResult,
    "deployment": DeploymentResult,
    "append": AppendResult,
    "pull_request_create": PullRequestResult,
    "pull_requests": PullRequestList,
    "get": RecordResult,
    "search": RecordsFound,
    "list_changed": RecordsChangedResult,
    "propose": ProposeResult,
    "upsert_page": Page,
    "get_page_by_key": PageFound,
    "list_children": PageList,
}

PAYLOADS.update({"list_since": TranscriptsSince, "fetch": TranscriptRef})
RESPONSES.update({"list_since": TranscriptList, "fetch": Transcript})


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
                "optional": [
                    "capabilities",
                    "comment",
                    "link",
                    "prepare",
                    "query",
                    "reconcile_closed",
                    "update",
                ],
            },
            "specs": {"mandatory": ["current"], "optional": []},
            "scm": {
                "mandatory": ["merged", "ci"],
                "optional": ["pull_request_create", "pull_requests"],
            },
            "deploy": {"mandatory": ["deployment"], "optional": []},
            "knowledge": {
                "mandatory": ["get", "search"],
                "optional": ["append", "list_changed", "propose"],
            },
            "wiki": {
                "mandatory": ["upsert_page", "get_page_by_key", "list_children"],
                "optional": [],
            },
            "transcripts": {"mandatory": ["list_since", "fetch"], "optional": []},
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
