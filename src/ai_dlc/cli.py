"""CLI surface; workflow operations delegate to the same services as MCP."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Annotated

import typer

from ai_dlc.config import load_project, read_toml, resolve_files, resolve_runtime
from ai_dlc.machine import MachineManager

app = typer.Typer(no_args_is_help=True, help="Portable development for people and agents.")
project = typer.Typer(no_args_is_help=True)
work = typer.Typer(no_args_is_help=True)
agents = typer.Typer(no_args_is_help=True)
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


def emit(value):
    typer.echo(json.dumps(value, indent=2, sort_keys=True, default=str))


def config_for(root: Path, machine: Path | None = None) -> dict:
    return resolve_runtime(root, machine=machine).values


@app.command()
def scaffold(
    provider: Annotated[list[str] | None, typer.Option("--provider", "-p")] = None,
    all: bool = False,
):
    from ai_dlc.legacy import scaffold as run

    emit(run(Path.cwd(), provider or [], all))


@project.command("check")
def project_check(
    root: Path = Path("."),
    target: str = "local",
    required: bool = True,
    json_output: Annotated[bool, typer.Option("--json")] = False,
    receipt: Path | None = None,
):
    from ai_dlc.project import check_project

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
    from ai_dlc.project import setup_project

    emit(setup_project(root, target))


@project.command("readiness")
def project_readiness(root: Path = Path(".")):
    """Inspect selected project requirements offline without applying changes."""
    import os

    from ai_dlc.provision import project_readiness as inspect

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
):
    from ai_dlc.templates import adopt

    emit(
        adopt(
            path,
            preset=preset,
            apply=apply,
            template_source=template_source,
            vcs_ref=vcs_ref,
            capabilities=capability,
            initialize=True,
        )
    )


@project.command("adopt")
def project_adopt(
    root: Path = Path("."),
    preset: str = "generic",
    apply: bool = False,
    template_source: str | None = None,
    vcs_ref: str | None = None,
    capability: Annotated[list[str] | None, typer.Option("--capability")] = None,
):
    from ai_dlc.templates import adopt

    emit(
        adopt(
            root,
            preset=preset,
            apply=apply,
            template_source=template_source,
            vcs_ref=vcs_ref,
            capabilities=capability,
        )
    )


@project.command("sync")
def project_sync(root: Path = Path("."), apply: bool = False, vcs_ref: str | None = None):
    from ai_dlc.templates import sync

    emit(sync(root, apply=apply, vcs_ref=vcs_ref))


@project.command("rebind")
def project_rebind(
    role: str,
    provider_id: str,
    root: Path = Path("."),
    plan: bool = True,
    mappings: Path | None = None,
    machine: Path | None = None,
):
    from ai_dlc.rebind import rebind

    emit(
        rebind(
            root,
            role,
            provider_id,
            apply=not plan,
            mappings=read_toml(mappings) if mappings else {},
            machine_config=read_toml(machine) if machine else None,
        )
    )


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
        from ai_dlc.user_agents import render_user_agents

        config = resolve_files(personal=personal).values
        result = render_user_agents(config, home or Path.home(), apply=apply, client=client)
    else:
        from ai_dlc.agents import render_agents

        result = render_agents(root, apply=apply, client=client)
    emit(result)
    if check and not result["clean"]:
        raise typer.Exit(1)


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
    from ai_dlc.provision import migrate

    emit(migrate(path, apply))


@profile.command("capture")
def profile_capture(profile: Path):
    from ai_dlc.provision import capture

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
    from ai_dlc.workflow import WorkService

    return WorkService(root, config_for(root, machine))


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
    from ai_dlc.knowledge import Knowledge

    emit(Knowledge(vault).find(query))


@knowledge.command("note")
def knowledge_note(path: str, body: Path, operation_id: str, vault: Path):
    from ai_dlc.knowledge import Knowledge

    emit(Knowledge(vault).note(path, body.read_text(), operation_id))


@knowledge.command("append")
def knowledge_append(path: str, body: Path, operation_id: str, vault: Path):
    from ai_dlc.knowledge import Knowledge

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
    team: Annotated[str | None, typer.Option("--team")] = None,
    in_progress: Annotated[str | None, typer.Option("--in-progress")] = None,
    closed: Annotated[str | None, typer.Option("--closed")] = None,
    plan_file: Annotated[Path | None, typer.Option("--plan-file")] = None,
    apply: Annotated[bool, typer.Option("--apply")] = False,
):
    """Discover or explicitly configure a supported project provider."""
    if name != "linear":
        raise typer.BadParameter(f"Provider connection is not supported: {name}")
    from ai_dlc.provider_onboarding import connect_linear_provider

    try:
        result = connect_linear_provider(
            root,
            organization=organization,
            team=team,
            in_progress=in_progress,
            closed=closed,
            plan_file=plan_file,
            apply=apply,
            environ=os.environ,
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from None
    emit(result)


@provider.command("test")
def provider_test(name: str, manifest: Path, live: bool = False):
    from ai_dlc.sandbox import test_provider

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
    from ai_dlc.hooks import handle_hook

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
