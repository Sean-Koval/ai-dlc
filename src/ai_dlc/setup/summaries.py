"""Short text summaries of readiness, doctor and onboarding results (KAN-364).

A person at a terminal gets a one-line verdict, then one line per blocking item with
its next action, most important first. The JSON results are not changed: these
functions only read them. Missing provider settings collapse into one item per
provider, whose next action is ``ai-dlc provider connect <alias>``.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

from ai_dlc.setup.readiness import BLOCKING_DIMENSIONS

# Install tools first; configuration and credentials depend on them, guidance last.
DIMENSION_ORDER = ("tool", "configuration", "credential", "lifecycle-adapter", "guidance")
_PROVIDER_FIELD = re.compile(r"^Configure providers\.(?P<alias>[^.\s]+)\.(?P<field>[^\s]+?)\.?$")
_JSON_HINT = "Run with --json for the full report."

Item = dict[str, str]


def _item(subject: str, action: str) -> Item:
    return {"subject": subject, "action": action}


def _connect(alias: str, fields: list[str], root_option: str) -> Item:
    return _item(
        f"{alias} configuration",
        f"Run `ai-dlc provider connect {alias}{root_option}`; it sets " + ", ".join(fields) + ".",
    )


def _root_option(root: str | None) -> str:
    return f" --root {root}" if root not in (None, "", ".") else ""


def readiness_items(checks: Iterable[Mapping[str, Any]], root: str | None = None) -> list[Item]:
    """Blocking readiness rows as items, provider settings collapsed per provider."""
    blocking = [
        check
        for check in checks
        if check.get("status") != "ready" and check.get("dimension") in BLOCKING_DIMENSIONS
    ]
    rank = {name: index for index, name in enumerate(DIMENSION_ORDER)}
    blocking.sort(key=lambda check: rank.get(str(check.get("dimension")), len(rank)))
    items: list[Item] = []
    fields: dict[str, list[str]] = {}
    for check in blocking:
        match = _PROVIDER_FIELD.match(str(check.get("next_action", "")))
        if check.get("dimension") == "configuration" and match:
            alias = match["alias"]
            if alias not in fields:
                fields[alias] = []
                items.append({"subject": f"{alias} configuration", "action": "", "connect": alias})
            fields[alias].append(match["field"])
            continue
        items.append(
            _item(f"{check.get('component')} {check.get('dimension')}", str(check["next_action"]))
        )
    option = _root_option(root)
    return [
        _connect(item["connect"], fields[item["connect"]], option) if "connect" in item else item
        for item in items
    ]


def _merge(items: list[Item]) -> list[Item]:
    """One line per next action: subjects sharing an action are named together."""
    merged: dict[str, list[str]] = {}
    for item in items:
        merged.setdefault(item["action"], [])
        if item["subject"] not in merged[item["action"]]:
            merged[item["action"]].append(item["subject"])
    return [_item(", ".join(subjects), action) for action, subjects in merged.items()]


def _render(verdict: str, items: list[Item], extra: list[str] | None = None) -> str:
    lines = [verdict]
    lines.extend(f"- {item['subject']}: {item['action']}" for item in items)
    lines.extend(extra or [])
    lines.append(_JSON_HINT)
    return "\n".join(lines) + "\n"


def _verdict(ready: bool, items: list[Item], what: str) -> str:
    """``what`` is ``"project"`` or ``"machine"``."""
    if ready:
        return f"Ready: nothing blocks this {what}."
    count = len(items)
    noun = "item" if count == 1 else "items"
    place = "on" if what == "machine" else "in"
    return f"Not ready: {count} {noun} to fix {place} this {what}, most important first."


def render_readiness(result: Mapping[str, Any], root: str | None = None) -> str:
    items = _merge(readiness_items(result.get("checks", []), root))
    return _render(_verdict(bool(result.get("ready")), items, "project"), items)


def render_preflight(result: Mapping[str, Any]) -> str:
    """The machine preflight that doctor runs outside an adopted repository (KAN-363)."""
    items = _merge(
        [
            _item(str(check["id"]), str(check["next_action"]))
            for check in result.get("checks", [])
            if check.get("required") and check.get("status") != "ready"
        ]
    )
    verdict = _verdict(bool(result.get("ready")), items, "machine")
    extra = [] if items else [str(result.get("next", ""))]
    return _render(verdict, items, [line for line in extra if line])


def doctor_items(result: Mapping[str, Any], root: str | None = None) -> list[Item]:
    """Blocking doctor findings, most important first, each with one next action."""
    items = [
        _item(tool, f"Install {tool}, then rerun `ai-dlc doctor`.")
        for tool in result.get("missing", [])
    ]
    items.extend(
        _item("runtime", f"Run `ai-dlc project setup` to install {drift}.")
        if "@" in str(drift)
        else _item("runtime", f"{str(drift)[0].upper()}{str(drift)[1:]}.")
        for drift in result.get("runtime_drift", [])
    )
    for signin in result.get("signins", []):
        text = str(signin)
        action = f"Run `{text}`." if not text[:1].isupper() else f"{text}."
        items.append(_item("sign-in", action))
    checks = list((result.get("project_readiness") or {}).get("checks", []))
    known = " ".join(str(check.get("next_action", "")) for check in checks)
    for gap in result.get("configuration", []):
        # Doctor's own gaps join readiness's configuration rows, unless one names them.
        key = str(gap).split(" ", 1)[0]
        if key not in known:
            checks.append(
                {
                    "component": "project",
                    "dimension": "configuration",
                    "status": "missing",
                    "next_action": f"Set {str(gap).removesuffix(' is required')} in ai-dlc.toml.",
                }
            )
    items.extend(readiness_items(checks, root))
    conflicts = list(result.get("managed_conflicts", []))
    if conflicts:
        shown = ", ".join(str(name) for name in conflicts[:3])
        more = f" and {len(conflicts) - 3} more" if len(conflicts) > 3 else ""
        items.append(
            _item(
                "managed files",
                f"{shown}{more} differ from the rendered guidance; review them, then run "
                f"`ai-dlc agents render{_root_option(root)} --apply`.",
            )
        )
    hooks = result.get("hooks") or {}
    if hooks and not hooks.get("ready", True):
        for reason in hooks.get("unavailable", []) or ["client hooks are not ready"]:
            items.append(_item("hooks", f"{reason}."))
    for entry in [*result.get("provider_health", []), *result.get("provider_capabilities", [])]:
        if not entry.get("ready", True):
            items.append(_item(str(entry.get("provider")), f"{entry.get('reason')}."))
    agents = result.get("user_agents") or {}
    if agents and not agents.get("clean", True):
        items.append(_item("user agents", "Resolve the user-level agent configuration conflicts."))
    machine = result.get("machine_status") or {}
    if machine and not machine.get("ready", True) and machine.get("next"):
        items.append(_item("machine", str(machine["next"])))
    return _merge(items)


def render_doctor(result: Mapping[str, Any], root: str | None = None) -> str:
    if result.get("mode") == "machine-preflight":
        return render_preflight(result)
    items = doctor_items(result, root)
    return _render(_verdict(bool(result.get("ready")), items, "project"), items)


def render_onboarding(plan: Mapping[str, Any]) -> str:
    """The plan's verdict, its findings, then the ordered commands to run."""
    state = str(plan.get("state", "unknown"))
    findings = [
        _item(str(finding.get("component")), str(finding.get("reason")))
        for finding in plan.get("findings", [])
    ]
    verdict = (
        "Actionable: run the commands below in order."
        if state == "actionable"
        else f"Not actionable ({state}): {len(findings)} "
        + ("finding" if len(findings) == 1 else "findings")
        + " to resolve first."
    )
    lines = [verdict]
    lines.extend(f"- {item['subject']}: {item['action']}" for item in findings)
    lines.append("Commands, in order ([review] = read its preview before running it):")
    for index, action in enumerate(plan.get("actions", []), start=1):
        argv = action.get("argv") or []
        command = " ".join(str(part) for part in argv) if argv else "(input required)"
        marker = "[review] " if action.get("requires_review") else ""
        effects = " ".join(str(effect) for effect in action.get("effects", []))
        lines.append(f"  {index}. {marker}{command}  # {action.get('id')}: {effects}")
    lines.append(_JSON_HINT)
    return "\n".join(lines) + "\n"
