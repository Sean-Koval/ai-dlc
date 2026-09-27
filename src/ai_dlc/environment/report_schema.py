"""Closed, safe environment report records and deterministic, scoped identities.

Reason/state literals below are the collection contract. Reasons have exactly the
listed nullable/status keys, with None for known values. Unknown IDs use None and
identifier-redacted (a scoped limitation for records without reasons). These
unsigned identities establish consistency, never authenticity of observations.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Annotated, Any, Literal, NoReturn

from pydantic import BaseModel, ConfigDict, Field, ValidationError

MAX_BYTES = 1024 * 1024
MAX_DEPTH = 12
SAFE_ERROR = "Invalid effective environment report."
Reason = Literal[
    "not-applicable",
    "not-assessed",
    "not-found",
    "identifier-redacted",
    "provenance-unavailable",
    "safe-digest-unavailable",
    "unsupported-version",
    "unsupported-platform",
    "conflicting-declarations",
    "invalid-configuration",
    "collection-failed",
    "cache-missing",
    "cache-corrupt",
    "probe-timeout",
    "probe-failed",
    "output-limit",
    "excluded-fields",
    "dirty-source",
    "guidance-mismatch",
    "evidence-stale",
]
ObservationState = Literal["observed", "missing", "unknown", "unsupported"]
Assessment = Literal["yes", "no", "unknown", "not-applicable"]
OS = Literal["linux", "macos", "windows"]
Architecture = Literal["x86_64", "arm64", "x86", "arm"]
Shell = Literal["sh", "bash", "zsh", "fish", "powershell", "cmd", "nushell"]
Identifier = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,63}$")]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Revision = Annotated[str, Field(pattern=r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")]
Version = Annotated[str, Field(max_length=64, pattern=r"^[0-9]+(?:\.[0-9]+)*$")]
Constraint = Annotated[
    str,
    Field(
        max_length=64,
        pattern=r"^(?:(?:==|>=|>|<=|<)?[0-9]+(?:\.[0-9]+)*)(?:,(?:==|>=|>|<=|<)[0-9]+(?:\.[0-9]+)*)*$",
    ),
]
LogicalField = Annotated[str, Field(max_length=256, pattern=r"^[a-z0-9][a-z0-9._-]*$")]
Timestamp = Annotated[
    str,
    Field(
        max_length=32,
        pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z$",
    ),
]


class _Record(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class _EngineObservation(_Record):
    package_version: Version | None
    installation_kind: Literal["release", "source", "unknown"]
    source_revision: Revision | None
    source_dirty: bool | None
    artifact_sha256: Digest | None
    state: ObservationState
    reasons: dict[str, Reason | None]


class _Engine(_Record):
    package_version: Version | None
    installation_kind: Literal["release", "source", "unknown"]
    source_revision: Revision | None
    source_dirty: bool | None
    artifact_sha256: Digest | None
    current_process: _EngineObservation
    path_selected: _EngineObservation


class _Platform(_Record):
    os: OS | None
    architecture: Architecture | None
    shell_family: Shell | None
    reasons: dict[str, Reason | None]


class _Source(_Record):
    id: Identifier | None
    commit: Revision | None
    content_sha256: Digest | None
    state: Literal["known", "unknown", "missing", "not-applicable"]
    reasons: dict[str, Reason | None]


class _Version(_Record):
    intended: Constraint | None
    observed: Version | None
    state: ObservationState
    reason: Reason | None


class _Runtime(_Record):
    id: Identifier | None
    required: bool
    version: _Version


class _Client(_Record):
    id: Identifier | None
    edition: Identifier | None
    version: _Version
    configured: Assessment
    rendered: Assessment
    recognized: Assessment
    authenticated: Assessment
    reasons: dict[str, Reason | None]


class _Support(_Record):
    os: Annotated[list[OS], Field(max_length=3)] | None
    architecture: Annotated[list[Architecture], Field(max_length=4)] | None
    shell_family: Annotated[list[Shell], Field(max_length=7)] | None


class _Component(_Record):
    id: Identifier | None
    platform_support: _Support


class _Role(_Record):
    role: Literal["scm", "tracker", "specs", "knowledge", "deploy"]
    provider: Identifier | None
    component: Identifier | None


class _NativeServer(_Record):
    alias: Identifier | None
    provider: Identifier | None
    transport: Literal["stdio", "http", "sse"] | None
    recipe_identity: Digest | None
    reasons: dict[str, Reason | None]


class _Guidance(_Record):
    id: Identifier | None
    kind: Literal["instruction", "skill", "provider", "native-server"]
    expected_sha256: Digest | None
    observed_sha256: Digest | None
    state: Literal["match", "mismatch", "missing", "unknown"]
    reasons: dict[str, Reason | None]
    native_server: _NativeServer | None


class _Project(_Record):
    engine_constraint: Constraint | None
    roles: list[_Role] = Field(max_length=5)
    components: list[_Component] = Field(max_length=128)
    client_ids: list[Identifier | None] = Field(max_length=16)
    configuration_sha256: Digest | None
    guidance: list[_Guidance] = Field(max_length=512)
    state: Literal["known", "unknown", "missing"]
    reasons: dict[str, Reason | None]


class _Evidence(_Record):
    configuration_identity: Digest
    observation_identity: Digest


class _Auth(_Record):
    kind: Literal["provider", "client"]
    id: Identifier | None
    credential_presence: Literal["present", "missing", "unknown"]
    verification: Literal["verified", "failed", "not-assessed", "stale"]
    verified_at: Timestamp | None
    evidence_identity: _Evidence | None
    reasons: dict[str, Reason | None]


class _Limitation(_Record):
    field: LogicalField
    reason_code: Reason
    required: bool


class _Report(_Record):
    schema_version: Literal[1]
    observed_at: Timestamp
    engine: _Engine
    platform: _Platform
    profile: _Source
    sources: list[_Source] = Field(max_length=16)
    runtimes: list[_Runtime] = Field(max_length=128)
    clients: list[_Client] = Field(max_length=16)
    project: _Project
    auth: list[_Auth] = Field(max_length=128)
    limitations: list[_Limitation] = Field(max_length=1024)
    configuration_identity: Digest | None
    observation_identity: Digest | None


def _fail() -> NoReturn:
    raise ValueError(SAFE_ERROR)


def _bounded(value: Any, depth: int = 0) -> None:
    if depth > MAX_DEPTH:
        _fail()
    if type(value) is dict:
        for key, child in value.items():
            if type(key) is not str:
                _fail()
            _bounded(child, depth + 1)
    elif type(value) is list:
        for child in value:
            _bounded(child, depth + 1)
    elif value is not None and type(value) not in (str, bool, int):
        _fail()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _reasons(record: dict, keys: tuple[str, ...], *, unconstrained: bool = False) -> None:
    if set(record["reasons"]) != set(keys):
        _fail()
    for key in keys:
        unknown = record[key] is None or record[key] == "unknown"
        reason = record["reasons"][key]
        if unconstrained and key == "engine_constraint" and record[key] is None:
            continue
        if unknown != (reason is not None):
            _fail()
        if (
            key in ("id", "alias", "provider")
            and record[key] is None
            and reason not in ("identifier-redacted", "not-applicable")
        ):
            _fail()


def _sort_unique(records: list, keys: tuple[str, ...] = ("id",)) -> None:
    def key(record: Any) -> tuple:
        return (
            tuple(record.get(k) or "" for k in keys)
            if isinstance(record, dict)
            else (record or "",)
        )

    if len({key(record) for record in records}) != len(records):
        _fail()
    records.sort(key=key)


def _check_records(report: dict) -> None:
    datetime.fromisoformat(report["observed_at"])
    engine = report["engine"]
    for key in (
        "package_version",
        "installation_kind",
        "source_revision",
        "source_dirty",
        "artifact_sha256",
    ):
        if engine[key] != engine["current_process"][key]:
            _fail()
    for side in ("current_process", "path_selected"):
        _reasons(
            engine[side], ("package_version", "source_revision", "source_dirty", "artifact_sha256")
        )
    _reasons(report["platform"], ("os", "architecture", "shell_family"))
    for source in [report["profile"], *report["sources"]]:
        _reasons(source, ("id", "commit", "content_sha256"))
        if source["state"] == "not-applicable" and (
            source is not report["profile"]
            or any(source[k] is not None for k in ("id", "commit", "content_sha256"))
        ):
            _fail()
    for record in [*report["runtimes"], *report["clients"]]:
        version = record["version"]
        if (version["state"] == "observed") != (version["observed"] is not None):
            _fail()
        if (version["state"] == "observed") != (version["reason"] is None):
            _fail()
    for client in report["clients"]:
        _reasons(client, ("id", "edition", "configured", "rendered", "recognized", "authenticated"))
    project = report["project"]
    _reasons(project, ("engine_constraint",), unconstrained=True)
    for guidance in project["guidance"]:
        _reasons(guidance, ("id", "expected_sha256", "observed_sha256"))
        if (guidance["kind"] == "native-server") != (guidance["native_server"] is not None):
            _fail()
        if guidance["native_server"] is not None:
            _reasons(
                guidance["native_server"], ("alias", "provider", "transport", "recipe_identity")
            )
        if guidance["state"] == "match" and (
            guidance["expected_sha256"] is None
            or guidance["expected_sha256"] != guidance["observed_sha256"]
        ):
            _fail()
        if (
            guidance["state"] == "mismatch"
            and guidance["expected_sha256"] is not None
            and guidance["expected_sha256"] == guidance["observed_sha256"]
        ):
            _fail()
    for auth in report["auth"]:
        _reasons(auth, ("id", "verified_at", "evidence_identity"))
        if auth["verified_at"] is not None:
            datetime.fromisoformat(auth["verified_at"])
        if auth["verification"] in ("verified", "failed") and (
            auth["verified_at"] is None or auth["evidence_identity"] is None
        ):
            _fail()
    for collection in ("sources", "runtimes", "clients"):
        _sort_unique(report[collection])
    for collection in ("components", "guidance", "client_ids"):
        _sort_unique(project[collection])
    _sort_unique(project["roles"], ("role",))
    _sort_unique(report["auth"], ("kind", "id"))
    if sum(item["id"] is None for item in report["auth"]) > 1:
        _fail()
    _sort_unique(report["limitations"], ("field", "reason_code"))
    if project["client_ids"] != [client["id"] for client in report["clients"]]:
        _fail()
    for field, records, keys in (
        ("runtimes", report["runtimes"], ("id",)),
        ("project.components", project["components"], ("id",)),
        ("project.roles", project["roles"], ("provider", "component")),
    ):
        if any(item[key] is None for item in records for key in keys) and not any(
            limitation["field"] == field and limitation["reason_code"] == "identifier-redacted"
            for limitation in report["limitations"]
        ):
            _fail()
    for component in project["components"]:
        for values in component["platform_support"].values():
            if values is not None:
                _sort_unique(values)


def _pick(record: dict, *keys: str) -> dict:
    return {key: record[key] for key in keys}


def _identities(report: dict) -> tuple[str, str, str]:
    project = report["project"]
    desired_project = _pick(project, "engine_constraint", "roles", "components", "client_ids")
    desired_project["guidance"] = [
        {
            **_pick(item, "id", "kind", "expected_sha256"),
            "native_server": None
            if item["native_server"] is None
            else _pick(item["native_server"], "alias", "provider", "transport", "recipe_identity"),
        }
        for item in project["guidance"]
    ]
    project_digest = _digest(desired_project)
    desired = {
        "project": desired_project,
        "profile": _pick(report["profile"], "id", "commit", "content_sha256"),
        "sources": [_pick(item, "id", "commit", "content_sha256") for item in report["sources"]],
        "runtimes": [
            {**_pick(item, "id", "required"), "intended": item["version"]["intended"]}
            for item in report["runtimes"]
        ],
        "clients": [
            {"id": item["id"], "intended": item["version"]["intended"]}
            for item in report["clients"]
        ],
    }
    configuration = _digest(desired)
    observed = {
        "configuration_identity": configuration,
        "engine": {
            key: _pick(
                report["engine"][key],
                "package_version",
                "installation_kind",
                "source_revision",
                "source_dirty",
                "artifact_sha256",
                "state",
            )
            for key in ("current_process", "path_selected")
        },
        "platform": _pick(report["platform"], "os", "architecture", "shell_family"),
        "runtimes": [
            {"id": item["id"], **_pick(item["version"], "observed", "state")}
            for item in report["runtimes"]
        ],
        "clients": [
            {
                **_pick(item, "id", "edition", "configured", "rendered"),
                **_pick(item["version"], "observed", "state"),
            }
            for item in report["clients"]
        ],
        "guidance": [_pick(item, "id", "observed_sha256", "state") for item in project["guidance"]],
    }
    return project_digest, configuration, _digest(observed)


def _validated(payload: dict, *, finalize: bool) -> dict:
    try:
        _bounded(payload)
        if len(_canonical(payload)) > MAX_BYTES or type(payload.get("schema_version")) is not int:
            _fail()
        report = _Report.model_validate(payload).model_dump()
        _check_records(report)
        project, configuration, observation = _identities(report)
        actual = (
            report["project"]["configuration_sha256"],
            report["configuration_identity"],
            report["observation_identity"],
        )
        if not finalize and actual != (project, configuration, observation):
            _fail()
        report["project"]["configuration_sha256"] = project
        report["configuration_identity"] = configuration
        report["observation_identity"] = observation
        for auth in report["auth"]:
            if auth["verification"] in ("verified", "failed") and (
                auth["evidence_identity"]
                != {"configuration_identity": configuration, "observation_identity": observation}
                or not all(_coverage(report))
            ):
                _fail()
        if len(_canonical(report)) > MAX_BYTES:
            _fail()
        return report
    except (ValidationError, ValueError, TypeError, AttributeError, RecursionError, OverflowError):
        raise ValueError(SAFE_ERROR) from None


def finalize_report(payload: dict) -> dict:
    """Validate a projected payload, sort its sets and calculate all three digests."""
    return _validated(payload, finalize=True)


def _object(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            _fail()
        result[key] = value
    return result


def parse_report(raw: bytes) -> dict:
    """Import only bounded UTF-8 JSON with unique keys and consistent identities."""
    try:
        if type(raw) is not bytes or len(raw) > MAX_BYTES:
            _fail()
        value = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_object, parse_constant=lambda _: _fail()
        )
        return _validated(value, finalize=False)
    except (ValueError, TypeError, RecursionError, OverflowError):
        raise ValueError(SAFE_ERROR) from None


def report_bytes(report: dict) -> bytes:
    """Serialize a fully validated report in canonical order."""
    return _canonical(_validated(report, finalize=False))


def engine_known(record: dict) -> bool:
    """Whether the observed engine has reproducible code identity."""
    if record["state"] != "observed" or record["package_version"] is None:
        return False
    if record["installation_kind"] == "source":
        return record["source_revision"] is not None and record["source_dirty"] is False
    return record["installation_kind"] == "release" and record["artifact_sha256"] is not None


def version_satisfies(version: str, constraint: str | None) -> bool:
    """Compare numeric dotted versions, padding absent trailing segments with zero."""
    if constraint is None:
        return True
    actual = tuple(int(part) for part in version.split("."))
    for clause in constraint.split(","):
        match = re.fullmatch(r"(==|>=|>|<=|<)?([0-9]+(?:\.[0-9]+)*)", clause)
        if match is None:
            _fail()
        operator, expected_text = match.groups()
        expected = tuple(int(part) for part in expected_text.split("."))
        width = max(len(actual), len(expected))
        left, right = (
            actual + (0,) * (width - len(actual)),
            expected + (0,) * (width - len(expected)),
        )
        if not {
            None: left == right,
            "==": left == right,
            ">=": left >= right,
            ">": left > right,
            "<=": left <= right,
            "<": left < right,
        }[operator]:
            return False
    return True


def completeness(report: dict) -> tuple[bool, bool]:
    """Derive coverage from fields and failed scopes; optional unknowns stay visible."""
    return _coverage(_validated(report, finalize=False))


def _coverage(report: dict) -> tuple[bool, bool]:
    project = report["project"]
    config = project["state"] == "known" and project["reasons"]["engine_constraint"] in (
        None,
        "not-applicable",
    )
    config &= all(
        source["state"] == "known"
        and all(source[key] is not None for key in ("id", "commit", "content_sha256"))
        for source in report["sources"]
    )
    profile = report["profile"]
    config &= profile["state"] == "not-applicable" or (
        profile["state"] == "known"
        and all(profile[key] is not None for key in ("id", "commit", "content_sha256"))
    )
    config &= all(
        item["id"] is not None
        for item in [*project["components"], *report["runtimes"], *report["clients"]]
    )
    config &= all(
        role["provider"] is not None and role["component"] is not None for role in project["roles"]
    )
    config &= all(
        item["id"] is not None
        and item["expected_sha256"] is not None
        and (
            item["native_server"] is None
            or all(
                item["native_server"][key] is not None
                for key in ("alias", "provider", "transport", "recipe_identity")
            )
        )
        for item in project["guidance"]
    )
    # Failure of a collection/declaration scope is not made optional by its flag.
    scope_failures = {
        "invalid-configuration",
        "unsupported-version",
        "collection-failed",
        "cache-missing",
        "cache-corrupt",
        "conflicting-declarations",
        "identifier-redacted",
    }
    config &= not any(
        item["reason_code"] in scope_failures
        and item["field"].split(".")[0] in {"project", "profile", "sources", "runtimes", "clients"}
        for item in report["limitations"]
    )
    observation = config and all(
        engine_known(report["engine"][side]) for side in ("current_process", "path_selected")
    )
    observation &= all(
        report["platform"][key] is not None for key in ("os", "architecture", "shell_family")
    )
    observation &= all(
        item["version"]["observed"] is not None and item["version"]["state"] == "observed"
        for item in report["runtimes"]
        if item["required"]
    )
    observation &= all(
        item["edition"] is not None
        and item["version"]["observed"] is not None
        and item["configured"] in ("yes", "no")
        and item["rendered"] in ("yes", "no")
        for item in report["clients"]
    )
    observation &= all(
        item["state"] == "match" and item["observed_sha256"] is not None
        for item in project["guidance"]
    )
    return bool(config), bool(observation)
