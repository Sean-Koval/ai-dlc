"""Versioned provider wire contracts. Completion is a workflow service operation."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Request(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    operation: Literal[
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


class Link(Read):
    url: str = Field(min_length=1)
    operation_id: str = Field(min_length=1)


class Transition(Read):
    state: str = Field(min_length=1)
    operation_id: str = Field(min_length=1)


PAYLOADS = {"create": Create, "find": Find, "read": Read, "link": Link, "transition": Transition}


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


PAYLOADS.update(
    {"current": Current, "merged": Read, "ci": Revision, "deployment": Revision, "append": Append}
)
RESPONSES = {
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
}


OPERATIONS = set(PAYLOADS)


def validate_request(operation, payload):
    if operation not in OPERATIONS:
        raise ValueError(f"Unsupported provider operation: {operation}")
    payload = PAYLOADS[operation].model_validate(payload).model_dump()
    return Request(operation=operation, payload=payload, operation_id=payload.get("operation_id"))


def validate_response(operation, result):
    return RESPONSES[operation].model_validate(result).model_dump()


def manifest():
    return {
        "schema": 1,
        "contract": "ai-dlc.providers/v1",
        "roles": {
            "tracker": {
                "mandatory": ["create", "find", "read", "transition"],
                "optional": ["link"],
            },
            "specs": {"mandatory": ["current"], "optional": []},
            "scm": {"mandatory": ["merged", "ci"], "optional": []},
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
