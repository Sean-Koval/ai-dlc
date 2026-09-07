"""Real local migration files and registered contract fixtures; no remote services."""

import copy
import importlib
import importlib.util
import json
import os
import tomllib

import pytest
import tomli_w
from typer.testing import CliRunner

from ai_dlc.config import resolve_runtime
from ai_dlc.providers import Registry
from ai_dlc.workflow import WorkService


def migration():
    assert importlib.util.find_spec("ai_dlc.tracker_migration"), "Migration service is missing"
    return importlib.import_module("ai_dlc.tracker_migration")


class Tickets:
    """Adapter fixture owns configured project validation and canonical ticket identity."""

    def __init__(self):
        self.identities = {"42": "T42", "url/42": "T42", "43": "T43"}
        self.calls = []
        self.on_read = None

    def invoke(self, operation, payload):
        self.calls.append(operation)
        assert operation == "read", "Migration must never mutate remote tickets"
        if self.on_read:
            self.on_read()
        reference = payload["reference"]
        if reference not in self.identities:
            raise ValueError("Target belongs to wrong project")
        ticket = self.identities[reference]
        return {"id": ticket, "url": f"https://tracker.test/project/{ticket}", "state": "open"}


@pytest.fixture
def checkout(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "ai-dlc.toml").write_text(
        '# authored project\nschema = 4\n[roles]\ntracker = "old" # retain alias\n'
        'specs = "openspec"\nscm = "github"\n[providers.old]\nkind = "linear"\n'
        'team_id = "old-team"\n[providers.destination]\nkind = "fixture-plane"\n'
        '[scm]\nrepository = "org/repo"\n[gates]\nfinish = ["pr-merged", "ci-green"]\n'
    )
    directory = root / ".ai-dlc/work"
    directory.mkdir(parents=True)
    for work_id, providers in [
        ("one", {}),
        ("two", {"tracker": "old"}),
        ("spec", {"specs": "openspec"}),
    ]:
        work = {
            "schema": 1,
            "id": work_id,
            "title": work_id,
            "scope": "scope",
            "requires_spec": False,
            "spec_reason": "fixture",
            "acceptance": ["verified"],
            "reviewed": True,
            "providers": providers,
            "artifacts": {"tracker": f"OLD-{work_id}", "pr": "pull/7", "spec": "change"},
        }
        (directory / f"{work_id}.toml").write_text("# work comment\n" + tomli_w.dumps(work))
    env = {
        key: str(tmp_path / key) for key in ["XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME"]
    }
    registry = Registry()
    adapter = Tickets()
    registry.register("destination", adapter)
    return root, env, registry, adapter


def files(root):
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in [root / "ai-dlc.toml", *sorted((root / ".ai-dlc/work").glob("*.toml"))]
    }


def plan(checkout, **options):
    root, env, registry, _ = checkout
    return migration().plan_tracker_migration(
        root, "destination", environ=env, registry=registry, **options
    )


def apply(checkout, value, **options):
    root, env, registry, _ = checkout
    return migration().apply_tracker_migration(
        root, value, environ=env, registry=registry, **options
    )


def test_default_preview_is_pure_and_switch_freezes_only_inherited_bindings(checkout):
    root, env, _, adapter = checkout
    before = files(root)
    service = WorkService(
        root, resolve_runtime(root, environ=env).values, state_path=root.parent / "state"
    )
    effective = service.load("one")
    proposed = plan(checkout, mode="default-only")
    assert files(root) == before
    assert not (root / ".ai-dlc/migrations").exists()
    result = apply(checkout, proposed)
    assert result["status"] == "applied"
    changed = files(root)
    assert changed["ai-dlc.toml"] == before["ai-dlc.toml"].replace(
        b'tracker = "old"', b'tracker = "destination"'
    )
    frozen = tomllib.loads(changed[".ai-dlc/work/one.toml"].decode())
    assert frozen["providers"] == effective["providers"]
    assert frozen["bindings"] == effective["bindings"]
    assert changed[".ai-dlc/work/two.toml"] == before[".ai-dlc/work/two.toml"]
    assert changed[".ai-dlc/work/spec.toml"] == before[".ai-dlc/work/spec.toml"]
    assert not adapter.calls


@pytest.mark.parametrize("kind", ["github-issues", "fixture-plane", "new-custom-tracker"])
def test_selected_mapping_preserves_unselected_bytes_and_records_verified_provenance(
    checkout, kind
):
    root, env, _, adapter = checkout
    source = root / "ai-dlc.toml"
    source.write_text(source.read_text().replace("fixture-plane", kind))
    before = files(root)
    proposed = plan(checkout, mode="selected", work_ids=["one"], mappings={"one": "42"})
    assert files(root) == before
    assert proposed["mappings"]["one"]["target"]["id"] == "T42"
    result = apply(checkout, proposed)
    after = files(root)
    updated = tomllib.loads(after[".ai-dlc/work/one.toml"].decode())
    assert updated["providers"]["tracker"] == "destination"
    assert updated["artifacts"] == {"tracker": "42", "pr": "pull/7", "spec": "change"}
    assert len(updated["bindings"]["tracker"]) == 64
    for name in before.keys() - {".ai-dlc/work/one.toml"}:
        assert after[name] == before[name]
    receipt = json.loads((root / result["receipt"]).read_text())
    assert receipt["plan"]["mappings"]["one"]["source"]["reference"] == "OLD-one"
    assert receipt["plan"]["mappings"]["one"]["requested_reference"] == "42"
    assert receipt["plan"]["mappings"]["one"]["target"]["id"] == "T42"
    assert adapter.calls == ["read", "read"]
    WorkService(
        root, resolve_runtime(root, environ=env).values, state_path=root.parent / "state"
    ).load("one")


@pytest.mark.parametrize(
    "options",
    [
        {"mode": "selected", "work_ids": ["one"], "mappings": {}},
        {"mode": "selected", "work_ids": ["missing"], "mappings": {"missing": "42"}},
        {
            "mode": "selected",
            "work_ids": ["one", "two"],
            "mappings": {"one": "42", "two": "url/42"},
        },
        {"mode": "selected", "work_ids": ["one"], "mappings": {"one": "wrong-project"}},
        {"mode": "default-only", "work_ids": ["one"]},
    ],
)
def test_invalid_or_duplicate_target_mapping_refuses_without_writes(checkout, options):
    before = files(checkout[0])
    with pytest.raises(ValueError):
        plan(checkout, **options)
    assert files(checkout[0]) == before


@pytest.mark.parametrize("drift", ["work", "added-work", "config", "target", "tamper"])
def test_saved_preview_refuses_drift_without_writes(checkout, drift):
    root, _, _, adapter = checkout
    proposed = plan(checkout, mode="selected", work_ids=["one"], mappings={"one": "42"})
    if drift == "work":
        with (root / ".ai-dlc/work/two.toml").open("a") as stream:
            stream.write("\n# edited\n")
    elif drift == "added-work":
        (root / ".ai-dlc/work/new.toml").write_text(
            (root / ".ai-dlc/work/two.toml").read_text().replace('id = "two"', 'id = "new"')
        )
    elif drift == "config":
        with (root / "ai-dlc.toml").open("a") as stream:
            stream.write("\n# edited\n")
    elif drift == "target":
        adapter.identities["42"] = "T99"
    else:
        proposed["provider"] = "old"
    before = files(root)
    with pytest.raises(ValueError, match="drift|changed|digest"):
        apply(checkout, proposed)
    assert files(root) == before


def test_drift_during_target_revalidation_is_detected_before_writes(checkout):
    root, _, _, adapter = checkout
    proposed = plan(checkout, mode="selected", work_ids=["one"], mappings={"one": "42"})
    adapter.on_read = lambda: (root / ".ai-dlc/work/two.toml").write_text(
        "# external replacement\n"
    )
    with pytest.raises(ValueError, match="changed|drift"):
        apply(checkout, proposed)
    assert (root / ".ai-dlc/work/two.toml").read_text() == "# external replacement\n"
    assert (
        tomllib.loads((root / ".ai-dlc/work/one.toml").read_text())["artifacts"]["tracker"]
        == "OLD-one"
    )


def test_second_work_write_failure_restores_the_batch_with_durable_evidence(checkout, monkeypatch):
    root, _, _, _ = checkout
    module = migration()
    before = files(root)
    proposed = plan(
        checkout, mode="selected", work_ids=["one", "two"], mappings={"one": "42", "two": "43"}
    )
    target_inode = (root / ".ai-dlc/work/two.toml").stat().st_ino
    original = module._write_bytes

    def fail_second(descriptor, data):
        if os.fstat(descriptor).st_ino == target_inode:
            raise OSError("disk failure before second work write")
        original(descriptor, data)

    monkeypatch.setattr(module, "_write_bytes", fail_second)
    result = apply(checkout, proposed)
    assert result["status"] == "rolled-back"
    assert files(root) == before
    receipt = json.loads((root / result["receipt"]).read_text())
    assert set(receipt["recovery"]) == {".ai-dlc/work/one.toml", ".ai-dlc/work/two.toml"}


@pytest.mark.parametrize("failure", ["partial", "replacement", "authored-in-place"])
def test_unknown_outcome_retains_evidence_and_refuses_future_migration(
    checkout, monkeypatch, failure
):
    root, _, _, _ = checkout
    module = migration()
    proposed = plan(
        checkout, mode="selected", work_ids=["one", "two"], mappings={"one": "42", "two": "43"}
    )
    first = root / ".ai-dlc/work/one.toml"
    second_inode = (root / ".ai-dlc/work/two.toml").stat().st_ino
    original = module._write_bytes

    def uncertain(descriptor, data):
        if os.fstat(descriptor).st_ino == second_inode:
            if failure == "partial":
                os.pwrite(descriptor, b"unknown partial write", 0)
            elif failure == "replacement":
                authored = root / "authored.toml"
                authored.write_text("# replacement belongs to user\n")
                authored.replace(first)
            else:
                first.write_text("# replacement belongs to user\n")
            raise OSError("outcome uncertain")
        original(descriptor, data)

    monkeypatch.setattr(module, "_write_bytes", uncertain)
    result = apply(checkout, proposed)
    assert result["status"] == "recovery-required"
    if failure != "partial":
        assert first.read_text() == "# replacement belongs to user\n"
    assert (root / result["receipt"]).exists()
    with pytest.raises(ValueError, match="recovery required"):
        apply(checkout, proposed)
    inspection = module.inspect_tracker_migration(root, proposed["operation_id"])
    assert inspection["status"] == "recovery-required"
    assert any(row["state"] == "changed" for row in inspection["files"].values())


def test_crash_after_first_write_is_visible_on_next_attempt(checkout, monkeypatch):
    root, _, _, _ = checkout
    module = migration()
    proposed = plan(
        checkout, mode="selected", work_ids=["one", "two"], mappings={"one": "42", "two": "43"}
    )
    original = module._write_bytes
    first_inode = (root / ".ai-dlc/work/one.toml").stat().st_ino

    def interrupted(descriptor, data):
        original(descriptor, data)
        if os.fstat(descriptor).st_ino == first_inode:
            raise KeyboardInterrupt("process interrupted after write")

    monkeypatch.setattr(module, "_write_bytes", interrupted)
    with pytest.raises(KeyboardInterrupt):
        apply(checkout, proposed)
    with pytest.raises(ValueError, match="recovery required"):
        apply(checkout, proposed)
    inspection = module.inspect_tracker_migration(root, proposed["operation_id"])
    assert inspection["status"] == "recovery-required"
    assert {row["state"] for row in inspection["files"].values()} == {"before", "after"}


def test_cli_saves_and_applies_exact_preview_and_rejects_combined_new_intent(checkout, monkeypatch):
    from ai_dlc.cli import app

    root, env, registry, _ = checkout
    module = migration()
    original = module.Registry
    monkeypatch.setattr(module, "Registry", lambda *args, **kwargs: registry)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    runner = CliRunner()
    target = ".ai-dlc/local/move.json"
    mapping_file = root / "mapping.toml"
    mapping_file.write_text('[one]\ntracker = "42"\n')
    preview = runner.invoke(
        app,
        [
            "project",
            "tracker-migrate",
            "destination",
            "--mode",
            "selected",
            "--work",
            "one",
            "--mappings",
            str(mapping_file),
            "--save-plan",
            target,
            "--root",
            str(root),
        ],
    )
    assert preview.exit_code == 0, preview.output
    saved = json.loads((root / target).read_text())
    refused = runner.invoke(
        app,
        ["project", "tracker-migrate", "destination", "--apply-plan", target, "--root", str(root)],
    )
    assert refused.exit_code == 2
    applied = runner.invoke(
        app, ["project", "tracker-migrate", "--apply-plan", target, "--root", str(root)]
    )
    assert applied.exit_code == 0, applied.output
    assert json.loads(applied.stdout)["operation_id"] == saved["operation_id"]
    monkeypatch.setattr(module, "Registry", original)


def test_real_enrollment_preserves_inherited_alias_and_detects_account_drift(checkout):
    from test_config import _write_enrollment

    from ai_dlc.enrollment import EnrollmentPaths

    root, env, registry, _ = checkout
    paths = EnrollmentPaths.from_environment(environ=env)
    _write_enrollment(
        paths,
        content=b'schema=4\nprofile_id="personal-profile"\n[roles]\ntracker="inherited"\n[providers.inherited]\nkind="linear"\nteam_id="original-team"\n',
        machine='schema=4\n[providers.inherited]\naccount="primary"\n[accounts.primary]\nidentity="first"\n',
    )
    source = root / "ai-dlc.toml"
    source.write_text(source.read_text().replace('tracker = "old" # retain alias\n', ""))
    proposed = plan(checkout, mode="default-only")
    assert proposed["retained"]["one"]["providers"]["tracker"] == "inherited"
    assert "first" not in json.dumps(proposed)
    machine = paths.machine_file("workstation-01")
    machine.write_text(machine.read_text().replace('identity="first"', 'identity="second"'))
    before = files(root)
    with pytest.raises(ValueError, match="runtime drift"):
        apply(checkout, proposed)
    assert files(root) == before
    proposed = plan(checkout, mode="default-only")
    assert apply(checkout, proposed)["status"] == "applied"
    frozen = tomllib.loads((root / ".ai-dlc/work/one.toml").read_text())
    assert frozen["providers"]["tracker"] == "inherited"
    WorkService(
        root,
        resolve_runtime(root, environ=env).values,
        state_path=root.parent / "state",
        registry=registry,
    ).load("one")


def test_explicit_machine_mapping_uses_runtime_precedence_and_validated_scopes(checkout):
    root, env, registry, _ = checkout
    machine_config = {
        "schema": 4,
        "providers": {"old": {"account": "primary"}},
        "accounts": {"primary": {"identity": "first"}},
    }
    proposed = migration().plan_tracker_migration(
        root,
        "destination",
        mode="default-only",
        environ=env,
        registry=registry,
        machine_config=machine_config,
    )
    changed = copy.deepcopy(machine_config)
    changed["accounts"]["primary"]["identity"] = "second"
    with pytest.raises(ValueError, match="runtime drift"):
        apply(checkout, proposed, machine_config=changed)
    assert apply(checkout, proposed, machine_config=machine_config)["status"] == "applied"
    with pytest.raises(ValueError, match="machine"):
        migration().plan_tracker_migration(
            root,
            "destination",
            mode="default-only",
            environ=env,
            registry=registry,
            machine_config={"schema": 4, "roles": {"tracker": "other"}},
        )


def test_explicit_machine_mapping_replaces_enrolled_machine(checkout):
    from test_config import _write_enrollment

    from ai_dlc.enrollment import EnrollmentPaths

    root, env, registry, _ = checkout
    paths = EnrollmentPaths.from_environment(environ=env)
    _write_enrollment(
        paths,
        content=b'schema=4\nprofile_id="personal-profile"\n',
        machine='schema=4\n[accounts.enrolled]\nidentity="enrolled"\n[providers.old]\naccount="enrolled"\n',
    )
    override = {
        "schema": 4,
        "providers": {"old": {"account": "explicit"}},
        "accounts": {"explicit": {"identity": "explicit"}},
    }
    proposed = migration().plan_tracker_migration(
        root,
        "destination",
        mode="default-only",
        environ=env,
        registry=registry,
        machine_config=override,
    )
    paths.machine_file("workstation-01").write_text(
        'schema=4\n[accounts.enrolled]\nidentity="changed"\n'
    )
    assert apply(checkout, proposed, machine_config=override)["status"] == "applied"


def test_recovery_resolution_requires_fully_known_restoration(checkout, monkeypatch):
    root = checkout[0]
    module = migration()
    before = files(root)
    proposed = plan(
        checkout, mode="selected", work_ids=["one", "two"], mappings={"one": "42", "two": "43"}
    )
    original = module._write_bytes
    inode = (root / ".ai-dlc/work/one.toml").stat().st_ino

    def crash(descriptor, data):
        original(descriptor, data)
        if os.fstat(descriptor).st_ino == inode:
            raise KeyboardInterrupt

    monkeypatch.setattr(module, "_write_bytes", crash)
    with pytest.raises(KeyboardInterrupt):
        apply(checkout, proposed)
    monkeypatch.setattr(module, "_write_bytes", original)
    with pytest.raises(ValueError, match="mixed|changed"):
        module.resolve_tracker_migration_recovery(root, proposed["operation_id"])
    for name, data in before.items():
        (root / name).write_bytes(data)
    result = module.resolve_tracker_migration_recovery(root, proposed["operation_id"])
    assert result["status"] == "rolled-back"
    fresh = plan(checkout, mode="selected", work_ids=["one"], mappings={"one": "42"})
    assert apply(checkout, fresh)["status"] == "applied"


@pytest.mark.parametrize("drift", ["unselected", "machine"])
def test_mid_batch_drift_never_reports_applied(checkout, monkeypatch, drift):
    root, env, registry, _ = checkout
    module = migration()
    machine = root.parent / "machine.toml"
    machine.write_text('schema=4\n[providers.old]\naccount="first"\n')
    before = files(root)
    proposed = module.plan_tracker_migration(
        root,
        "destination",
        mode="selected",
        work_ids=["one", "two"],
        mappings={"one": "42", "two": "43"},
        environ=env,
        registry=registry,
        machine=machine,
    )
    original = module._write_bytes
    first_inode = (root / ".ai-dlc/work/one.toml").stat().st_ino

    def change_after_first(descriptor, data):
        original(descriptor, data)
        if os.fstat(descriptor).st_ino == first_inode:
            if drift == "unselected":
                (root / ".ai-dlc/work/spec.toml").write_text("# concurrent external edit\n")
            else:
                machine.write_text('schema=4\n[providers.old]\naccount="second"\n')

    monkeypatch.setattr(module, "_write_bytes", change_after_first)
    result = apply(checkout, proposed, machine=machine)
    assert result["status"] == "rolled-back"
    assert (root / ".ai-dlc/work/one.toml").read_bytes() == before[".ai-dlc/work/one.toml"]
    assert (root / ".ai-dlc/work/two.toml").read_bytes() == before[".ai-dlc/work/two.toml"]
    if drift == "unselected":
        assert (root / ".ai-dlc/work/spec.toml").read_text() == "# concurrent external edit\n"


def test_missing_plan_fields_refused_as_validation_error(checkout):
    from ai_dlc.config import digest

    proposed = plan(checkout, mode="default-only")
    proposed.pop("mappings")
    proposed.pop("digest")
    proposed["digest"] = digest(proposed)
    with pytest.raises(ValueError, match="plan"):
        apply(checkout, proposed)


def test_recovery_treats_interrupted_result_write_as_unknown(checkout, monkeypatch):
    root = checkout[0]
    module = migration()
    proposed = plan(checkout, mode="selected", work_ids=["one"], mappings={"one": "42"})
    original = module._new_json

    def interrupted(root, name, value):
        if name.endswith(".result.json"):
            (root / name).write_text('{"status":')
            raise OSError("result write interrupted")
        original(root, name, value)

    monkeypatch.setattr(module, "_new_json", interrupted)
    with pytest.raises(OSError):
        apply(checkout, proposed)
    report = module.inspect_tracker_migration(root, proposed["operation_id"])
    assert report["status"] == "recovery-required"
    assert report["files"][".ai-dlc/work/one.toml"]["state"] == "after"
    with pytest.raises(ValueError, match="recovery required"):
        apply(checkout, proposed)


@pytest.mark.parametrize("link", ["file-symlink", "parent-symlink", "hardlink"])
def test_unsafe_source_aliases_are_refused(checkout, link):
    root = checkout[0]
    module = migration()
    target = root / ".ai-dlc/work/one.toml"
    outside = root.parent / "outside"
    if link == "file-symlink":
        target.rename(outside)
        target.symlink_to(outside)
    elif link == "parent-symlink":
        target.parent.rename(outside)
        target.parent.symlink_to(outside, target_is_directory=True)
    else:
        os.link(target, outside)
    before = outside.read_bytes() if outside.is_file() else None
    with pytest.raises((ValueError, OSError)):
        module.plan_tracker_migration(
            root, "destination", mode="default-only", environ=checkout[1], registry=checkout[2]
        )
    if before:
        assert outside.read_bytes() == before


def test_save_plan_never_overwrites_an_authored_path(checkout):
    root = checkout[0]
    module = migration()
    proposed = plan(checkout, mode="default-only")
    path = root / ".ai-dlc/local/plan.json"
    path.parent.mkdir()
    path.write_text("authored")
    with pytest.raises(FileExistsError):
        module.save_tracker_migration_plan(root, proposed, path)
    assert path.read_text() == "authored"


def test_rollback_descriptor_cannot_overwrite_a_late_pathname_replacement(checkout, monkeypatch):
    root = checkout[0]
    module = migration()
    before = files(root)
    proposed = plan(
        checkout, mode="selected", work_ids=["one", "two"], mappings={"one": "42", "two": "43"}
    )
    first = root / ".ai-dlc/work/one.toml"
    second_inode = (root / ".ai-dlc/work/two.toml").stat().st_ino
    original = module._write_bytes

    def replace_during_rollback(descriptor, data):
        if os.fstat(descriptor).st_ino == second_inode:
            raise OSError("second file fails")
        if data == before[".ai-dlc/work/one.toml"]:
            replacement = root / "external"
            replacement.write_text("user replacement during rollback")
            replacement.replace(first)
        original(descriptor, data)

    monkeypatch.setattr(module, "_write_bytes", replace_during_rollback)
    result = apply(checkout, proposed)
    assert result["status"] == "recovery-required"
    assert first.read_text() == "user replacement during rollback"


@pytest.mark.parametrize(
    "field,value", [("mappings", []), ("snapshot", []), ("work_ids", "one"), ("schema", True)]
)
def test_invalid_saved_plan_shapes_are_refused(checkout, field, value):
    from ai_dlc.config import digest

    proposed = plan(checkout, mode="selected", work_ids=["one"], mappings={"one": "42"})
    proposed[field] = value
    proposed.pop("digest")
    proposed["digest"] = digest(proposed)
    before = files(checkout[0])
    with pytest.raises(ValueError, match="plan"):
        apply(checkout, proposed)
    assert files(checkout[0]) == before


def test_non_tracker_provider_is_not_a_default_destination(checkout):
    root, env, _, _ = checkout
    with (root / "ai-dlc.toml").open("a") as stream:
        stream.write('\n[providers.documents]\nkind="openspec"\n')
    before = files(root)
    with pytest.raises(TypeError, match="tracker"):
        migration().plan_tracker_migration(root, "documents", mode="default-only", environ=env)
    assert files(root) == before


def test_shared_resolver_keeps_workflow_review_refusal_before_binding_validation(checkout):
    root, env, _, _ = checkout
    path = root / ".ai-dlc/work/one.toml"
    raw = tomllib.loads(path.read_text())
    raw["reviewed"] = False
    raw["bindings"] = {"tracker": "invalid-existing-binding"}
    path.write_text(tomli_w.dumps(raw))
    service = WorkService(
        root, resolve_runtime(root, environ=env).values, state_path=root.parent / "state"
    )
    with pytest.raises(ValueError, match="must be reviewed"):
        service.load("one", mutation=True)


def test_completed_migration_receipts_do_not_block_a_cloned_checkout(checkout):
    import shutil

    root, env, registry, _ = checkout
    first = plan(checkout, mode="default-only")
    assert apply(checkout, first)["status"] == "applied"
    clone = root.parent / "clone"
    shutil.copytree(root, clone)
    module = migration()
    proposed = module.plan_tracker_migration(
        clone,
        "destination",
        mode="selected",
        work_ids=["one"],
        mappings={"one": "42"},
        environ=env,
        registry=registry,
    )
    assert (
        module.apply_tracker_migration(clone, proposed, environ=env, registry=registry)["status"]
        == "applied"
    )


@pytest.mark.parametrize("value", [[], None, "unexpected", 42])
@pytest.mark.parametrize("suffix", ["result", "recovered"])
def test_non_object_outcome_events_require_recovery(checkout, value, suffix):
    root = checkout[0]
    proposed = plan(checkout, mode="selected", work_ids=["one"], mappings={"one": "42"})
    assert apply(checkout, proposed)["status"] == "applied"
    (root / f".ai-dlc/migrations/{proposed['operation_id']}.{suffix}.json").write_text(
        json.dumps(value)
    )
    report = migration().inspect_tracker_migration(root, proposed["operation_id"])
    assert report["status"] == "recovery-required"
    with pytest.raises(ValueError, match="recovery required"):
        apply(checkout, proposed)


@pytest.mark.parametrize("value", [[], None, {"schema": 1, "status": "prepared"}])
def test_malformed_prepared_receipt_reports_manual_recovery(checkout, value):
    root = checkout[0]
    proposed = plan(checkout, mode="default-only")
    path = root / f".ai-dlc/migrations/{proposed['operation_id']}.json"
    path.parent.mkdir()
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="receipt.*invalid"):
        migration().inspect_tracker_migration(root, proposed["operation_id"])
    with pytest.raises(ValueError, match="recovery required"):
        apply(checkout, proposed)
