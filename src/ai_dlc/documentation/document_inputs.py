"""Typed MCP inputs for the documentation review tools.

The shapes mirror what ``prepare_review``, ``inventory_documents`` and the
disposition checks read and write, so an MCP client sees a full input schema
instead of a bare object. Strict mode keeps JSON values as they were sent (no
``"1"`` turning into ``1``), because the services compare packets and citations
exactly. They stay plain dictionaries after validation.

A packet is the server's own output passed back, so an unknown key in it is
refused. Inputs an agent writes (dispositions and reviews) drop unknown keys,
as the services always have.
"""

from __future__ import annotations

from typing import Literal, NotRequired, TypedDict

from pydantic import ConfigDict, with_config

EXACT = ConfigDict(strict=True, extra="forbid")
WRITTEN = ConfigDict(strict=True, extra="ignore")

Outcome = Literal["updated", "reviewed-no-change", "no-impact"]
Category = Literal[
    "contradiction",
    "unsupported-claim",
    "obsolete-instruction",
    "unnecessary-repetition",
    "missing-explanation",
    "vague-prose",
    "useful-repetition",
]
Suggestion = Literal["revise", "consolidate", "retain", "investigate"]


@with_config(WRITTEN)
class Disposition(TypedDict):
    """One reviewed documentation target: what happened to it and why."""

    target: str
    outcome: Outcome
    reason: str


@with_config(EXACT)
class PathReason(TypedDict):
    """A path left out of review, and the reason."""

    path: str
    reason: str


@with_config(EXACT)
class DocumentBody(TypedDict):
    """One bounded local document or evidence body, as ``project_docs_review`` returns it."""

    path: str
    content: str
    digest: str
    start_line: int
    end_line: int


@with_config(EXACT)
class Inventory(TypedDict):
    """The document inventory a packet built from ``source="inventory"`` carries."""

    schema: int
    documents: list[str]
    excluded: list[PathReason]
    omitted: list[PathReason]
    constraints: list[str]


@with_config(EXACT)
class ReviewPacket(TypedDict):
    """The packet ``project_docs_review`` returned, passed back unchanged."""

    schema: int
    base: str
    selected: list[str]
    max_bytes: int
    catalog_digest: str
    documents: list[DocumentBody]
    evidence: list[DocumentBody]
    omitted: list[PathReason]
    unreviewed: list[str]
    constraints: list[str]
    rubric: list[str]
    source: NotRequired[Literal["inventory"]]
    inventory: NotRequired[Inventory]
    snapshot: str


@with_config(WRITTEN)
class Citation(TypedDict):
    """A quoted passage: ``quote`` must equal lines ``start_line`` to ``end_line``."""

    path: str
    start_line: int
    end_line: int
    quote: str


@with_config(WRITTEN)
class Finding(TypedDict):
    """One grounded review finding."""

    category: Category
    suggested_disposition: Suggestion
    uncertainty: str
    rationale: str
    target: Citation
    supporting: list[Citation]


@with_config(WRITTEN)
class Review(TypedDict):
    """A harness review of one packet: coverage and grounded findings."""

    schema: int
    packet_snapshot: str
    reviewed: list[str]
    unreviewed: list[str]
    findings: list[Finding]
