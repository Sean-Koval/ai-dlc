"""Common connection dispatch and exact-plan file boundaries.

Linear retains its canonical-digest codec; GitHub and declarative handlers share
these exact-byte primitives without changing GitHub's saved formats or journal.
"""

import copy
import hashlib
import json
import os
import re
import stat
import tempfile
import tomllib
from collections.abc import Mapping
from pathlib import Path

from ai_dlc.config import digest, resolve_layers, resolve_runtime
from ai_dlc.locking import project_write_lock


def snapshot_work(root):
    directory = root / ".ai-dlc/work"
    if directory.is_symlink() or directory.parent.is_symlink():
        raise ValueError("Work bindings cannot use symlinks during connection")
    snapshot = {}
    for path in sorted(directory.glob("*.toml")):
        if path.is_symlink() or not path.is_file():
            raise ValueError("Work bindings must be regular files")
        snapshot[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return snapshot


def render_patch(text, alias, patch, *, require_project=False):
    from ai_dlc.setup.provider_onboarding import _set_table_value, _table_paths

    original = tomllib.loads(text)
    expected = copy.deepcopy(original)
    settings = expected.setdefault("providers", {}).setdefault(alias, {})
    paths = _table_paths(text)
    base = ("providers", alias)
    current = original.get("providers", {}).get(alias)
    if current is not None and base not in paths:
        raise ValueError(
            "Provider TOML representation cannot be edited safely; use provider tables"
        )

    def update(table, values, target):
        nonlocal text
        for key, value in values.items():
            if isinstance(value, dict):
                existing = target.get(key)
                if existing is not None and tuple((table + "." + key).split(".")) not in paths:
                    raise ValueError(
                        "Provider TOML representation cannot be edited safely; use provider tables"
                    )
                update(table + "." + key, value, target.setdefault(key, {}))
            else:
                text = _set_table_value(text, table, key, value)
                target[key] = value

    if require_project and "project" in settings and "project" not in patch:
        raise ValueError("Removing a configured Project requires a separate migration")
    update("providers." + alias, patch, settings)
    try:
        actual = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        raise ValueError("Provider TOML representation cannot be edited safely") from None
    if actual != expected:
        raise ValueError("Provider TOML representation cannot be edited safely")
    return text


def guard_bound_tracker(root, config, alias, patch):
    current = config.get("providers", {}).get(alias, {})
    # Even adding viewer identity changes provider fingerprints: retain all bound records.
    if all(current.get(key) == value for key, value in patch.items()):
        return
    for path in (root / ".ai-dlc/work").glob("*.toml"):
        work = tomllib.loads(path.read_text())
        selected = work.get("providers", {}).get("tracker", config.get("roles", {}).get("tracker"))
        if selected == alias and (
            work.get("bindings", {}).get("tracker") or work.get("artifacts", {}).get("tracker")
        ):
            raise ValueError("Tracker work is already bound; use a separate reviewed migration")


def save_exclusive_plan(root, path, plan):
    from ai_dlc.setup.provider_onboarding import _connection_plan_parent

    with _connection_plan_parent(root, path, create=True) as (resolved, parent, leaf):
        # Exclusive creation never clobbers an authored plan or follows a symlink.
        descriptor = os.open(
            leaf, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent
        )
        with os.fdopen(descriptor, "w") as stream:
            json.dump(plan, stream, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        return resolved.relative_to(root).as_posix()


def apply_exact_patch(
    root,
    alias,
    saved,
    *,
    environ,
    snapshot=snapshot_work,
    render=render_patch,
    lock=None,
    label="Provider",
    stage_prefix=".ai-dlc-connection-",
):
    """Apply an already revalidated exact plan with existing GitHub write safeguards."""
    with (lock or project_write_lock)(root):
        path = root / "ai-dlc.toml"
        if path.is_symlink():
            raise ValueError(f"{label} configuration must not be a symlink")
        before = path.read_bytes()
        if (
            hashlib.sha256(before).hexdigest() != saved["before_digest"]
            or snapshot(root) != saved["work_digest"]
        ):
            raise ValueError(f"{label} connection source or work bindings changed")
        if digest(resolve_runtime(root, environ=environ).values) != saved["runtime_digest"]:
            raise ValueError(f"{label} runtime configuration changed")
        rendered = render(before.decode(), alias, saved["patch"])
        # A private stage is retained on failure; never delete a possibly replaced pathname.
        stage = Path(tempfile.mkdtemp(prefix=stage_prefix, dir=root))
        staged = stage / "config.toml"
        descriptor = os.open(
            staged,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            stat.S_IMODE(path.stat().st_mode),
        )
        with os.fdopen(descriptor, "w") as stream:
            stream.write(rendered)
            stream.flush()
            os.fsync(stream.fileno())
            identity = os.fstat(stream.fileno())
        if (
            path.is_symlink()
            or path.read_bytes() != before
            or snapshot(root) != saved["work_digest"]
            or digest(resolve_runtime(root, environ=environ).values) != saved["runtime_digest"]
        ):
            raise ValueError(f"{label} source changed during apply; stage retained at {stage}")
        current = staged.lstat()
        if (current.st_dev, current.st_ino) != (identity.st_dev, identity.st_ino):
            raise ValueError(f"{label} stage changed; retained at {stage}")
        os.replace(staged, path)
        # Empty private directory retained intentionally; no cleanup by mutable pathname.


def parse_selections(values):
    """Parse repeatable selectors without logging values that may be credentials."""
    selected = {}
    for value in values or []:
        key, separator, choice = value.partition("=")
        if not separator or not choice.strip() or not re.fullmatch(r"[a-z][a-z0-9_-]*", key):
            raise ValueError("Selection requires KEY=VALUE with a nonempty value")
        key = key.replace("-", "_")
        if key in selected:
            raise ValueError(f"Duplicate selection: {key}")
        selected[key] = choice
    return selected


def choose_named(rows, selected, fields, label):
    """Resolve names and IDs only when exactly one authorized row matches."""
    matches = [row for row in rows if any(row.get(field) == selected for field in fields)]
    if len(matches) != 1:
        raise ValueError(f"Select one unambiguous authorized {label}")
    return matches[0]


def _definition(root, name, environ):
    from ai_dlc.provider_definitions import DEFINITIONS

    if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
        raise ValueError("Provider alias must use letters, digits, underscore or hyphen")
    runtime = resolve_runtime(root, environ=environ).values
    settings = runtime.get("providers", {}).get(name, {})
    kind = settings.get("kind", settings.get("type", name))
    if name == "linear":
        from ai_dlc.setup.provider_onboarding import _validate_linear_settings

        _validate_linear_settings(settings)
    if name in DEFINITIONS and kind != name:
        raise ValueError(f"Configured provider {name} does not use its named adapter")
    definition = DEFINITIONS.get(kind)
    if definition is None or (
        definition.handler is None and definition.compatibility_connect is None
    ):
        raise ValueError(
            f"Provider connection is not supported: {name}; lifecycle support is unchanged"
        )
    if not definition.aliases and name != kind:
        raise ValueError("Linear alias guided setup is unsupported; configure the alias explicitly")
    return runtime, definition


def _validated_discovery(discovery, definition):
    if (
        not isinstance(discovery, dict)
        or discovery.get("schema") != 1
        or discovery.get("complete") is not True
        or not isinstance(discovery.get("account"), dict)
        or not isinstance(discovery["account"].get("id"), str)
        or not discovery["account"]["id"]
        or not isinstance(discovery.get("resources"), dict)
        or set(discovery["resources"]) != definition.selection_keys
    ):
        raise ValueError("Connection discovery must contain complete account and resource identity")
    for rows in discovery["resources"].values():
        if not isinstance(rows, list) or any(
            not isinstance(row, dict)
            or any(not isinstance(row.get(key), str) or not row[key] for key in ("id", "name"))
            for row in rows
        ):
            raise ValueError("Connection discovery resources require names and IDs")
        if len({row["id"] for row in rows}) != len(rows):
            raise ValueError("Connection discovery contains duplicate resource identities")
    # Apply existing shared configuration secret checks before displaying/saving metadata.
    resolve_layers([("project", {"schema": 4, "providers": {"discovery": discovery}})])
    return discovery


def _guard_roles(root, runtime, alias, patch, roles):
    current = runtime.get("providers", {}).get(alias, {})
    if all(current.get(key) == value for key, value in patch.items()):
        return
    for path in (root / ".ai-dlc/work").glob("*.toml"):
        work = tomllib.loads(path.read_text())
        for role in roles:
            selected = work.get("providers", {}).get(role, runtime.get("roles", {}).get(role))
            if selected == alias and (
                work.get("bindings", {}).get(role) or work.get("artifacts", {}).get(role)
            ):
                raise ValueError(
                    "Provider work is already bound; use a separate reviewed migration"
                )


def _common_preview(root, alias, definition, selections, *, environ):
    path = root / "ai-dlc.toml"
    if path.is_symlink():
        raise ValueError("Connection configuration must not be a symlink")
    before = path.read_bytes()
    runtime = resolve_runtime(root, environ=environ).values
    work = snapshot_work(root)
    handler = definition.handler
    if handler is None:
        raise ValueError("Provider connection is not supported")
    discovery = _validated_discovery(handler.discover(runtime, alias, environ=environ), definition)
    if not selections:
        return {"provider": alias, "status": "discovered", "discovery": discovery}
    if set(selections) != definition.selection_keys:
        raise ValueError("Connection preview requires every declared selection")
    selected = {
        key: choose_named(discovery["resources"][key], value, ("id", "name"), key)["id"]
        for key, value in selections.items()
    }
    patch = handler.configure(copy.deepcopy(discovery), dict(selected))
    if not isinstance(patch, dict) or not patch:
        raise ValueError("Connection selector must return a nonempty provider patch")
    if patch.get("kind", definition.kind) != definition.kind:
        raise ValueError("Connection selector cannot change provider kind")
    patch = {**patch, "kind": definition.kind}
    rendered = render_patch(before.decode(), alias, patch)
    resolve_layers([("project", tomllib.loads(rendered))])
    _guard_roles(root, runtime, alias, patch, definition.roles)
    return {
        "provider": alias,
        "status": "planned",
        "plan": {
            "schema": 1,
            "kind": "provider-connection",
            "adapter": definition.kind,
            "provider": alias,
            "before_digest": hashlib.sha256(before).hexdigest(),
            "runtime_digest": digest(runtime),
            "work_digest": work,
            "selected": selected,
            "discovery": discovery,
            "patch": patch,
        },
    }


def load_saved_plan(root, plan_file):
    """Read a regular, non-symlink local plan; callers validate their own schema."""
    from ai_dlc.setup.provider_onboarding import _connection_plan_parent

    with _connection_plan_parent(root, plan_file, create=False) as (_, parent, leaf):
        descriptor = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(descriptor) as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError("Connection plan must be a regular file")
            return json.load(stream)


def _load_common_plan(root, plan_file):
    plan = load_saved_plan(root, plan_file)
    if (
        not isinstance(plan, dict)
        or set(plan)
        != {
            "schema",
            "kind",
            "adapter",
            "provider",
            "before_digest",
            "runtime_digest",
            "work_digest",
            "selected",
            "discovery",
            "patch",
        }
        or plan["schema"] != 1
        or plan["kind"] != "provider-connection"
    ):
        raise ValueError("Invalid common connection plan")
    return plan


def connect_provider(root: Path, *, name: str, environ: Mapping[str, str], select=None, **options):
    """Validate selections and dispatch compatibility or common declarative onboarding."""
    root = Path(root).resolve()
    generic = parse_selections(select)
    _, definition = _definition(root, name, environ)
    accepted = definition.selection_keys | {"plan_file", "apply"}
    arguments = {key: value for key, value in options.items() if value is not None}
    if any(key not in accepted for key in arguments) or any(
        key not in definition.selection_keys for key in generic
    ):
        raise ValueError(f"Selection flags do not apply to {definition.kind}")
    if arguments.keys() & generic.keys():
        raise ValueError("Duplicate legacy and generic selection")
    for key, value in generic.items():
        if key in definition.boolean_keys:
            if value not in {"true", "false"}:
                raise ValueError(f"Selection {key} requires true or false")
            generic[key] = value == "true"
    arguments.update(generic)
    if "plan_file" in arguments:
        arguments["plan_file"] = Path(arguments["plan_file"])
    if arguments.get("apply") and any(key in definition.selection_keys for key in arguments):
        raise ValueError("Connection apply consumes only saved selections")
    if definition.compatibility_connect is not None:
        return definition.compatibility_connect(root, alias=name, environ=environ, **arguments)
    plan_file = arguments.pop("plan_file", None)
    apply = arguments.pop("apply", False)
    if apply:
        if plan_file is None:
            raise ValueError("Connection apply requires --plan-file")
        saved = _load_common_plan(root, plan_file)
        if saved["provider"] != name or saved["adapter"] != definition.kind:
            raise ValueError("Connection plan provider identity mismatch")
        selected = saved["selected"]
        if not isinstance(selected, dict) or any(
            not isinstance(value, str) or not value for value in selected.values()
        ):
            raise ValueError("Invalid saved selections")
        fresh = _common_preview(root, name, definition, selected, environ=environ)
        if fresh.get("plan") != saved:
            raise ValueError(
                "Connection plan drift: source, runtime, work or remote identity changed"
            )
        apply_exact_patch(root, name, saved, environ=environ)
        return {"provider": name, "status": "applied", "selected": selected}
    result = _common_preview(root, name, definition, arguments, environ=environ)
    if plan_file is not None:
        if result["status"] != "planned":
            raise ValueError("Saving a connection plan requires every declared selection")
        result["plan_file"] = save_exclusive_plan(root, plan_file, result["plan"])
    return result


def discover_connection(root, provider_id, *, environ):
    """Discover resources or the provider's existing default preview, without saving."""
    return connect_provider(root, name=provider_id, environ=environ)


def plan_connection(root, provider_id, selections, *, environ, plan_file=None):
    return connect_provider(
        root, name=provider_id, environ=environ, plan_file=plan_file, **selections
    )


def apply_connection(root, provider_id, plan_file, *, environ):
    return connect_provider(
        root, name=provider_id, environ=environ, plan_file=plan_file, apply=True
    )
