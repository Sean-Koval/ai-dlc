"""Saved target creation and real local journal; transport is fixture-only."""

import copy
import importlib
import importlib.util
import json

import pytest
from test_tracker_migration import checkout, files  # noqa: F401 -- shared real project fixture

from ai_dlc.tracker_migration import apply_tracker_migration


def targets():
    assert importlib.util.find_spec("ai_dlc.tracker_targets"), (
        "Reviewed target reconciliation service is missing"
    )
    return importlib.import_module("ai_dlc.tracker_targets")


class TargetAdapter:
    def __init__(self):
        self.items = {}
        self.sent = []
        self.calls = []
        self.hide = False
        self.lose = False
        self.after_create = None

    def invoke(self, operation, payload):
        self.calls.append(operation)
        if operation == "find":
            return {
                "items": []
                if self.hide
                else [
                    row
                    for row in self.items.values()
                    if row["correlation"] == payload["correlation"]
                ]
            }
        if operation == "read":
            return next(
                row
                for row in self.items.values()
                if payload["reference"] in {row["id"], row["url"]}
            )
        assert operation == "create"
        self.sent.append(copy.deepcopy(payload))
        item = {
            "id": str(len(self.sent)),
            "url": "https://fixture/" + str(len(self.sent)),
            "state": "open",
            "correlation": payload["correlation"],
        }
        self.items[item["id"]] = item
        if self.after_create:
            self.after_create()
        if self.lose:
            raise RuntimeError("Response lost")
        return item


@pytest.fixture
def creation(checkout):  # noqa: F811 -- pytest resolves the imported shared fixture
    root, env, registry, _ = checkout
    adapter = TargetAdapter()
    registry.register("destination", adapter)
    return root, env, registry, adapter


def preview(creation, **kwargs):
    root, env, registry, _ = creation
    return targets().plan_tracker_targets(
        root,
        "destination",
        work_ids=["one"],
        create_work_ids=["one"],
        source="local-records",
        environ=env,
        registry=registry,
        **kwargs,
    )


def reconcile(creation, plan):
    root, env, registry, _ = creation
    return targets().reconcile_tracker_targets(root, plan, environ=env, registry=registry)


def test_preview_is_read_only_explicit_source_and_complete_payload(creation):
    root, _, _, adapter = creation
    before = files(root)
    planned = preview(creation)
    assert files(root) == before and adapter.calls == []
    assert planned["source"]["basis"] == "local-records-only"
    assert planned["creates"]["one"]["payload"]["title"]
    assert "verified" in planned["creates"]["one"]["payload"]["body"]
    with pytest.raises(ValueError, match="source"):
        targets().plan_tracker_targets(
            root,
            "destination",
            work_ids=["one"],
            create_work_ids=["one"],
            source="remote-complete",
            environ=creation[1],
            registry=creation[2],
        )


def test_saved_reconciliation_never_binds_before_separate_local_apply(creation):
    root, env, registry, adapter = creation
    before = files(root)
    planned = preview(creation)
    path = targets().save_tracker_targets_plan(root, planned, ".ai-dlc/local/create.json")
    with pytest.raises(FileExistsError):
        targets().save_tracker_targets_plan(root, planned, path)
    result = reconcile(creation, path)
    assert result["status"] == "resolved"
    assert files(root) == before
    assert len(adapter.sent) == 1
    assert reconcile(creation, path)["targets"] == result["targets"]
    assert len(adapter.sent) == 1
    applied = apply_tracker_migration(
        root, result["migration_plan"], environ=env, registry=registry
    )
    receipt = json.loads((root / applied["receipt"]).read_text())
    assert receipt["plan"]["evidence"]["creation"]["intent_digest"] == planned["digest"]
    assert applied["status"] == "applied"


def test_uncertain_absence_never_resends_then_visible_target_reconciles(creation):
    _, _, _, adapter = creation
    planned = preview(creation)
    adapter.hide = adapter.lose = True
    assert reconcile(creation, planned)["status"] == "unresolved"
    assert reconcile(creation, planned)["status"] == "unresolved"
    assert len(adapter.sent) == 1
    adapter.hide = False
    assert reconcile(creation, planned)["status"] == "resolved"
    assert len(adapter.sent) == 1


def test_local_conflict_retains_created_target_and_stale_retry_only_reads(creation):
    root, _, _, adapter = creation
    planned = preview(creation)
    path = root / ".ai-dlc/work/two.toml"
    adapter.after_create = lambda: path.write_text(path.read_text() + "\n# authored edit\n")
    result = reconcile(creation, planned)
    assert result["status"] == "local-conflict"
    assert result["migration_plan"] is None and result["targets"]["one"]["id"] == "1"
    assert reconcile(creation, planned)["status"] == "local-conflict"
    assert len(adapter.sent) == 1


def test_fingerprint_conflict_is_refused_before_read_reuse(creation):
    from ai_dlc.config import digest

    _, _, _, adapter = creation
    planned = preview(creation)
    reconcile(creation, planned)
    altered = copy.deepcopy(planned)
    altered["creates"]["one"]["payload"]["title"] = "changed"
    altered.pop("digest")
    altered["digest"] = digest(altered)
    before = list(adapter.calls)
    with pytest.raises(ValueError, match="payload conflict"):
        reconcile(creation, altered)
    assert adapter.calls == before


def test_stale_never_sent_intent_does_not_create(creation):
    root, _, _, adapter = creation
    planned = preview(creation)
    path = root / ".ai-dlc/work/two.toml"
    path.write_text(path.read_text() + "\n# edited\n")
    result = reconcile(creation, planned)
    assert result["migration_plan"] is None
    assert adapter.sent == []


def test_partial_batch_retains_targets_and_requires_all_before_local_plan(creation):
    root, env, registry, adapter = creation
    planned = targets().plan_tracker_targets(
        root,
        "destination",
        work_ids=["one", "two"],
        create_work_ids=["one", "two"],
        source="local-records",
        environ=env,
        registry=registry,
    )
    adapter.lose = True
    adapter.hide = True
    result = reconcile(creation, planned)
    assert result["migration_plan"] is None and result["status"] == "unresolved"
    assert len(adapter.sent) == 2
    adapter.hide = False
    assert reconcile(creation, planned)["status"] == "resolved"
    assert len(adapter.sent) == 2


def test_successful_create_retains_known_reference_when_readback_fails(creation):
    _, _, _, adapter = creation
    original = adapter.invoke

    def invoke(operation, payload):
        if operation == "read":
            raise RuntimeError("Read temporarily unavailable")
        return original(operation, payload)

    adapter.invoke = invoke
    planned = preview(creation)
    result = reconcile(creation, planned)
    assert result["status"] == "unresolved"
    assert result["retained_targets"]["one"]["id"] == "1"
    adapter.hide = True
    adapter.invoke = original
    assert reconcile(creation, planned)["status"] == "resolved"
    assert len(adapter.sent) == 1


def test_final_mapping_read_failure_still_reports_retained_target(creation):
    _, _, _, adapter = creation
    original = adapter.invoke
    reads = 0

    def invoke(operation, payload):
        nonlocal reads
        if operation == "read":
            reads += 1
            if reads == 2:
                raise RuntimeError("Final verification unavailable")
        return original(operation, payload)

    adapter.invoke = invoke
    result = reconcile(creation, preview(creation))
    assert result["status"] == "unresolved" and result["migration_plan"] is None
    assert result["retained_targets"]["one"]["id"] == "1"
    assert len(adapter.sent) == 1


def test_cli_has_distinct_saved_creation_and_reconciliation_actions(creation, monkeypatch):
    from typer.testing import CliRunner

    from ai_dlc.cli import app
    from ai_dlc.providers import Registry

    root, env, registry, _ = creation
    original = Registry.get
    monkeypatch.setattr(
        Registry,
        "get",
        lambda self, key: original(registry, key) if key == "destination" else original(self, key),
    )
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    runner = CliRunner()
    preview_result = runner.invoke(
        app,
        [
            "project",
            "tracker-create-plan",
            "destination",
            "--root",
            str(root),
            "--work",
            "one",
            "--create",
            "one",
            "--source",
            "local-records",
            "--save-plan",
            ".ai-dlc/local/create.json",
        ],
    )
    assert preview_result.exit_code == 0, preview_result.output
    reconcile_result = runner.invoke(
        app,
        [
            "project",
            "tracker-reconcile",
            "--root",
            str(root),
            "--plan",
            ".ai-dlc/local/create.json",
            "--save-plan",
            ".ai-dlc/local/mapped.json",
        ],
    )
    assert reconcile_result.exit_code == 0, reconcile_result.output
    assert (root / ".ai-dlc/local/mapped.json").is_file()
    refused = runner.invoke(
        app,
        [
            "project",
            "tracker-reconcile",
            "--root",
            str(root),
            "--plan",
            ".ai-dlc/local/create.json",
            "--create",
            "two",
        ],
    )
    assert refused.exit_code != 0


def _competing_reconciler(root, env, plan, start, output):
    import time
    from pathlib import Path

    from ai_dlc.config import resolve_runtime
    from ai_dlc.providers import Registry
    from ai_dlc.tracker_targets import reconcile_tracker_targets

    class Transport:
        def invoke(self, operation, payload):
            if operation == "find":
                return {"items": []}
            if operation == "create":
                with (Path(root) / "sent.log").open("a") as stream:
                    stream.write(payload["operation_id"] + "\n")
                    stream.flush()
                time.sleep(0.1)
            return {"id": "one", "url": "https://fixture/one", "state": "open"}

    registry = Registry(resolve_runtime(root, environ=env).values, root=root, environ=env)
    registry.register("destination", Transport())
    start.wait(5)
    try:
        output.put(reconcile_tracker_targets(root, plan, environ=env, registry=registry)["status"])
    except Exception as exc:  # noqa: BLE001 -- report child failures to the bounded parent
        output.put(type(exc).__name__ + ": " + str(exc))


def test_competing_processes_send_only_once_per_saved_intent(creation):
    import multiprocessing

    root, env, _, _ = creation
    planned = preview(creation)
    context = multiprocessing.get_context("spawn")
    start, output = context.Event(), context.Queue()
    workers = [
        context.Process(target=_competing_reconciler, args=(root, env, planned, start, output))
        for _ in range(2)
    ]
    try:
        for worker in workers:
            worker.start()
        start.set()
        results = [output.get(timeout=12) for _ in workers]
        for worker in workers:
            worker.join(timeout=5)
        assert all(worker.exitcode == 0 for worker in workers)
        assert "resolved" in results and set(results) <= {"resolved", "unresolved"}
        assert len((root / "sent.log").read_text().splitlines()) == 1
    finally:
        for worker in workers:
            if worker.is_alive():
                worker.terminate()
                worker.join(timeout=5)
        output.close()


@pytest.mark.parametrize("damage", ["digest", "source", "root", "symlink", "fifo"])
def test_unsafe_saved_intent_refuses_without_provider_calls(creation, damage):
    import os

    from ai_dlc.config import digest

    root, _, _, adapter = creation
    planned = preview(creation)
    if damage in {"symlink", "fifo"}:
        folder = root / ".ai-dlc/local"
        folder.mkdir()
        path = folder / "intent.json"
        if damage == "symlink":
            outside = root / "outside.json"
            outside.write_text(json.dumps(planned))
            path.symlink_to(outside)
        else:
            os.mkfifo(path)
        target = str(path)
    else:
        if damage == "digest":
            planned["digest"] = "bad"
        elif damage == "source":
            planned["source"]["complete_import"] = True
        else:
            planned["root_digest"] = digest("elsewhere")
        if damage != "digest":
            planned.pop("digest")
            planned["digest"] = digest(planned)
        target = planned
    with pytest.raises((OSError, ValueError)):
        reconcile(creation, target)
    assert adapter.calls == []


def test_existing_and_created_targets_must_all_verify_before_binding(creation):
    root, env, registry, adapter = creation
    adapter.items["existing"] = {
        "id": "existing",
        "url": "https://fixture/existing",
        "state": "cancelled",
        "correlation": "unrelated",
    }
    planned = targets().plan_tracker_targets(
        root,
        "destination",
        work_ids=["one", "two"],
        create_work_ids=["one"],
        mappings={"two": "existing"},
        source="local-records",
        environ=env,
        registry=registry,
    )
    before = files(root)
    result = reconcile(creation, planned)
    assert result["status"] == "resolved" and files(root) == before
    assert result["migration_plan"]["evidence"]["targets"]["two"]["state"] == "cancelled"
    assert len(adapter.sent) == 1


def test_later_local_transaction_failure_keeps_created_target(creation, monkeypatch):
    import ai_dlc.tracker_migration as migration

    root, env, registry, adapter = creation
    planned = preview(creation)
    result = reconcile(creation, planned)
    before = files(root)
    original = migration._write_bytes
    failed = False

    def write(descriptor, data):
        nonlocal failed
        if b'tracker = "destination"' in data and not failed:
            failed = True
            raise OSError("Fixture local write failure")
        original(descriptor, data)

    monkeypatch.setattr(migration, "_write_bytes", write)
    outcome = apply_tracker_migration(
        root, result["migration_plan"], environ=env, registry=registry
    )
    assert outcome["status"] == "rolled-back"
    assert files(root) == before and len(adapter.sent) == 1
    assert reconcile(creation, planned)["targets"] == result["targets"]
    assert len(adapter.sent) == 1


def test_non_runtime_transport_failure_stays_uncertain_and_never_retries(creation):
    import httpx

    _, _, _, adapter = creation
    original = adapter.invoke

    def invoke(operation, payload):
        result = original(operation, payload)
        if operation == "create":
            raise httpx.ReadTimeout("Fixture transport response lost")
        return result

    adapter.invoke = invoke
    adapter.hide = True
    planned = preview(creation)
    assert reconcile(creation, planned)["status"] == "unresolved"
    assert reconcile(creation, planned)["status"] == "unresolved"
    assert len(adapter.sent) == 1


def test_unresolved_local_migration_blocks_new_target_send(creation):
    root, _, _, adapter = creation
    planned = preview(creation)
    pending = root / ".ai-dlc/migrations"
    pending.mkdir()
    (pending / ("a" * 32 + ".json")).write_text("{}")
    result = reconcile(creation, planned)
    assert result["status"] == "unresolved"
    assert "recovery required" in result["unresolved"]["one"].lower()
    assert adapter.sent == []
