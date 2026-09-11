"""CLI surface; workflow operations delegate to the same services as MCP."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Annotated

import typer

from ai_dlc.config import load_project, read_toml, resolve_files, resolve_runtime
from ai_dlc.environment.machine import MachineManager

app = typer.Typer(no_args_is_help=True, help="Portable development for people and agents.")
project = typer.Typer(no_args_is_help=True)
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


def config_for(root: Path, machine: Path | None = None) -> dict:
    return resolve_runtime(root, machine=machine).values


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
    from ai_dlc.setup.project import check_project

    result = check_project(root, target, required_only=required)
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

    # Resolve local bindings while retaining only explicit provider selections.
    resolved = resolve_runtime(root)
    config = dict(resolved.values)
    config["roles"] = {
        role: value
        for role, value in config.get("roles", {}).items()
        if role == "agent-client"
        or resolved.sources.get(f"roles.{role}") in {"personal", "project"}
    }
    result = inspect(root, config, os.environ)
    emit(result)
    if not result["ready"]:
        raise typer.Exit(1)


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


@project.command("docs-init")
def project_docs_init(root: Path = Path("."), preset: str = "organized", apply: bool = False):
    """Preview or add canonical documentation navigation without relocating existing files."""
    from ai_dlc.documentation.moc import initialize_documents

    emit(initialize_documents(root, preset=preset, apply=apply))


@project.command("docs-check")
def project_docs_check(root: Path = Path("."), strict: bool = False):
    """Inspect canonical document ownership, coverage and review metadata without mutation."""
    from ai_dlc.documentation.documents import check_documents

    result = check_documents(root)
    emit(result)
    if strict and result["findings"]:
        raise typer.Exit(2)


@project.command("docs-impact")
def project_docs_impact(base: Annotated[str, typer.Option()], root: Path = Path(".")):
    """Identify documentation affected by a Git comparison and working changes."""
    from ai_dlc.documentation.document_impact import inspect_impact

    emit(inspect_impact(root, base=base))


@project.command("docs-disposition")
def project_docs_disposition(
    base: Annotated[str, typer.Option()],
    decisions: Annotated[Path, typer.Option()],
    reviewer: Annotated[str, typer.Option()],
    root: Path = Path("."),
):
    """Emit current content-bound evidence from reviewed JSON decisions; does not write files."""
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


@project.command("docs-baseline")
def project_docs_baseline(
    owner: Annotated[str, typer.Option()],
    reason: Annotated[str, typer.Option()],
    root: Path = Path("."),
):
    """Emit an explicit proposed historical-debt baseline for review."""
    from ai_dlc.documentation.document_impact import prepare_baseline

    emit(prepare_baseline(root, owner=owner, reason=reason))


@project.command("docs-style")
def project_docs_style(
    paths: Annotated[list[str], typer.Option("--path")],
    root: Path = Path("."),
    strict: bool = False,
):
    """Run explicitly configured optional Vale checks without installing tools."""
    from ai_dlc.documentation.document_style import check_style

    result = check_style(root, paths=paths)
    emit(result)
    if strict and result["status"] != "passed":
        raise typer.Exit(2)


@project.command("docs-inventory")
def project_docs_inventory(root: Path = Path(".")):
    """Discover repository Markdown paths and exclusions without reading bodies."""
    from ai_dlc.documentation.document_inventory import inventory_documents

    emit(inventory_documents(root))


@project.command("docs-review")
def project_docs_review(
    base: Annotated[str, typer.Option()],
    paths: Annotated[list[str], typer.Option("--path")],
    root: Path = Path("."),
    max_bytes: int = 64000,
    source: str = "catalog",
):
    """Prepare bounded selected-document evidence for the existing harness."""
    from ai_dlc.documentation.document_review import prepare_review

    emit(prepare_review(root, paths=paths, base=base, max_bytes=max_bytes, source=source))


@project.command("docs-review-check")
def project_docs_review_check(
    packet: Annotated[Path, typer.Option()],
    review: Annotated[Path, typer.Option()],
    root: Path = Path("."),
):
    """Check citation grounding and current source bytes, not semantic truth."""
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


@project.command("docs-gate")
def project_docs_gate(
    root: Path = Path("."),
    evidence: str = ".ai-dlc/documentation/current.json",
    baseline: str = ".ai-dlc/documentation/baseline.json",
    base: Annotated[str | None, typer.Option(envvar="AI_DLC_DOCS_BASE")] = None,
):
    """Require current dispositions and refuse new objective documentation defects."""
    from ai_dlc.documentation.document_impact import check_gate

    result = check_gate(root, evidence_path=evidence, baseline_path=baseline, base=base)
    emit(result)
    if not result["valid"]:
        raise typer.Exit(2)


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
):
    """Create a machine-local portal linking to canonical project documentation."""
    from ai_dlc.documentation.vault_link import link_vault

    try:
        result = link_vault(
            root, vault=vault, name=name, force=force, docs_preset=docs_preset, apply=not preview
        )
    except (OSError, RuntimeError, ValueError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(2) from None
    emit(result.as_dict())


@project.command("workspace-init")
def project_workspace_init(
    root: Path = Path("."),
    vault: Path | None = None,
    name: str | None = None,
    bases: bool = False,
    apply: bool = False,
):
    """Preview or add linked Obsidian project navigation and personal note templates."""
    from ai_dlc.documentation.knowledge_workspace import setup_workspace

    try:
        emit(setup_workspace(root, vault=vault, name=name, bases=bases, apply=apply))
    except (OSError, ValueError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(2) from None


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

    try:
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
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(2) from None
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
    from ai_dlc.setup.tracker_targets import plan_tracker_targets, save_tracker_targets_plan

    try:
        raw = read_toml(mappings) if mappings else {}
        if any(not isinstance(row, dict) or set(row) != {"tracker"} for row in raw.values()):
            raise ValueError("Mappings must have exactly tracker = REFERENCE per work table")
        result = plan_tracker_targets(
            root,
            provider_id,
            work_ids=work,
            create_work_ids=create,
            source=source,
            mappings={key: row["tracker"] for key, row in raw.items()},
            environ=os.environ,
            machine=machine,
        )
        if save_plan is not None:
            path = save_tracker_targets_plan(root, result, save_plan)
            result = {"status": "planned", "path": path, "plan": result}
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(2) from None
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

    try:
        result = reconcile_tracker_targets(root, plan, environ=os.environ, machine=machine)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(2) from None
    if save_plan is not None and result["migration_plan"] is not None:
        try:
            result["saved_plan"] = save_tracker_migration_plan(
                root, result["migration_plan"], save_plan
            )
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
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
    from ai_dlc.work.tracker_migration import (
        apply_tracker_migration,
        inspect_tracker_migration,
        plan_tracker_migration,
        resolve_tracker_migration_recovery,
        save_tracker_migration_plan,
    )

    try:
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
            raw = read_toml(mappings) if mappings else {}
            if any(not isinstance(row, dict) or set(row) != {"tracker"} for row in raw.values()):
                raise ValueError("Mappings must have exactly tracker = REFERENCE per work table")
            result = plan_tracker_migration(
                root,
                provider_id,
                mode=mode,
                work_ids=work,
                mappings={key: row["tracker"] for key, row in raw.items()},
                environ=os.environ,
                machine=machine,
            )
            if save_plan is not None:
                path = save_tracker_migration_plan(root, result, save_plan)
                result = {"status": "planned", "plan_path": path, "plan": result}
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(2) from None
    emit(result)
    if result.get("status") in {"rolled-back", "recovery-required"} and apply_plan is not None:
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
    except (OSError, ValueError) as exc:
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
    if check and not result["clean"]:
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

    try:
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
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        for note in getattr(exc, "__notes__", ()):
            if note.startswith("Bundle import "):
                typer.echo(note, err=True)
        raise typer.Exit(2) from None
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
    emit(result)
    if not result["ready"]:
        raise typer.Exit(1)


@app.command()
def doctor(
    root: Annotated[Path | None, typer.Argument()] = None,
    root_option: Annotated[Path, typer.Option("--root")] = Path("."),
    target: str = "local",
    machine: Path | None = None,
):
    selected_root = root or root_option
    result = MachineManager().doctor(selected_root, target=target, machine=machine)
    emit(result)
    if not result["ready"]:
        raise typer.Exit(1)


@app.command()
def context(root: Path = Path("."), brief: bool = False):
    config = load_project(root)
    records = []
    for path in sorted((root / ".ai-dlc/work").glob("*.toml")):
        record = read_toml(path)
        records.append({k: record.get(k) for k in ["id", "title", "artifacts", "providers"]})
    result = {
        "work": records[-3:] if brief else records,
        "required": config.get("checks", {}).get("required", []),
        "next": "Select work; prepare specification when required; publish/start; check; finish; handoff.",
    }
    text = json.dumps(result, indent=2)
    typer.echo(text[:2000] if brief else text)


def service(root: Path, machine: Path | None):
    from ai_dlc.work.workflow import WorkService

    return WorkService.from_project(root, machine=machine)


@work.command("validate")
def work_validate(work_id: str, root: Path = Path("."), machine: Path | None = None):
    from ai_dlc.config import resolve_runtime
    from ai_dlc.work.workflow import validate_work

    try:
        result = validate_work(root, resolve_runtime(root, machine=machine).values, work_id)
    except (OSError, ValueError) as exc:
        result = {"valid": False, "work_id": work_id, "dependencies": [], "errors": [str(exc)]}
    emit(result)
    if not result["valid"]:
        raise typer.Exit(1)


@work.command("publish")
def work_publish(work_id: str, root: Path = Path("."), machine: Path | None = None):
    emit(service(root, machine).publish(work_id))


@work.command("link")
def work_link(
    work_id: str, kind: str, reference: str, root: Path = Path("."), machine: Path | None = None
):
    emit(service(root, machine).link(work_id, kind, reference))


@work.command("start")
def work_start(work_id: str, root: Path = Path("."), machine: Path | None = None):
    emit(service(root, machine).start(work_id))


@work.command("status")
def work_status(work_id: str, root: Path = Path("."), machine: Path | None = None):
    emit(service(root, machine).status(work_id))


@work.command("finish")
def work_finish(
    work_id: str, root: Path = Path("."), machine: Path | None = None, handoff: Path | None = None
):
    result = service(root, machine).finish(work_id, handoff.read_text() if handoff else None)
    emit(result)
    if result.get("status") == "blocked":
        raise typer.Exit(1)


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

    try:
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
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(2) from None
    emit(result)


@provider.command("test")
def provider_test(name: str, manifest: Path, live: bool = False):
    from ai_dlc.verification.sandbox import test_provider

    result = test_provider(name, read_toml(manifest), live=live)
    emit(result)
    if not result["passed"]:
        raise typer.Exit(1)


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
    if result.get("reminder"):
        typer.echo(result["message"])
    elif result.get("context"):
        typer.echo(result["context"])
    elif result.get("warning"):
        typer.echo(result["warning"])


if __name__ == "__main__":
    app()
