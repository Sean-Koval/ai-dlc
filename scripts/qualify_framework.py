"""Validate qualification records without executing steps or authenticating live claims."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from pathlib import Path, PurePosixPath
from typing import Annotated, Any, Literal, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    model_validator,
)


def _nonblank(value: str) -> str:
    if not value.strip():
        raise ValueError("text must not be blank")
    return value


Text = Annotated[str, AfterValidator(_nonblank)]
Revision = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
Digest = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
ImageDigest = Annotated[str, StringConstraints(pattern=r"^sha256:[0-9a-f]{64}$")]
EvidenceKind = Literal["fixture", "live-local", "live-container", "live-hosted"]
Result = Literal["passed", "failed", "unavailable", "not-run"]

CATALOG = {
    "Q01-setup": "Prepare the declared revision and independently scoped local bindings.",
    "Q01-repeat-setup": "Repeat setup at the same revision without duplicate owned assets.",
    "Q01-authored-preservation": "Refuse authored conflicts while preserving original bytes.",
    "Q01-offline-restart": "Read selected pinned guidance offline from a new process.",
    "Q01-failed-update": "Fail a staged update, preserve authored content and report recovery state.",
    "Q02-provider-cycle": "Use shared lifecycle services for new work on the selected actual adapter.",
    "Q02-capabilities": "Report the configured adapter's capabilities and refuse unsupported transitions.",
    "Q02-existing-bindings": "Keep prior work bound while new work uses another selected adapter.",
    "Q03-handoff": "A fresh client session derives the next action from saved artifacts alone.",
}
LOCAL_TARGET = "native-macos-arm64"
CONTAINER_TARGET = "container-ubuntu2404-arm64"


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Environment(Record):
    os: Text | None
    version: Text | None
    architecture: Text | None
    isolation: Literal[
        "planned",
        "existing-host",
        "clean-clone",
        "isolated-runtime",
        "container",
        "factory-clean",
        "hosted",
    ]
    image_digest: ImageDigest | None
    container_id: Text | None
    inherited_tools: list[Text]


class Provider(Record):
    kind: Literal["github-issues", "jira-cloud", "plane", "linear"]
    alias: Text
    site: Text
    project: Text


class Evidence(Record):
    path: Text
    sha256: Digest
    kind: EvidenceKind
    producer: Text
    method: Text


class Scenario(Record):
    scenario_id: Text
    target_id: Text
    commit: Revision | None
    profile_revision: Revision | None
    bundle_revisions: dict[Text, Revision]
    environment: Environment
    harness_name: Text | None
    harness_version: Text | None
    provider: Provider | None
    steps: Annotated[list[Text], Field(min_length=1, max_length=100)]
    expected: Text
    observed: str
    classification: EvidenceKind | None
    result: Result
    evidence: Annotated[list[Evidence], Field(max_length=32)]
    limitations: list[Text]

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if bool(self.harness_name) != bool(self.harness_version):
            raise ValueError("harness name and version must be provided together")
        if self.scenario_id not in CATALOG:
            raise ValueError("unknown scenario_id")
        if any(item.kind != self.classification for item in self.evidence):
            raise ValueError(
                "evidence classes must match the record; split mixed evidence into separate records"
            )
        if self.result == "passed" and (
            not self.observed.strip() or not self.evidence or self.commit is None
        ):
            raise ValueError("passed observations require a revision, observation and evidence")
        if self.result == "failed" and not self.observed.strip():
            raise ValueError("failed observations require an observed failure")
        if self.result in {"unavailable", "not-run"} and not self.limitations:
            raise ValueError(
                "unavailable/not-run records require an explicit reason in limitations"
            )
        if self.classification is None and (self.evidence or self.result in {"passed", "failed"}):
            raise ValueError("performed observations require a classification")
        if self.classification and self.classification.startswith("live-"):
            environment = self.environment
            if not all([environment.os, environment.version, environment.architecture]):
                raise ValueError("declared live evidence requires actual environment metadata")
            if self.classification == "live-container":
                if (
                    environment.isolation != "container"
                    or not environment.image_digest
                    or not environment.container_id
                ):
                    raise ValueError(
                        "live-container requires container isolation, image digest and container identity"
                    )
            elif self.classification == "live-hosted":
                if environment.isolation != "hosted":
                    raise ValueError("live-hosted requires hosted isolation")
            elif environment.isolation in {"container", "hosted", "planned"}:
                raise ValueError("live-local contradicts the declared isolation")
        if self.result == "passed" and self.classification != "fixture":
            environment = self.environment
            if self.target_id == LOCAL_TARGET and (
                self.classification != "live-local"
                or environment.os not in {"Darwin", "macOS"}
                or environment.architecture not in {"arm64", "aarch64"}
            ):
                raise ValueError("native target requires matching macOS arm64 live-local metadata")
            if self.target_id == CONTAINER_TARGET and (
                self.classification != "live-container"
                or environment.os not in {"Linux", "Ubuntu"}
                or not (environment.version or "").startswith("24.04")
                or environment.architecture not in {"arm64", "aarch64"}
            ):
                raise ValueError(
                    "container target requires matching Ubuntu24.04 arm64 live-container metadata"
                )
        if self.result == "passed":
            if self.scenario_id == "Q03-handoff" and not (
                self.harness_name and self.harness_version
            ):
                raise ValueError("a passed handoff needs an actual harness name and version")
            if self.scenario_id == "Q02-provider-cycle" and self.provider is None:
                raise ValueError(
                    "a passed provider cycle needs an explicit adapter and destination"
                )
        return self


class Report(Record):
    schema_version: Literal[1] = Field(alias="schema")
    run_id: Text
    scenarios: Annotated[list[Scenario], Field(min_length=1, max_length=200)]

    @model_validator(mode="before")
    @classmethod
    def schema_kind(cls, data: Any) -> Any:
        if isinstance(data, dict) and type(data.get("schema")) is not int:
            raise ValueError("schema must be integer 1")
        return data

    @model_validator(mode="after")
    def unique(self) -> Self:
        keys = [(row.scenario_id, row.target_id) for row in self.scenarios]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate scenario_id/target_id record")
        if sum(len(row.evidence) for row in self.scenarios) > 128:
            raise ValueError("report exceeds 128 evidence references")
        return self


def _read_confined(root: Path, relative: str, limit: int) -> bytes:
    """Read regular files through directory descriptors; do not follow path links."""
    path = PurePosixPath(relative)
    if (
        path.is_absolute()
        or "\\" in relative
        or not path.parts
        or ".." in path.parts
        or path.as_posix() != relative
    ):
        raise ValueError(
            "evidence paths must be normalized relative paths inside the report directory"
        )
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptor = os.open(root, flags)
    try:
        for part in path.parts[:-1]:
            following = os.open(part, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = following
        file_descriptor = os.open(
            path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor
        )
    finally:
        os.close(descriptor)
    with os.fdopen(file_descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise ValueError("report/evidence must be a regular file within the size limit")
        content = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
        if len(content) > limit or (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ):
            raise ValueError("report/evidence changed while reading or exceeds the size limit")
        return content


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def validate_report(path: Path) -> dict:
    root = path.parent.resolve()
    raw = json.loads(
        _read_confined(root, path.name, 2 * 1024 * 1024), object_pairs_hook=_unique_object
    )
    report = Report.model_validate(raw)
    for row in report.scenarios:
        for artifact in row.evidence:
            content = _read_confined(root, artifact.path, 20 * 1024 * 1024)
            if hashlib.sha256(content).hexdigest() != artifact.sha256:
                raise ValueError("evidence digest mismatch")
    live_rows = [
        row
        for row in report.scenarios
        if row.result == "passed" and row.classification and row.classification.startswith("live-")
    ]
    live_slots = {(row.scenario_id, row.target_id) for row in live_rows}
    required_setup = [
        (case, target)
        for case in CATALOG
        if case.startswith("Q01-")
        for target in [LOCAL_TARGET, CONTAINER_TARGET]
    ]
    missing = [
        {"scenario_id": case, "target_id": target}
        for case, target in required_setup
        if (case, target) not in live_slots
    ]
    adapters = sorted(
        {
            row.provider.kind
            for row in live_rows
            if row.scenario_id == "Q02-provider-cycle" and row.provider
        }
    )
    handoffs = [row.target_id for row in live_rows if row.scenario_id == "Q03-handoff"]
    return {
        "schema": 1,
        "run_id": report.run_id,
        "structurally_valid": True,
        "live_authenticated": False,
        "qualification_complete": False,
        "human_review_required": True,
        "scenarios": [row.model_dump(mode="json") for row in report.scenarios],
        "requirements": {
            "Q-01": {
                "status": "unmet" if missing else "pending-review",
                "missing_reported_live_slots": missing,
            },
            "Q-02": {
                "status": "pending-review" if len(adapters) >= 2 else "unmet",
                "reported_live_adapters": adapters,
                "review_obligation": "Two actual adapters plus preserved bindings and shared lifecycle; GitHub Project modes are one adapter.",
            },
            "Q-03": {
                "status": "pending-review" if handoffs else "unmet",
                "reported_live_handoffs": handoffs,
                "review_obligation": "Review true fresh-session inputs/transcripts for every required client/target.",
            },
        },
        "limitations": [
            "File hashes and declarations do not authenticate live claims.",
            "No work-finish, platform-qualification or factory-clean claim follows from validation.",
        ],
    }


def protocol() -> dict:
    rows = []
    for case, expected in CATALOG.items():
        if case.startswith("Q01-"):
            targets = [LOCAL_TARGET, CONTAINER_TARGET]
        elif case == "Q02-provider-cycle":
            targets = ["github", "jira"]
        elif case == "Q03-handoff":
            targets = ["claude-code", "antigravity"]
        else:
            targets = ["planned"]
        for target in targets:
            rows.append(
                {
                    "scenario_id": case,
                    "target_id": target,
                    "commit": None,
                    "profile_revision": None,
                    "bundle_revisions": {},
                    "environment": {
                        "os": None,
                        "version": None,
                        "architecture": None,
                        "isolation": "planned",
                        "image_digest": None,
                        "container_id": None,
                        "inherited_tools": [],
                    },
                    "harness_name": None,
                    "harness_version": None,
                    "provider": None,
                    "steps": [
                        "Follow the reviewed framework qualification protocol; record actual actions."
                    ],
                    "expected": expected,
                    "observed": "",
                    "classification": None,
                    "result": "not-run",
                    "evidence": [],
                    "limitations": [
                        "Not executed; revisions, environment, credentials and client availability must be recorded, not inferred."
                    ],
                }
            )
    return {"schema": 1, "run_id": "pending-qualification", "scenarios": rows}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--schema", action="store_true")
    mode.add_argument("--protocol", action="store_true")
    mode.add_argument("--validate", type=Path, metavar="REPORT.json")
    args = parser.parse_args(argv)
    try:
        if args.schema:
            output = Report.model_json_schema()
        elif args.protocol:
            output = protocol()
        else:
            output = validate_report(args.validate)
    except ValidationError as error:
        output = {
            "structurally_valid": False,
            "errors": error.errors(include_input=False, include_context=False, include_url=False),
        }
    except ValueError as error:
        output = {"structurally_valid": False, "errors": [str(error)]}
    except OSError:
        output = {
            "structurally_valid": False,
            "errors": ["Report or evidence file is unavailable, linked, or unreadable."],
        }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 1 if output.get("structurally_valid") is False else 0


if __name__ == "__main__":
    raise SystemExit(main())
