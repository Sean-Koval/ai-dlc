"""Pure offline comparison of validated safe environment reports.

Finding reasons and repair routes are closed constants; no input is interpreted
as a command, filesystem location or adapter recipe.
"""

from __future__ import annotations

import json
from typing import get_args

from .report_schema import (
    Reason,
    completeness,
    engine_known,
    parse_report,
    report_bytes,
    version_satisfies,
)

REASON_CODES = frozenset(get_args(Reason)) | frozenset(
    {
        "identity-unavailable",
        "identity-drift",
        "selection-drift",
        "dirty-source",
        "required-missing",
        "constraint-violation",
        "compatible-version",
        "compatibility-unknown",
        "supported-platform",
        "unsupported-platform",
        "guidance-drift",
        "client-not-configured",
        "authentication-difference",
        "authentication-failed",
        "optional-unavailable",
        "collection-incomplete",
    }
)
NEXT_ACTIONS = frozenset(
    {
        "project-workspace-check",
        "machine-enroll",
        "sources-sync",
        "project-check",
        "agents-render",
        "provider-doctor",
        "review-report",
    }
)


def compare_reports(left: dict, right: dict) -> dict:
    """Compare known fields independently; matching unknowns never establish parity."""
    left, right = (parse_report(report_bytes(value)) for value in (left, right))
    findings: list[dict] = []
    lc, lo = completeness(left)
    rc, ro = completeness(right)
    configuration_complete, observation_complete = lc and rc, lo and ro

    def add(field, a, b, classification, reason, action="project-check", *, required=True):
        nonlocal observation_complete
        if classification == "unknown" and required:
            observation_complete = False
        findings.append(
            {
                "field": field,
                "left": a,
                "right": b,
                "class": classification,
                "reason_code": reason,
                "next_action": action,
            }
        )

    def known(field, a, b, *, action="project-check", nullable=False):
        if not nullable and (a is None or b is None):
            add(field, a, b, "unknown", "identity-unavailable", action)
        elif a != b:
            add(field, a, b, "blocking", "identity-drift", action)

    def pairs(a, b, key="id"):
        la, rb = {item[key]: item for item in a}, {item[key]: item for item in b}
        for identifier in sorted(la.keys() | rb.keys(), key=lambda value: value or ""):
            yield identifier or "redacted", la.get(identifier), rb.get(identifier)

    for side in ("current_process", "path_selected"):
        a, b = left["engine"][side], right["engine"][side]
        field = f"engine.{side}"
        if not engine_known(a) or not engine_known(b):
            reason = (
                "dirty-source" if a["source_dirty"] or b["source_dirty"] else "identity-unavailable"
            )
            add(field, a["state"], b["state"], "unknown", reason, "project-workspace-check")
        for key in (
            "package_version",
            "installation_kind",
            "source_revision",
            "source_dirty",
            "artifact_sha256",
        ):
            # Independent known facts still expose drift in incomplete reports.
            if key == "installation_kind" and "unknown" in (a[key], b[key]):
                continue
            if a[key] is not None and b[key] is not None and a[key] != b[key]:
                if key == "source_dirty":
                    continue
                known(f"{field}.{key}", a[key], b[key], action="project-workspace-check")
        for report, engine in ((left, a), (right, b)):
            if engine["package_version"] is not None and not version_satisfies(
                engine["package_version"], report["project"]["engine_constraint"]
            ):
                add(
                    f"{field}.package_version",
                    a["package_version"],
                    b["package_version"],
                    "blocking",
                    "constraint-violation",
                    "project-workspace-check",
                )
                break

    for name, a, b in [("profile", left["profile"], right["profile"])]:
        if a["state"] == b["state"] == "not-applicable":
            continue
        if "not-applicable" in (a["state"], b["state"]):
            add(name, a["id"], b["id"], "blocking", "selection-drift", "machine-enroll")
        if a["state"] != "known" or b["state"] != "known":
            add(name, a["state"], b["state"], "unknown", "identity-unavailable", "machine-enroll")
        for key in ("id", "commit", "content_sha256"):
            known(f"{name}.{key}", a[key], b[key], action="machine-enroll")
    for identifier, a, b in pairs(left["sources"], right["sources"]):
        field = f"sources.{identifier}"
        if a is None or b is None:
            add(
                field,
                None if a is None else a["id"],
                None if b is None else b["id"],
                "blocking",
                "selection-drift",
                "sources-sync",
            )
            continue
        if a["state"] != "known" or b["state"] != "known":
            add(field, a["state"], b["state"], "unknown", "identity-unavailable", "sources-sync")
        for key in ("id", "commit", "content_sha256"):
            known(f"{field}.{key}", a[key], b[key], action="sources-sync")

    project_left, project_right = left["project"], right["project"]
    for key in ("engine_constraint", "roles", "components", "client_ids", "configuration_sha256"):
        known(f"project.{key}", project_left[key], project_right[key], nullable=True)
    if project_left["state"] != "known" or project_right["state"] != "known":
        add(
            "project",
            project_left["state"],
            project_right["state"],
            "unknown",
            "collection-incomplete",
        )

    for key in ("os", "architecture", "shell_family"):
        a, b = left["platform"][key], right["platform"][key]
        supports = [
            component["platform_support"][key]
            for report in (left, right)
            for component in report["project"]["components"]
        ]
        unsupported = any(
            values is not None
            and any(value is not None and value not in values for value in (a, b))
            for values in supports
        )
        if unsupported:
            add(f"platform.{key}", a, b, "blocking", "unsupported-platform")
        elif a is None or b is None:
            add(f"platform.{key}", a, b, "unknown", "identity-unavailable")
        elif a != b:
            if supports and all(
                values is not None and a in values and b in values for values in supports
            ):
                add(f"platform.{key}", a, b, "expected-platform", "supported-platform")
            else:
                add(f"platform.{key}", a, b, "unknown", "compatibility-unknown")

    for identifier, a, b in pairs(left["runtimes"], right["runtimes"]):
        field = f"runtimes.{identifier}"
        if a is None or b is None:
            add(
                field,
                None if a is None else a["id"],
                None if b is None else b["id"],
                "blocking",
                "selection-drift",
            )
            continue
        required = a["required"] or b["required"]
        known(f"{field}.required", a["required"], b["required"])
        av, bv = a["version"], b["version"]
        known(f"{field}.intended", av["intended"], bv["intended"], nullable=True)
        if any(item["required"] and item["version"]["state"] == "missing" for item in (a, b)):
            add(field, av["observed"], bv["observed"], "blocking", "required-missing")
        if any(
            item["required"]
            and item["version"]["observed"] is not None
            and not version_satisfies(item["version"]["observed"], item["version"]["intended"])
            for item in (a, b)
        ):
            add(field, av["observed"], bv["observed"], "blocking", "constraint-violation")
        if av["observed"] is None or bv["observed"] is None:
            add(
                f"{field}.observed",
                av["observed"],
                bv["observed"],
                "unknown",
                "identity-unavailable" if required else "optional-unavailable",
                required=required,
            )
        elif av["observed"] != bv["observed"]:
            compatible = (
                av["intended"] == bv["intended"]
                and av["intended"] is not None
                and all(version_satisfies(v["observed"], v["intended"]) for v in (av, bv))
            )
            add(
                f"{field}.observed",
                av["observed"],
                bv["observed"],
                "informational" if compatible else "unknown",
                "compatible-version" if compatible else "compatibility-unknown",
                required=required,
            )

    for identifier, a, b in pairs(left["clients"], right["clients"]):
        field = f"clients.{identifier}"
        if a is None or b is None:
            add(
                field,
                None if a is None else a["id"],
                None if b is None else b["id"],
                "blocking",
                "selection-drift",
                "agents-render",
            )
            continue
        known(f"{field}.edition", a["edition"], b["edition"], action="agents-render")
        known(
            f"{field}.intended", a["version"]["intended"], b["version"]["intended"], nullable=True
        )
        av, bv = a["version"]["observed"], b["version"]["observed"]
        if any(
            item["version"]["observed"] is not None
            and not version_satisfies(item["version"]["observed"], item["version"]["intended"])
            for item in (a, b)
        ):
            add(f"{field}.version", av, bv, "blocking", "constraint-violation")
        if av is None or bv is None or av != bv:
            add(f"{field}.version", av, bv, "unknown", "compatibility-unknown")
        for key in ("configured", "rendered"):
            if "no" in (a[key], b[key]):
                add(
                    f"{field}.{key}",
                    a[key],
                    b[key],
                    "blocking",
                    "client-not-configured",
                    "agents-render",
                )
            elif a[key] in ("unknown", "not-applicable") or b[key] in ("unknown", "not-applicable"):
                add(
                    f"{field}.{key}",
                    a[key],
                    b[key],
                    "unknown",
                    "identity-unavailable",
                    "agents-render",
                )
        for key in ("recognized", "authenticated"):
            if "unknown" in (a[key], b[key]):
                add(
                    f"{field}.{key}",
                    a[key],
                    b[key],
                    "unknown",
                    "optional-unavailable",
                    "provider-doctor",
                    required=False,
                )
            elif a[key] != b[key]:
                add(
                    f"{field}.{key}",
                    a[key],
                    b[key],
                    "informational",
                    "authentication-difference",
                    "provider-doctor",
                )

    for identifier, a, b in pairs(project_left["guidance"], project_right["guidance"]):
        field = f"project.guidance.{identifier}"
        if a is None or b is None:
            add(
                field,
                None if a is None else a["id"],
                None if b is None else b["id"],
                "blocking",
                "selection-drift",
                "agents-render",
            )
            continue
        if any(
            item["state"] in ("missing", "mismatch")
            or (
                item["expected_sha256"] is not None
                and item["observed_sha256"] is not None
                and item["expected_sha256"] != item["observed_sha256"]
            )
            for item in (a, b)
        ):
            add(field, a["state"], b["state"], "blocking", "guidance-drift", "agents-render")
        elif a["state"] != "match" or b["state"] != "match":
            add(field, a["state"], b["state"], "unknown", "identity-unavailable", "agents-render")
        for key in ("kind", "expected_sha256", "observed_sha256"):
            known(f"{field}.{key}", a[key], b[key], action="agents-render")
        if a["native_server"] is not None and b["native_server"] is not None:
            for key in ("alias", "provider", "transport", "recipe_identity"):
                known(
                    f"{field}.native_server.{key}",
                    a["native_server"][key],
                    b["native_server"][key],
                    action="agents-render",
                )

    # Authentication is a separate local/evidence dimension, never shared drift.
    auth_left = {(item["kind"], item["id"]): item for item in left["auth"]}
    auth_right = {(item["kind"], item["id"]): item for item in right["auth"]}
    for identity in sorted(
        auth_left.keys() | auth_right.keys(), key=lambda item: (item[0], item[1] or "")
    ):
        a, b = auth_left.get(identity), auth_right.get(identity)
        # Leading underscores cannot occur in valid IDs, so this marker is unambiguous.
        identifier = f"{identity[0]}.{identity[1] if identity[1] is not None else '_redacted'}"
        for key in ("credential_presence", "verification", "verified_at", "evidence_identity"):
            av, bv = a[key] if a else None, b[key] if b else None
            if key == "credential_presence" and "unknown" in (av, bv):
                add(
                    f"auth.{identifier}.{key}",
                    av,
                    bv,
                    "unknown",
                    "optional-unavailable",
                    "provider-doctor",
                    required=False,
                )
            elif av != bv or (key == "verification" and av == "failed"):
                add(
                    f"auth.{identifier}.{key}",
                    av,
                    bv,
                    "informational",
                    "authentication-failed"
                    if key == "verification" and "failed" in (av, bv)
                    else "authentication-difference",
                    "provider-doctor",
                )
    for report in (left, right):
        for limitation in report["limitations"]:
            if limitation["reason_code"] == "excluded-fields":
                continue
            add(
                limitation["field"],
                None,
                None,
                "unknown",
                limitation["reason_code"],
                "review-report",
                required=False,
            )
    # Identical limitations or independent per-side violations need one finding.
    findings = list({json.dumps(finding, sort_keys=True): finding for finding in findings}.values())
    findings.sort(key=lambda item: (item["field"], item["class"], item["reason_code"]))
    return {
        "schema_version": 1,
        "configuration_complete": configuration_complete,
        "observation_complete": bool(observation_complete),
        "findings": findings,
    }


def comparison_exit_code(result: dict) -> int:
    """Blocking drift or incomplete required coverage returns 1; otherwise 0."""
    return int(
        not result["configuration_complete"]
        or not result["observation_complete"]
        or any(finding["class"] == "blocking" for finding in result["findings"])
    )
