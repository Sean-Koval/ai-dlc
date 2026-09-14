"""CLI surface; workflow operations delegate to the same services as MCP."""

from __future__ import annotations

import json
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated

import typer

from ai_dlc.config import load_project, read_toml, resolve_files, resolve_runtime
from ai_dlc.contracts import succeeded
from ai_dlc.environment.machine import MachineManager
from ai_dlc.errors import AiDlcError

app = typer.Typer(no_args_is_help=True, help="Portable development for people and agents.")
LEGACY_DOCS_NOTE = (
    "The former docs-* commands moved to `ai-dlc docs`. For one release docs-init, "
    "docs-check, docs-inventory, docs-style, docs-impact, docs-disposition, "
    "docs-baseline, docs-review, docs-review-check, docs-gate, docs-search and "
    "docs-read still run here and name their replacement."
)
project = typer.Typer(no_args_is_help=True, epilog=LEGACY_DOCS_NOTE)
docs = typer.Typer(
    no_args_is_help=True,
    help="Project documentation: ownership checks, impact review, the gate, search and navigation.",
)
work = typer.Typer(no_args_is_help=True)
agents = typer.Typer(no_args_is_help=True)
agent_bundle = typer.Typer(no_args_is_help=True)
profile = typer.Typer(no_args_is_help=True)
setup = typer.Typer(no_args_is_help=True)
machine = typer.Typer(no_args_is_help=True)
knowledge = typer.Typer(no_args_is_help=True)
provider = typer.Typer(no_args_is_help=True)
mcp = typer.Typer(no_args_is_help=True)
for name, group in [
    ("project", project),
    ("docs", docs),
    ("work", work),
    ("agents", agents),
    ("profile", profile),
    ("setup", setup),
    ("machine", machine),
    ("knowledge", knowledge),
    ("provider", provider),
    ("mcp", mcp),
]:
    app.add_typer(group, name=name)
agents.add_typer(agent_bundle, name="bundle")


def emit(value):
    typer.echo(json.dumps(value, indent=2, sort_keys=True, default=str))


# Failures a service may raise. AiDlcError is the application's own base; the builtin
# types stay until every bare raise in the services has moved to a typed error.
SERVICE_FAILURES = (AiDlcError, OSError, RuntimeError, TypeError, ValueError)


@contextmanager
def service_call():
    """Report a failed service call once: message and notes on stderr, exit code from the error."""
    try:
        yield
    except SERVICE_FAILURES as exc:
        typer.echo(f"Error: {exc}", err=True)
        for note in getattr(exc, "__notes__", ()):
            typer.echo(note, err=True)
        raise typer.Exit(getattr(exc, "exit_code", 2)) from None


def conclude(result) -> None:
    """Emit a completed service result and map its envelope to the exit status."""
    emit(result)
    if not succeeded(result):
        raise typer.Exit(1)


def config_for(root: Path, machine: Path | None = None) -> dict:
    return resolve_runtime(root, machine=machine).values


def _show_version(value: bool) -> None:
    if value:
        from ai_dlc import __version__

        typer.echo(f"ai-dlc {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version", callback=_show_version, is_eager=True, help="Show the version and exit."
        ),
    ] = False,
):
    """Portable development for people and agents."""


@app.command()
def scaffold(
    provider: Annotated[list[str] | None, typer.Option("--provider", "-p")] = None,
    all: bool = False,
):
    from ai_dlc.compatibility.legacy import scaffold as run

    emit(run(Path.cwd(), provider or [], all))


@project.command("check")
def project_check(
    root: Path = Path("."),
    target: str = "local",
    required: bool = True,
    json_output: Annotated[bool, typer.Option("--json")] = False,
    receipt: Path | None = None,
):
    from ai_dlc.setup.project import RuntimeUnavailable, check_project

    try:
        result = check_project(root, target, required_only=required)
    except RuntimeUnavailable as exc:
        # No check ran, so no receipt is written and no outcome may read as passing.
        failure = {
            "schema": 1,
            "status": "runtime-unavailable",
            "ran": False,
            "error": str(exc),
            "executable": exc.executable,
            "remedy": exc.remedy,
            "outcomes": [],
        }
        emit(failure)
        if not json_output:
            typer.echo(f"error: {exc}", err=True)
            for step in exc.remedy:
                typer.echo(f"  - {step}", err=True)
        raise typer.Exit(1) from None
    if receipt:
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(json.dumps(result, indent=2) + "\n")
    emit(result)
    passed = {
        x["id"] for x in result["outcomes"] if x["status"] == "passed" and x["exit_code"] == 0
    }
    if not set(result["required"]).issubset(passed):
        raise typer.Exit(1)


@project.command("setup")
def project_setup(root: Path = Path("."), target: str = "local"):
    from ai_dlc.setup.project import setup_project

    emit(setup_project(root, target))


@project.command("readiness")
def project_readiness(root: Path = Path(".")):
    """Inspect selected project requirements offline without applying changes."""
    import os

    from ai_dlc.setup.provision import project_readiness as inspect
    from ai_dlc.setup.provision import readiness_config

    result = inspect(root, readiness_config(root), os.environ)
    conclude(result)


@project.command("init")
def project_init(
    path: Path,
    preset: str = "generic",
    apply: bool = True,
    template_source: str | None = None,
    vcs_ref: str | None = None,
    capability: Annotated[list[str] | None, typer.Option("--capability")] = None,
    tracker: Annotated[str | None, typer.Option("--tracker")] = None,
    knowledge_provider: Annotated[str | None, typer.Option("--knowledge")] = None,
    agent_client: Annotated[list[str] | None, typer.Option("--agent-client")] = None,
    docs_preset: Annotated[str | None, typer.Option("--docs-preset")] = None,
    link_vault_option: Annotated[bool, typer.Option("--link-vault")] = False,
    vault: Annotated[Path | None, typer.Option("--vault")] = None,
):
    from ai_dlc.setup.templates import adopt

    result = adopt(
        path,
        preset=preset,
        apply=apply,
        template_source=template_source,
        vcs_ref=vcs_ref,
        capabilities=capability,
        providers={
            role: value
            for role, value in (("tracker", tracker), ("knowledge", knowledge_provider))
            if value is not None
        },
        agent_clients=agent_client,
        initialize=True,
        docs_preset=docs_preset,
        link_vault=link_vault_option,
        vault=vault,
    )
    emit(result)


@project.command("adopt")
def project_adopt(
    root: Path = Path("."),
    preset: str = "generic",
    apply: bool = False,
    template_source: str | None = None,
    vcs_ref: str | None = None,
    capability: Annotated[list[str] | None, typer.Option("--capability")] = None,
    tracker: Annotated[str | None, typer.Option("--tracker")] = None,
    knowledge_provider: Annotated[str | None, typer.Option("--knowledge")] = None,
    agent_client: Annotated[list[str] | None, typer.Option("--agent-client")] = None,
    docs_preset: Annotated[str | None, typer.Option("--docs-preset")] = None,
    link_vault_option: Annotated[bool, typer.Option("--link-vault")] = False,
    vault: Annotated[Path | None, typer.Option("--vault")] = None,
):
    from ai_dlc.setup.templates import adopt

    result = adopt(
        root,
        preset=preset,
        apply=apply,
        template_source=template_source,
        vcs_ref=vcs_ref,
        capabilities=capability,
        providers={
            role: value
            for role, value in (("tracker", tracker), ("knowledge", knowledge_provider))
            if value is not None
        },
        agent_clients=agent_client,
        docs_preset=docs_preset,
        link_vault=link_vault_option,
        vault=vault,
    )
    emit(result)


# Documentation commands. Every `docs` command and every hidden `project docs-*` alias
# calls the same helper, so an alias cannot drift from its replacement.


def _deprecated(old: str, new: str) -> None:
    typer.echo(
        f"Deprecated: `ai-dlc project {old}` is now `ai-dlc {new}`; "
        "the old name is removed in the next release.",
        err=True,
    )


def _docs_init(root: Path, preset: str, apply: bool) -> None:
    from ai_dlc.documentation.moc import initialize_documents

    emit(initialize_documents(root, preset=preset, apply=apply))


def _docs_check(root: Path, strict: bool) -> None:
    from ai_dlc.documentation.documents import check_documents

    result = check_documents(root)
    emit(result)
    if strict and result["findings"]:
        raise typer.Exit(2)


def _docs_inventory(root: Path) -> None:
    from ai_dlc.documentation.document_inventory import inventory_documents

    emit(inventory_documents(root))


def _docs_style(root: Path, paths: list[str], strict: bool) -> None:
    from ai_dlc.documentation.document_style import check_style

    result = check_style(root, paths=paths)
    emit(result)
    if strict and result["status"] != "passed":
        raise typer.Exit(2)


def _docs_impact(root: Path, base: str) -> None:
    from ai_dlc.documentation.document_impact import inspect_impact

    emit(inspect_impact(root, base=base))


def _docs_disposition(root: Path, base: str, decisions: Path, reviewer: str) -> None:
    from ai_dlc.documentation.document_files import read_document
    from ai_dlc.documentation.document_impact import prepare_disposition

    emit(
        prepare_disposition(
            root,
            base=base,
            decisions=json.loads(read_document(decisions.absolute())),
            reviewer=reviewer,
        )
    )


def _docs_baseline(root: Path, owner: str, reason: str) -> None:
    from ai_dlc.documentation.document_impact import prepare_baseline

    emit(prepare_baseline(root, owner=owner, reason=reason))


def _docs_review_packet(root: Path, base: str, paths: list[str], max_bytes: int, source: str):
    from ai_dlc.documentation.document_review import prepare_review

    emit(prepare_review(root, paths=paths, base=base, max_bytes=max_bytes, source=source))


def _docs_review_check(root: Path, packet: Path, review: Path) -> None:
    from ai_dlc.documentation.document_files import read_document
    from ai_dlc.documentation.document_review import validate_review

    result = validate_review(
        root,
        packet=json.loads(read_document(packet.absolute())),
        review=json.loads(read_document(review.absolute())),
    )
    emit(result)
    if not result["valid"]:
        raise typer.Exit(2)


def _docs_gate(root: Path, evidence: str, baseline: str, base: str | None) -> None:
    from ai_dlc.documentation.document_impact import check_gate

    result = check_gate(root, evidence_path=evidence, baseline_path=baseline, base=base)
    emit(result)
    if not result["valid"]:
        raise typer.Exit(2)


def _docs_search(root: Path, query: str, sources, max_bytes: int, limit: int) -> None:
    from ai_dlc.documentation.document_access import search_project_documents

    emit(
        search_project_documents(
            root, query=query, sources=sources, max_bytes=max_bytes, limit=limit
        )
    )


def _docs_read(root: Path, path: str, sources, max_bytes: int) -> None:
    from ai_dlc.documentation.document_access import read_project_document

    emit(read_project_document(root, path=path, sources=sources, max_bytes=max_bytes))


# Options each `docs review` mode requires, keyed by the callback parameter name.
REVIEW_MODE_OPTIONS = {
    "disposition": {"reviewer": "--reviewer"},
    "baseline": {"owner": "--owner", "reason": "--reason"},
    "report": {"paths": "--path"},
    "check": {"packet": "--packet", "review": "--review"},
}


def _review_mode(values: dict) -> str:
    """Pick the one review mode the options select; refuse mixed, incomplete or stray ones."""
    selected = [name for name in REVIEW_MODE_OPTIONS if values[name]]
    if len(selected) > 1:
        raise typer.BadParameter("choose one mode: " + " ".join(f"--{m}" for m in selected))
    mode = selected[0] if selected else "impact"
    for name, options in REVIEW_MODE_OPTIONS.items():
        given = [flag for key, flag in options.items() if values[key]]
        missing = [flag for key, flag in options.items() if not values[key]]
        if name == mode and missing:
            raise typer.BadParameter(f"--{name} needs {', '.join(missing)}", param_hint=missing[0])
        if name != mode and given:
            raise typer.BadParameter(f"{', '.join(given)} applies to --{name}", param_hint=given[0])
    if mode in ("impact", "disposition", "report") and not values["base"]:
        raise typer.BadParameter("--base is required", param_hint="--base")
    return mode


@docs.command("init")
def docs_init(root: Path = Path("."), preset: str = "organized", apply: bool = False):
    """Preview or add canonical documentation navigation without relocating existing files."""
    _docs_init(root, preset, apply)


@docs.command("check")
def docs_check(
    root: Path = Path("."),
    strict: bool = False,
    inventory: Annotated[
        bool, typer.Option("--inventory", help="List repository Markdown paths instead.")
    ] = False,
    style: Annotated[
        bool, typer.Option("--style", help="Run configured Vale on each --path instead.")
    ] = False,
    paths: Annotated[list[str] | None, typer.Option("--path")] = None,
):
    """Inspect document ownership, coverage and links; --inventory and --style are alternatives."""
    if inventory and style:
        raise typer.BadParameter("choose --inventory or --style, not both")
    if paths and not style:
        raise typer.BadParameter("--path applies to --style", param_hint="--path")
    if style and not paths:
        raise typer.BadParameter("--style needs at least one --path", param_hint="--path")
    if inventory:
        _docs_inventory(root)
    elif style:
        _docs_style(root, paths or [], strict)
    else:
        _docs_check(root, strict)


@docs.command("review")
def docs_review(
    root: Path = Path("."),
    base: Annotated[str | None, typer.Option(help="Git comparison base.")] = None,
    disposition: Annotated[
        Path | None,
        typer.Option(help="Read reviewed decisions from this JSON file; emit evidence to stdout."),
    ] = None,
    reviewer: str | None = None,
    baseline: Annotated[
        bool, typer.Option("--baseline", help="Propose a historical-debt baseline.")
    ] = False,
    owner: str | None = None,
    reason: str | None = None,
    report: Annotated[
        bool, typer.Option("--report", help="Prepare a bounded review packet.")
    ] = False,
    paths: Annotated[list[str] | None, typer.Option("--path")] = None,
    max_bytes: int | None = None,
    source: str | None = None,
    check: Annotated[
        bool, typer.Option("--check", help="Validate a review against its packet.")
    ] = False,
    packet: Path | None = None,
    review: Path | None = None,
):
    """Inspect documentation impact; one mode flag records, baselines, reports or checks instead."""
    mode = _review_mode(
        {
            "base": base,
            "disposition": disposition,
            "reviewer": reviewer,
            "baseline": baseline,
            "owner": owner,
            "reason": reason,
            "report": report,
            "paths": paths,
            "check": check,
            "packet": packet,
            "review": review,
        }
    )
    if mode != "report" and (max_bytes is not None or source is not None):
        raise typer.BadParameter("--max-bytes and --source apply to --report")
    if mode == "disposition":
        _docs_disposition(root, str(base), Path(str(disposition)), str(reviewer))
    elif mode == "baseline":
        _docs_baseline(root, str(owner), str(reason))
    elif mode == "report":
        _docs_review_packet(
            root,
            str(base),
            paths or [],
            64000 if max_bytes is None else max_bytes,
            source or "catalog",
        )
    elif mode == "check":
        _docs_review_check(root, Path(str(packet)), Path(str(review)))
    else:
        _docs_impact(root, str(base))


@docs.command("gate")
def docs_gate(
    root: Path = Path("."),
    evidence: str = ".ai-dlc/documentation/current.json",
    baseline: str = ".ai-dlc/documentation/baseline.json",
    base: Annotated[str | None, typer.Option(envvar="AI_DLC_DOCS_BASE")] = None,
):
    """Require current dispositions and refuse new objective documentation defects."""
    _docs_gate(root, evidence, baseline, base)


@docs.command("search")
def docs_search(
    query: str,
    root: Path = Path("."),
    sources: Annotated[list[str] | None, typer.Option("--source")] = None,
    max_bytes: int = 64000,
    limit: int = 20,
):
    """Search docs/, openspec/ and declared project Markdown; bounded, never private notes."""
    _docs_search(root, query, sources, max_bytes, limit)


@docs.command("read")
def docs_read(
    path: str,
    root: Path = Path("."),
    sources: Annotated[list[str] | None, typer.Option("--source")] = None,
    max_bytes: int = 64000,
):
    """Read one complete eligible project document within a byte budget."""
    _docs_read(root, path, sources, max_bytes)


# Hidden aliases: one release of compatibility for the former `project docs-*` names.


@project.command("docs-init", hidden=True)
def project_docs_init(root: Path = Path("."), preset: str = "organized", apply: bool = False):
    _deprecated("docs-init", "docs init")
    _docs_init(root, preset, apply)


@project.command("docs-check", hidden=True)
def project_docs_check(root: Path = Path("."), strict: bool = False):
    _deprecated("docs-check", "docs check")
    _docs_check(root, strict)


@project.command("docs-impact", hidden=True)
def project_docs_impact(base: Annotated[str, typer.Option()], root: Path = Path(".")):
    _deprecated("docs-impact", "docs review")
    _docs_impact(root, base)


@project.command("docs-disposition", hidden=True)
def project_docs_disposition(
    base: Annotated[str, typer.Option()],
    decisions: Annotated[Path, typer.Option()],
    reviewer: Annotated[str, typer.Option()],
    root: Path = Path("."),
):
    _deprecated("docs-disposition", "docs review --disposition FILE --reviewer NAME")
    _docs_disposition(root, base, decisions, reviewer)


@project.command("docs-baseline", hidden=True)
def project_docs_baseline(
    owner: Annotated[str, typer.Option()],
    reason: Annotated[str, typer.Option()],
    root: Path = Path("."),
):
    _deprecated("docs-baseline", "docs review --baseline")
    _docs_baseline(root, owner, reason)


@project.command("docs-style", hidden=True)
def project_docs_style(
    paths: Annotated[list[str], typer.Option("--path")],
    root: Path = Path("."),
    strict: bool = False,
):
    _deprecated("docs-style", "docs check --style")
    _docs_style(root, paths, strict)


@project.command("docs-inventory", hidden=True)
def project_docs_inventory(root: Path = Path(".")):
    _deprecated("docs-inventory", "docs check --inventory")
    _docs_inventory(root)


@project.command("docs-search", hidden=True)
def project_docs_search(
    query: str,
    root: Path = Path("."),
    sources: Annotated[list[str] | None, typer.Option("--source")] = None,
    max_bytes: int = 64000,
    limit: int = 20,
):
    _deprecated("docs-search", "docs search")
    _docs_search(root, query, sources, max_bytes, limit)


@project.command("docs-read", hidden=True)
def project_docs_read(
    path: str,
    root: Path = Path("."),
    sources: Annotated[list[str] | None, typer.Option("--source")] = None,
    max_bytes: int = 64000,
):
    _deprecated("docs-read", "docs read")
    _docs_read(root, path, sources, max_bytes)


@project.command("docs-review", hidden=True)
def project_docs_review(
    base: Annotated[str, typer.Option()],
    paths: Annotated[list[str], typer.Option("--path")],
    root: Path = Path("."),
    max_bytes: int = 64000,
    source: str = "catalog",
):
    _deprecated("docs-review", "docs review --report")
    _docs_review_packet(root, base, paths, max_bytes, source)


@project.command("docs-review-check", hidden=True)
def project_docs_review_check(
    packet: Annotated[Path, typer.Option()],
    review: Annotated[Path, typer.Option()],
    root: Path = Path("."),
):
    _deprecated("docs-review-check", "docs review --check")
    _docs_review_check(root, packet, review)


@project.command("docs-gate", hidden=True)
def project_docs_gate(
    root: Path = Path("."),
    evidence: str = ".ai-dlc/documentation/current.json",
    baseline: str = ".ai-dlc/documentation/baseline.json",
    base: Annotated[str | None, typer.Option(envvar="AI_DLC_DOCS_BASE")] = None,
):
    _deprecated("docs-gate", "docs gate")
    _docs_gate(root, evidence, baseline, base)


@project.command("sync")
def project_sync(root: Path = Path("."), apply: bool = False, vcs_ref: str | None = None):
    from ai_dlc.setup.templates import sync

    emit(sync(root, apply=apply, vcs_ref=vcs_ref))


@project.command("link-vault")
def project_link_vault(
    root: Path = Path("."),
    vault: Annotated[Path | None, typer.Option("--vault", "-v")] = None,
    name: Annotated[str | None, typer.Option("--name", "-n")] = None,
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Compatibility flag; never overwrites notes.")
    ] = False,
    preview: Annotated[bool, typer.Option("--preview")] = False,
    docs_preset: Annotated[str | None, typer.Option("--docs-preset")] = None,
    mode: str = "portal",
    adopt: Annotated[bool, typer.Option("--adopt")] = False,
):
    """Create a local portal or explicit canonical directory mounts; --preview writes nothing."""
    from ai_dlc.documentation.vault_link import link_vault

    with service_call():
        result = link_vault(
            root,
            vault=vault,
            name=name,
            force=force,
            docs_preset=docs_preset,
            apply=not preview,
            mode=mode,
            adopt=adopt,
        )
    emit(result.as_dict())


@project.command("workspace-check")
def project_workspace_check(root: Path = Path(".")):
    """Inspect installation, activation, local mounts and navigation without changes."""
    from ai_dlc.documentation.workspace_diagnostics import inspect_project_workspace

    vault = config_for(root).get("paths", {}).get("vault")
    emit(inspect_project_workspace(root, vault=vault))


@project.command("workspace-init")
def project_workspace_init(
    root: Path = Path("."),
    vault: Path | None = None,
    name: str | None = None,
    bases: bool = False,
    apply: bool = False,
    shell: bool = False,
):
    """Preview or add linked Obsidian project navigation and personal note templates."""
    from ai_dlc.documentation.knowledge_workspace import setup_workspace

    if shell and (vault is not None or name is not None or bases):
        raise typer.BadParameter("--shell cannot be combined with --vault, --name or --bases")
    with service_call():
        if shell:
            from ai_dlc.environment.bootstrap import plan_shell_activation

            emit(plan_shell_activation(apply=apply))
            return
        emit(setup_workspace(root, vault=vault, name=name, bases=bases, apply=apply))


@project.command("rebind")
def project_rebind(
    role: str,
    provider_id: str,
    root: Path = Path("."),
    plan: bool = True,
    mappings: Path | None = None,
    machine: Path | None = None,
    connection_plan: Annotated[Path | None, typer.Option("--connection-plan")] = None,
):
    from ai_dlc.setup.rebind import rebind

    with service_call():
        result = rebind(
            root,
            role,
            provider_id,
            apply=not plan,
            mappings=read_toml(mappings) if mappings else {},
            machine_config=read_toml(machine) if machine else None,
            connection_plan=connection_plan,
            environ=os.environ,
        )
    emit(result)


@project.command("tracker-create-plan")
def project_tracker_create_plan(
    provider_id: str,
    source: Annotated[str, typer.Option("--source")],
    work: Annotated[list[str], typer.Option("--work")],
    create: Annotated[list[str], typer.Option("--create")],
    root: Path = Path("."),
    mappings: Path | None = None,
    save_plan: Path | None = None,
    machine: Path | None = None,
):
    """Preview exact local-record target creation; saving never contacts the tracker."""
    from ai_dlc.setup.tracker_targets import (
        plan_tracker_targets,
        read_tracker_mappings,
        save_tracker_targets_plan,
    )

    with service_call():
        result = plan_tracker_targets(
            root,
            provider_id,
            work_ids=work,
            create_work_ids=create,
            source=source,
            mappings=read_tracker_mappings(mappings),
            environ=os.environ,
            machine=machine,
        )
        if save_plan is not None:
            path = save_tracker_targets_plan(root, result, save_plan)
            result = {"status": "planned", "path": path, "plan": result}
    emit(result)


@project.command("tracker-reconcile")
def project_tracker_reconcile(
    plan: Annotated[Path, typer.Option("--plan")],
    root: Path = Path("."),
    save_plan: Path | None = None,
    machine: Path | None = None,
):
    """Explicitly reconcile reviewed saved creation intent; never apply local bindings."""
    from ai_dlc.setup.tracker_targets import reconcile_tracker_targets
    from ai_dlc.work.tracker_migration import save_tracker_migration_plan

    with service_call():
        result = reconcile_tracker_targets(root, plan, environ=os.environ, machine=machine)
    if save_plan is not None and result["migration_plan"] is not None:
        try:
            result["saved_plan"] = save_tracker_migration_plan(
                root, result["migration_plan"], save_plan
            )
        except SERVICE_FAILURES as exc:
            result["save_error"] = str(exc)
            emit(result)
            raise typer.Exit(2) from None
    emit(result)
    if result["status"] != "resolved":
        raise typer.Exit(2)


@project.command("tracker-migrate")
def project_tracker_migrate(
    provider_id: Annotated[str | None, typer.Argument()] = None,
    root: Path = Path("."),
    mode: str | None = None,
    work: Annotated[list[str] | None, typer.Option("--work")] = None,
    mappings: Path | None = None,
    save_plan: Path | None = None,
    apply_plan: Path | None = None,
    machine: Path | None = None,
    inspect_recovery: str | None = None,
    resolve_recovery: str | None = None,
):
    """Preview a tracker default/selected move, or apply an exact saved JSON plan."""
    from ai_dlc.setup.tracker_targets import read_tracker_mappings
    from ai_dlc.work.tracker_migration import (
        apply_tracker_migration,
        inspect_tracker_migration,
        plan_tracker_migration,
        resolve_tracker_migration_recovery,
        save_tracker_migration_plan,
    )

    with service_call():
        actions = sum(
            value is not None for value in (apply_plan, inspect_recovery, resolve_recovery)
        )
        intent = any(value is not None for value in (provider_id, mode, work, mappings, save_plan))
        if actions > 1 or (actions and intent):
            raise ValueError("Saved apply/recovery cannot be combined with new migration intent")
        if apply_plan is not None:
            result = apply_tracker_migration(root, apply_plan, environ=os.environ, machine=machine)
        elif inspect_recovery is not None:
            result = inspect_tracker_migration(root, inspect_recovery)
        elif resolve_recovery is not None:
            result = resolve_tracker_migration_recovery(root, resolve_recovery)
        else:
            if provider_id is None or mode is None:
                raise ValueError("Preview requires provider ID and --mode default-only or selected")
            result = plan_tracker_migration(
                root,
                provider_id,
                mode=mode,
                work_ids=work,
                mappings=read_tracker_mappings(mappings),
                environ=os.environ,
                machine=machine,
            )
            if save_plan is not None:
                path = save_tracker_migration_plan(root, result, save_plan)
                result = {"status": "planned", "plan_path": path, "plan": result}
    emit(result)
    if apply_plan is not None and not succeeded(result):
        raise typer.Exit(1)


@agents.command("connect")
def agents_connect(
    root: Path = Path("."),
    bindings: Path | None = None,
    save_plan: Path | None = None,
    apply_plan: Path | None = None,
):
    """Review native role bindings and apply only project configuration."""
    from ai_dlc.harness.native_composition import apply_native_connections, plan_native_connections

    try:
        if apply_plan is not None:
            if bindings is not None or save_plan is not None:
                raise ValueError("Native apply consumes only the saved plan")
            result = apply_native_connections(root, apply_plan, environ=os.environ)
        else:
            if bindings is None:
                raise ValueError("Native preview requires --bindings")
            result = plan_native_connections(
                root, bindings, environ=os.environ, save_plan=save_plan
            )
    except SERVICE_FAILURES as exc:
        emit({"status": "refused", "reason": str(exc)})
        raise typer.Exit(1) from None
    emit(result)


@agents.command("render")
def agents_render(
    root: Path = Path("."),
    check: bool = False,
    apply: bool = False,
    client: str | None = None,
    personal: Path | None = None,
    home: Path | None = None,
):
    if check and apply:
        raise typer.BadParameter("choose --check or --apply")
    if home is not None and personal is None:
        raise typer.BadParameter("--home requires --personal")
    if personal is not None:
        from ai_dlc.harness.user_agents import render_user_agents

        config = resolve_files(personal=personal).values
        result = render_user_agents(config, home or Path.home(), apply=apply, client=client)
    else:
        from ai_dlc.harness.agents import render_agents

        result = render_agents(root, apply=apply, client=client)
    emit(result)
    if check and not succeeded(result):
        raise typer.Exit(1)


@agent_bundle.command("import")
def agents_bundle_import(
    source: str,
    ref: Annotated[str, typer.Option("--ref")],
    bundle_id: Annotated[str, typer.Option("--id")],
    root: Annotated[Path, typer.Option("--root")] = Path("."),
    apply: Annotated[bool, typer.Option("--apply")] = False,
    expected_commit: Annotated[str | None, typer.Option("--expected-commit")] = None,
):
    """Preview or vendor one pinned portable workflow bundle."""
    from ai_dlc.harness.workflow_bundles import (
        import_bundle,
        resolve_bundle,
        validate_bundle_project,
    )

    with service_call():
        if apply and expected_commit is None:
            raise ValueError("bundle apply requires --expected-commit")
        if not apply and expected_commit is not None:
            raise ValueError("bundle --expected-commit requires --apply")
        root = validate_bundle_project(root)
        with resolve_bundle(source, ref, bundle_id, environ=os.environ) as candidate:
            result = import_bundle(
                root,
                candidate,
                apply=apply,
                expected_commit=expected_commit,
            )
    emit(result)


@profile.command("show")
def profile_show(
    base: Path | None = None,
    personal: Path | None = None,
    project: Path | None = None,
    machine: Path | None = None,
    resolved: bool = True,
):
    result = resolve_runtime(base=base, personal=personal, project=project, machine=machine)
    emit({"values": result.values, "sources": result.sources})


@profile.command("migrate")
def profile_migrate(path: Path, apply: bool = False):
    from ai_dlc.setup.provision import migrate

    emit(migrate(path, apply))


@profile.command("capture")
def profile_capture(profile: Path):
    from ai_dlc.setup.provision import capture

    emit(capture(profile))


@setup.command("plan")
def setup_plan(
    profile: Annotated[Path | None, typer.Option("--profile")] = None,
    headless: bool = False,
    home: Path | None = None,
    root: Annotated[Path | None, typer.Option("--root")] = None,
):
    manager = MachineManager(home=home)
    if root is None:
        emit(manager.plan(headless=headless, profile=profile))
    else:
        emit(manager.plan(headless=headless, profile=profile, root=root))


@setup.command("apply")
def setup_apply(
    profile: Annotated[Path | None, typer.Option("--profile")] = None,
    headless: bool = False,
    home: Path | None = None,
    root: Annotated[Path | None, typer.Option("--root")] = None,
):
    manager = MachineManager(home=home)
    if root is None:
        emit(manager.apply(headless=headless, profile=profile))
    else:
        emit(manager.apply(headless=headless, profile=profile, root=root))


@machine.command("enroll")
def machine_enroll(
    source: str,
    profile_id: Annotated[str, typer.Option("--profile-id")],
    machine_id: Annotated[str, typer.Option("--machine-id")],
    ref: Annotated[str, typer.Option("--ref")] = "main",
    subdirectory: Annotated[str, typer.Option("--subdirectory")] = "",
    apply: bool = False,
):
    emit(
        MachineManager().enroll(
            source,
            profile_id,
            machine_id,
            requested_ref=ref,
            subdirectory=subdirectory,
            apply=apply,
        )
    )


@machine.command("migrate")
def machine_migrate(
    source: str,
    profile_file: Annotated[str, typer.Option("--profile-file")],
    profile_id: Annotated[str, typer.Option("--profile-id")],
    machine_id: Annotated[str, typer.Option("--machine-id")],
    ref: Annotated[str, typer.Option("--ref")] = "main",
    subdirectory: Annotated[str, typer.Option("--subdirectory")] = "",
    apply: bool = False,
):
    emit(
        MachineManager().migrate(
            source,
            profile_file,
            profile_id,
            machine_id,
            requested_ref=ref,
            subdirectory=subdirectory,
            apply=apply,
        )
    )


@machine.command("plan")
def machine_plan_command(
    headless: bool = False,
    root: Annotated[Path | None, typer.Option("--root")] = None,
):
    manager = MachineManager()
    if root is None:
        emit(manager.plan(headless=headless))
    else:
        emit(manager.plan(headless=headless, root=root))


@machine.command("apply")
def machine_apply_command(
    headless: bool = False,
    root: Annotated[Path | None, typer.Option("--root")] = None,
):
    manager = MachineManager()
    if root is None:
        emit(manager.apply(headless=headless))
    else:
        emit(manager.apply(headless=headless, root=root))


@machine.command("sync")
def machine_sync(apply: bool = False, headless: bool = False):
    emit(MachineManager().sync(apply=apply, headless=headless))


@machine.command("status")
def machine_status():
    emit(MachineManager().status())


@machine.command("doctor")
def machine_doctor(
    root: Annotated[Path, typer.Option("--root")] = Path("."), target: str = "local"
):
    result = MachineManager().doctor(root, target=target)
    conclude(result)


@app.command()
def doctor(
    root: Annotated[Path | None, typer.Argument()] = None,
    root_option: Annotated[Path, typer.Option("--root")] = Path("."),
    target: str = "local",
    machine: Path | None = None,
):
    selected_root = root or root_option
    result = MachineManager().doctor(selected_root, target=target, machine=machine)
    conclude(result)


@app.command()
def context(root: Path = Path("."), brief: bool = False):
    """Print the offline session context as JSON; --brief prints the what-next summary."""
    from ai_dlc.work.workflow import build_context

    result = build_context(root, brief=brief)
    typer.echo(result["text"], nl=False) if brief else typer.echo(json.dumps(result, indent=2))


@app.command("next")
def next_summary(
    root: Annotated[Path, typer.Option("--root")] = Path("."),
    all_records: Annotated[
        bool, typer.Option("--all", help="Include unpublished records (no tracker artifact).")
    ] = False,
    as_json: Annotated[bool, typer.Option("--json", help="Print the same data as JSON.")] = False,
):
    """Summarize what to do next from local work records; the tracker is not consulted."""
    from ai_dlc.work.summary import render_next, summarize_next

    with service_call():
        summary = summarize_next(root, include_all=all_records)
    if as_json:
        emit(summary["records"])
    else:
        typer.echo(render_next(summary), nl=False)


def service(root: Path, machine: Path | None):
    from ai_dlc.work.workflow import WorkService

    return WorkService.from_project(root, machine=machine)


@work.command("validate")
def work_validate(
    work_id: Annotated[str | None, typer.Argument()] = None,
    root: Path = Path("."),
    machine: Path | None = None,
    all_records: Annotated[
        bool,
        typer.Option(
            "--all",
            help="Validate every record under .ai-dlc/work: record shape, local artifacts "
            "and the dependency graph, without resolving provider bindings.",
        ),
    ] = False,
):
    """Validate one record's dependency closure, or every record's artifacts with --all."""
    from ai_dlc.config import resolve_runtime
    from ai_dlc.work.workflow import validate_work, validate_work_records

    if all_records == (work_id is not None):
        # Plain text keeps the refusal readable and testable under any terminal renderer.
        typer.echo("error: Provide exactly one of a work ID or --all", err=True)
        raise typer.Exit(2)
    if all_records:
        result = validate_work_records(root)
    else:
        assert work_id is not None
        try:
            result = validate_work(root, resolve_runtime(root, machine=machine).values, work_id)
        except SERVICE_FAILURES as exc:
            result = {"valid": False, "work_id": work_id, "dependencies": [], "errors": [str(exc)]}
    errors = result.get("errors", [])
    if (
        not all_records
        and errors
        and all("Provider binding drift for " in error for error in errors)
    ):
        result["hint"] = "\n".join(
            "Provider binding drift for " + error.split("Provider binding drift for ", 1)[1]
            for error in errors
        )
    conclude(result)


@work.command("new")
def work_new(
    work_id: str,
    from_issue: Annotated[str | None, typer.Option("--from-issue")] = None,
    title: str | None = None,
    scope: str | None = None,
    requires_spec: Annotated[
        bool | None, typer.Option("--requires-spec/--no-requires-spec")
    ] = None,
    spec_reason: str | None = None,
    acceptance: Annotated[list[str] | None, typer.Option("--acceptance")] = None,
    root: Path = Path("."),
    machine: Path | None = None,
):
    """Create an unreviewed local work record from explicit fields or an issue."""
    try:
        record = service(root, machine).new(
            work_id,
            tracker_reference=from_issue,
            title=title,
            scope=scope,
            requires_spec=requires_spec,
            spec_reason=spec_reason,
            acceptance=acceptance,
        )
    except SERVICE_FAILURES as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(1) from exc
    emit(record)
    typer.echo(str(root.resolve() / ".ai-dlc/work" / f"{work_id}.toml"), err=True)


@work.command("publish")
def work_publish(work_id: str, root: Path = Path("."), machine: Path | None = None):
    emit(service(root, machine).publish(work_id))


CommitOption = Annotated[
    bool,
    typer.Option(
        "--commit/--no-commit",
        help="Commit the edited work record, staging only .ai-dlc/work/<id>.toml.",
    ),
]


@work.command("link")
def work_link(
    work_id: str,
    kind: str,
    reference: str,
    root: Path = Path("."),
    machine: Path | None = None,
    commit: CommitOption = True,
):
    emit(service(root, machine).link(work_id, kind, reference, commit=commit))


@work.command("start")
def work_start(
    work_id: str, root: Path = Path("."), machine: Path | None = None, commit: CommitOption = True
):
    emit(service(root, machine).start(work_id, commit=commit))


@work.command("pr")
def work_pr(work_id: str, root: Path = Path("."), machine: Path | None = None):
    """Open the pull request for the bound branch once, link it and commit the record."""
    with service_call():
        conclude(service(root, machine).pr(work_id))


@work.command("status")
def work_status(work_id: str, root: Path = Path("."), machine: Path | None = None):
    emit(service(root, machine).status(work_id))


@work.command("finish")
def work_finish(
    work_id: str,
    root: Path = Path("."),
    machine: Path | None = None,
    handoff: Path | None = None,
    learning: Path | None = None,
):
    result = service(root, machine).finish(
        work_id,
        handoff.read_text() if handoff else None,
        learning.read_text() if learning else None,
    )
    conclude(result)


@knowledge.command("find")
def knowledge_find(query: str, vault: Path):
    from ai_dlc.documentation.knowledge import Knowledge

    emit(Knowledge(vault).find(query))


@knowledge.command("note")
def knowledge_note(path: str, body: Path, operation_id: str, vault: Path):
    from ai_dlc.documentation.knowledge import Knowledge

    emit(Knowledge(vault).note(path, body.read_text(), operation_id))


@knowledge.command("append")
def knowledge_append(path: str, body: Path, operation_id: str, vault: Path):
    from ai_dlc.documentation.knowledge import Knowledge

    emit(Knowledge(vault).append(path, body.read_text(), operation_id))


@provider.command("list")
def provider_list(root: Path = Path(".")):
    from ai_dlc.providers import Registry

    emit(Registry(load_project(root), root=root).discover())


@provider.command("connect")
def provider_connect(
    name: str,
    root: Annotated[Path, typer.Option("--root")] = Path("."),
    organization: Annotated[str | None, typer.Option("--organization")] = None,
    host: Annotated[str | None, typer.Option("--host")] = None,
    repository: Annotated[str | None, typer.Option("--repository")] = None,
    project: Annotated[str | None, typer.Option("--project")] = None,
    issues_only: Annotated[bool, typer.Option("--issues-only")] = False,
    status_field: Annotated[str | None, typer.Option("--status-field")] = None,
    open: Annotated[str | None, typer.Option("--open")] = None,
    team: Annotated[str | None, typer.Option("--team")] = None,
    in_progress: Annotated[str | None, typer.Option("--in-progress")] = None,
    closed: Annotated[str | None, typer.Option("--closed")] = None,
    plan_file: Annotated[Path | None, typer.Option("--plan-file")] = None,
    apply: Annotated[bool, typer.Option("--apply")] = False,
    select: Annotated[list[str] | None, typer.Option("--select")] = None,
):
    """Discover or explicitly configure a supported project provider."""
    from ai_dlc.setup.provider_onboarding import connect_provider

    with service_call():
        result = connect_provider(
            root,
            name=name,
            select=select,
            host=host,
            repository=repository,
            project=project,
            issues_only=True if issues_only else None,
            status_field=status_field,
            open=open,
            organization=organization,
            team=team,
            in_progress=in_progress,
            closed=closed,
            plan_file=plan_file,
            apply=apply,
            environ=os.environ,
        )
    emit(result)


@provider.command("test")
def provider_test(name: str, manifest: Path, live: bool = False):
    from ai_dlc.verification.sandbox import test_provider

    result = test_provider(name, read_toml(manifest), live=live)
    conclude(result)


@mcp.command("serve")
def mcp_serve(root: Path = Path("."), machine: Path | None = None):
    from ai_dlc.mcp_server import serve

    serve(root, machine)


@app.command("hook", hidden=True)
def hook(event: str, root: Path = Path(".")):
    from ai_dlc.harness.hooks import handle_hook

    result = handle_hook(root, event, json.load(sys.stdin))
    if result.get("decision") == "deny":
        typer.echo(result["reason"], err=True)
        raise typer.Exit(2)
    if result.get("friction"):
        typer.echo(result["friction"])
    if result.get("reminder"):
        typer.echo(result["message"])
    elif result.get("context"):
        typer.echo(result["context"])
    elif result.get("warning"):
        typer.echo(result["warning"])


if __name__ == "__main__":
    app()
