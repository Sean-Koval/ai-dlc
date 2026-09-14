"""Reviewed work, reconciled provider mutations, and evidence-gated completion."""

import hashlib
import json
import os
import re
import tomllib
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

import tomli_w
from pydantic import BaseModel, ConfigDict, Field, field_validator

from ai_dlc.config import digest as config_digest
from ai_dlc.config import load_project, read_toml, resolve_layers, resolve_runtime
from ai_dlc.errors import RefusedError, UncertainError
from ai_dlc.files import inside, run_git
from ai_dlc.locking import project_write_lock
from ai_dlc.providers import Registry
from ai_dlc.providers.openspec import OpenSpecProvider
from ai_dlc.providers.scm import GitHubSCM
from ai_dlc.work.journal import Journal
from ai_dlc.work.traceability import (
    artifact_is_local,
    draft_issue_fields,
    render_pull_request_body,
    render_ticket_body,
    validate_work_graph,
)


class Work(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    schema_version: int = Field(alias="schema", ge=1, le=1)
    id: str
    title: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    requires_spec: bool
    spec_reason: str = Field(min_length=1)
    acceptance: list[str] = Field(min_length=1)
    reviewed: bool = False
    depends_on: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    providers: dict[str, str] = Field(default_factory=dict)
    artifacts: dict[str, str] = Field(default_factory=dict)
    bindings: dict[str, str] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def safe_id(cls, value):
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,99}", value):
            raise ValueError("Unsafe work ID")
        return value

    @field_validator("title", "scope", "spec_reason")
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError("Work text cannot be empty")
        return value

    @field_validator("requirements")
    @classmethod
    def requirement_ids(cls, value):
        if any(
            not item or not item.isprintable() or any(c.isspace() for c in item) for item in value
        ):
            raise ValueError("Requirement references must be nonempty single-token identifiers")
        return value

    @field_validator("acceptance")
    @classmethod
    def criteria(cls, value):
        if any(not s.strip() for s in value):
            raise ValueError("Acceptance criteria cannot be empty")
        return value


def project_source_digest(root: Path) -> str | None:
    """Canonical digest of the authored ai-dlc.toml, or None when it is absent."""
    project_file = root / "ai-dlc.toml"
    if not project_file.is_file():
        return None
    return config_digest(tomllib.loads(project_file.read_text()))


_BINDING_ROLES = {"specs", "tracker", "scm", "deploy", "knowledge"}
_UNSET_SOURCE = object()


def _matches_project_layer(actual, project_value) -> bool:
    if isinstance(project_value, dict) and ("add" in project_value or "remove" in project_value):
        if not isinstance(actual, list):
            return False
        key = lambda item: item["id"] if isinstance(item, dict) else item
        present = {key(item) for item in actual}
        added = {key(item) for item in project_value.get("add", [])}
        removed = set(project_value.get("remove", []))
        return added <= present and not removed & present
    if isinstance(project_value, dict):
        return isinstance(actual, dict) and all(
            key in actual and _matches_project_layer(actual[key], value)
            for key, value in project_value.items()
        )
    return type(actual) is type(project_value) and actual == project_value


def _validate_binding_config(root: Path, config: dict) -> None:
    project_file = root / "ai-dlc.toml"
    if not project_file.is_file():
        return
    source = read_toml(project_file)
    resolve_layers([("project", source)])
    project_roles = source.get("roles", {})
    actual_roles = config.get("roles", {})
    if not isinstance(project_roles, dict) or not isinstance(actual_roles, dict):
        raise TypeError("Work service configuration does not match current project source")
    for role in _BINDING_ROLES & project_roles.keys():
        if role not in actual_roles or not _matches_project_layer(
            actual_roles[role], project_roles[role]
        ):
            raise ValueError("Work service configuration does not match current project source")
    actual_providers = config.get("providers", {})
    for provider_id, project_settings in source.get("providers", {}).items():
        actual = actual_providers.get(provider_id)
        if not isinstance(actual, dict) or not _matches_project_layer(actual, project_settings):
            raise ValueError("Work service configuration does not match current project source")
    for field in ("scm", "deploy"):
        if field in source and not _matches_project_layer(config.get(field), source[field]):
            raise ValueError("Work service configuration does not match current project source")


# Receipt artifact names are evidence policy, not provider identity: the finish gate
# reads the expected names from the manifest at the merged revision, never from a
# binding, so hashing them would invalidate every record whenever the CI matrix
# changes without protecting anything. Every other key stays in the identity so an
# unrecognised setting cannot silently bypass the drift guard.
SCM_EVIDENCE_POLICY_KEYS = frozenset({"receipt_artifact", "receipt_artifacts"})


def _scm_identity(scm: dict) -> dict:
    """Project SCM configuration onto the settings that decide which service is trusted."""
    return {key: value for key, value in scm.items() if key not in SCM_EVIDENCE_POLICY_KEYS}


def resolve_work(raw: dict, config: dict, work_id: str, *, require_review: bool = False) -> dict:
    """Resolve effective work providers and validate fingerprints without local writes."""
    aliases = {"specification": "specs", "deployment": "deploy"}
    raw = dict(raw)
    source = raw.get("providers") or config.get("roles", {})
    raw["providers"] = {
        aliases.get(k, k): v
        for k, v in source.items()
        if aliases.get(k, k) in {"specs", "tracker", "scm", "deploy", "knowledge"}
    }
    work = Work.model_validate(raw).model_dump(by_alias=True)
    if work["id"] != work_id:
        raise ValueError("Work ID does not match filename")
    if require_review and not work["reviewed"]:
        raise ValueError("Work must be reviewed before mutation")
    defaults = {
        "specs": "openspec",
        "scm": "github",
        "deploy": "github-deployment",
        "knowledge": "obsidian",
    }
    for role, provider_id in {**defaults, **work["providers"]}.items():
        cfg = config.get("providers", {}).get(provider_id, {})
        identity = {"provider_id": provider_id, "configuration": cfg}
        # A vault's machine path is not its logical provider identity. Configure
        # providers.<id>.vault_id when distinct vaults must retain distinct bindings.
        if role in {"scm", "deploy"} or cfg.get("kind", provider_id) == "github-issues":
            identity["scm"] = _scm_identity(config.get("scm", {}))
        if role == "deploy":
            identity["deploy"] = config.get("deploy", {})
        account = cfg.get("account")
        if account:
            identity["account"] = config.get("accounts", {}).get(account, {})
        fingerprint = config_digest(identity)
        existing = work["bindings"].get(role)
        if existing and existing != fingerprint:
            raise ValueError(
                f"Provider binding drift for {role}; explicitly review and rebind work"
            )
        work["bindings"][role] = fingerprint
    return work


def read_work_graph(root: Path, config: dict, work_id: str) -> tuple[dict[str, dict], list[str]]:
    """Inspect only the selected dependency closure, without journals or provider calls."""
    records = {}
    errors = []
    pending = [work_id]
    attempted = set()
    while pending:
        current = pending.pop()
        if current in attempted:
            continue
        attempted.add(current)
        try:
            Work.safe_id(current)
            path = inside(root, f".ai-dlc/work/{current}.toml")
            record = resolve_work(tomllib.loads(path.read_text()), config, current)
        except (OSError, ValueError) as exc:
            errors.append(f"Work {current}: {exc}")
            continue
        records[current] = record
        # Validate before traversing IDs so no invalid dependency can become a path.
        for dependency in record["depends_on"]:
            try:
                Work.safe_id(dependency)
            except ValueError as exc:
                errors.append(f"Work {current}: dependency {dependency!r}: {exc}")
            else:
                pending.append(dependency)
        errors.extend(f"Work {current}: {error}" for error in validate_artifacts(root, record))
    errors.extend(validate_work_graph(records))
    return records, sorted(set(errors))


def _anchored(root: Path, path: str) -> bool:
    """Whether a relative reference's leading segment is an entry of the repository root."""
    parts = PurePosixPath(path).parts
    if not parts or parts[0] in {".", ".."}:
        return False
    entry = root / parts[0]
    # A dangling symlink is still a local entry; it must reach inside() rather than
    # masquerade as an opaque ID.
    return entry.exists() or entry.is_symlink()


def validate_artifacts(root: Path, record: dict) -> list[str]:
    """Check a record's local artifact references without probing provider-owned ones.

    The repository anchor, not the referenced leaf, decides whether a suffix-less
    specification path is local, so a change directory that archiving moved away is
    reported as absent instead of silently becoming an opaque provider ID.
    """
    errors = []
    for kind, reference in record["artifacts"].items():
        try:
            parsed = urlsplit(reference)
            anchored = kind == "spec" and not parsed.scheme and _anchored(root, parsed.path)
            if not artifact_is_local(kind, reference, anchored=anchored):
                continue
            if parsed.scheme or parsed.netloc or parsed.query or not parsed.path.strip():
                raise ValueError("Expected a local artifact path or HTTP(S) reference")
            target = inside(root, parsed.path)
            if not target.is_file() and not target.is_dir():
                raise ValueError("Referenced local artifact is absent")
        except (OSError, ValueError) as exc:
            errors.append(f"artifact {kind} ({reference}): {exc}")
    return errors


def validate_work(root: Path, config: dict, work_id: str) -> dict:
    records, errors = read_work_graph(Path(root).resolve(), config, work_id)
    return {
        "valid": not errors,
        "work_id": work_id,
        "dependencies": sorted(set(records) - {work_id}),
        "errors": errors,
    }


CONTEXT_NEXT = (
    "Select work; prepare specification when required; publish/start; check; finish; handoff."
)


def build_context(root: Path, brief: bool = False) -> dict:
    """Offline session context: local work records and the required checks.

    Records are read as written, without validation, so a malformed record still
    appears; ``brief`` keeps only the three most recent by filename order. Nothing is
    probed outside the repository tree.
    """
    config = load_project(root)
    records = []
    for path in sorted((root / ".ai-dlc/work").glob("*.toml")):
        record = read_toml(path)
        records.append({k: record.get(k) for k in ["id", "title", "artifacts", "providers"]})
    return {
        "work": records[-3:] if brief else records,
        "required": config.get("checks", {}).get("required", []),
        "next": CONTEXT_NEXT,
    }


def read_work_records(root: Path) -> tuple[dict[str, dict], list[str]]:
    """Read every record under .ai-dlc/work: shape, local artifacts and the graph.

    Provider bindings are deliberately not resolved. Binding drift is a mutation-time
    refusal for the record being changed, and finished records keep their historical
    fingerprints, so a repository-wide invariant cannot include it. Nothing is probed
    outside the repository tree.
    """
    records: dict[str, dict] = {}
    errors: list[str] = []
    directory = root / ".ai-dlc/work"
    if not directory.is_dir():
        return records, errors
    for path in sorted(directory.glob("*.toml")):
        work_id = path.stem
        try:
            Work.safe_id(work_id)
            record = Work.model_validate(tomllib.loads(path.read_text())).model_dump(by_alias=True)
            if record["id"] != work_id:
                raise ValueError("Work ID does not match filename")
        except (OSError, ValueError) as exc:
            errors.append(f"Work {work_id}: {exc}")
            continue
        records[work_id] = record
        errors.extend(f"Work {work_id}: {error}" for error in validate_artifacts(root, record))
    errors.extend(validate_work_graph(records))
    return records, sorted(set(errors))


def validate_work_records(root: Path) -> dict:
    """Validate every work record together so a dangling artifact fails a required check."""
    records, errors = read_work_records(Path(root).resolve())
    return {"valid": not errors, "records": sorted(records), "errors": errors}


class WorkService:
    @classmethod
    def from_project(
        cls,
        root: Path,
        *,
        machine: Path | None = None,
        state_path: Path | None = None,
        registry: Registry | None = None,
    ):
        root = Path(root).resolve()
        with project_write_lock(root):
            source_digest = project_source_digest(root)
            config = resolve_runtime(root, machine=machine).values
            return cls(
                root,
                config,
                state_path=state_path,
                registry=registry,
                _source_digest=source_digest,
            )

    def __init__(
        self,
        root: Path,
        config: dict,
        state_path: Path | None = None,
        registry: Registry | None = None,
        *,
        _source_digest: str | None | object = _UNSET_SOURCE,
    ):
        self.root = Path(root).resolve()
        with project_write_lock(self.root):
            current_digest = project_source_digest(self.root)
            if _source_digest is _UNSET_SOURCE:
                _validate_binding_config(self.root, config)
            elif _source_digest != current_digest:
                raise ValueError("Work service configuration does not match current project source")
            self.project_source_digest = current_digest
            self.config = config
            state = (
                Path(state_path)
                if state_path
                else Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "ai-dlc"
            )
            self._journal_path = state / "operations.sqlite3"
            self._journal: Journal | None = None
            self.registry = registry or Registry(config, root=self.root)

    @property
    def journal(self):
        if self._journal is None:
            self._journal = Journal(self._journal_path)
        return self._journal

    def new(
        self,
        work_id,
        *,
        tracker_reference=None,
        title=None,
        scope=None,
        requires_spec=None,
        spec_reason=None,
        acceptance=None,
    ):
        """Create a local unreviewed draft without publishing or opening a journal."""
        Work.safe_id(work_id)
        with project_write_lock(self.root):
            self._check_source()
            path = inside(self.root, f".ai-dlc/work/{work_id}.toml")
            if path.exists():
                raise RefusedError(f"Work record already exists: {work_id}")
            providers = {
                role: provider
                for role, provider in self.config.get("roles", {}).items()
                if role in {"specs", "tracker", "knowledge", "scm", "deploy"}
            }
            item = {}
            if tracker_reference is not None:
                if not isinstance(tracker_reference, str) or not tracker_reference.strip():
                    raise RefusedError("Tracker reference cannot be empty")
                if not providers.get("tracker"):
                    raise RefusedError("Configure a tracker before using --from-issue")
                item = self.registry.get(providers["tracker"]).invoke(
                    "read", {"reference": tracker_reference}
                )
            derived = draft_issue_fields(item.get("body") or "")
            record = Work.model_validate(
                {
                    "schema": 1,
                    "id": work_id,
                    "title": title
                    if title is not None
                    else item.get("title") or "TODO: state title",
                    "scope": scope if scope is not None else derived["scope"],
                    "acceptance": acceptance if acceptance is not None else derived["acceptance"],
                    "requires_spec": requires_spec if requires_spec is not None else True,
                    "spec_reason": spec_reason
                    if spec_reason is not None
                    else "TODO: record the specification decision",
                    "reviewed": False,
                    "providers": providers,
                    "artifacts": {"tracker": tracker_reference}
                    if tracker_reference is not None
                    else {},
                    "requirements": [],
                    "depends_on": [],
                }
            ).model_dump(by_alias=True)
            self._check_source()
            path = inside(self.root, f".ai-dlc/work/{work_id}.toml")
            path.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive creation also refuses a concurrent non-cooperating writer.
            with path.open("x") as handle:
                handle.write(tomli_w.dumps(record))
            return record

    def load(self, work_id, mutation=False):
        if mutation:
            with project_write_lock(self.root):
                return self._load(work_id, mutation=True)
        return self._load(work_id, mutation=False)

    def _load(self, work_id, mutation=False):
        Work.safe_id(work_id)
        path = (self.root / ".ai-dlc/work" / f"{work_id}.toml").resolve()
        if not path.is_relative_to(self.root / ".ai-dlc/work"):
            raise ValueError("Unsafe work path")
        raw = tomllib.loads(path.read_text())
        work = resolve_work(raw, self.config, work_id, require_review=mutation)
        if mutation:
            self.save(work)
        return work

    def _check_source(self):
        try:
            current_digest = project_source_digest(self.root)
        except (OSError, tomllib.TOMLDecodeError):
            raise ValueError("Project configuration changed; retry the work mutation") from None
        if current_digest != self.project_source_digest:
            raise ValueError("Project configuration changed; retry the work mutation")

    def save(self, work):
        path = self.root / ".ai-dlc/work" / f"{work['id']}.toml"
        with project_write_lock(self.root):
            self._check_source()
            tmp = path.with_suffix(".toml.tmp")
            tmp.write_text(tomli_w.dumps(work))
            tmp.replace(path)

    def op_id(self, work, action):
        repo = self.config.get("scm", {}).get("repository", str(self.root))
        identity = {"repository": repo, "work": work["id"], "action": action}
        if action != "work":
            role = {"handoff": "knowledge", "pr": "scm"}.get(action, "tracker")
            identity["provider"] = work["providers"].get(role)
            identity["binding"] = work["bindings"].get(role)
            if role == "knowledge":
                identity["artifact"] = work["artifacts"].get("knowledge", f"ai-dlc/{work['id']}.md")
            if role == "scm":
                identity["artifact"] = work["artifacts"].get("branch")
            if role == "tracker" and action != "publish":
                identity["artifact"] = work["artifacts"].get("tracker")
        return hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()

    def tracker(self, work):
        provider = work["providers"].get("tracker")
        if not provider:
            raise ValueError("Work has no pinned tracker provider")
        return self.registry.get(provider)

    def validate(self, work_id):
        return validate_work(self.root, self.config, work_id)

    def validated_records(self, work_id):
        self._check_source()
        records, errors = read_work_graph(self.root, self.config, work_id)
        if errors:
            raise ValueError("Work validation failed: " + "; ".join(errors))
        work = records[work_id]
        if not work["reviewed"]:
            raise ValueError("Work must be reviewed before mutation")
        return records

    def publish(self, work_id):
        with project_write_lock(self.root):
            return self._publish(work_id)

    def _publish(self, work_id):
        work = self.validated_records(work_id)[work_id]
        self.save(work)
        provider = self.tracker(work)
        operation_id = self.op_id(work, "publish")
        payload = {
            "title": work["title"],
            "body": render_ticket_body(work),
            "correlation": f"<!-- ai-dlc:{self.op_id(work, 'work')} -->",
            "operation_id": operation_id,
        }
        # Reconcile before comparing create payloads: legacy bodies and authored
        # remote edits do not change a work item's operation or provider identity.
        mapped = work["artifacts"].get("tracker")
        items = (
            [provider.invoke("read", {"reference": mapped})]
            if mapped
            else provider.invoke("find", {"correlation": payload["correlation"]})["items"]
        )
        if len(items) > 1:
            raise ValueError("Duplicate correlation conflict")
        record = self.journal.lookup(operation_id)
        if items:
            item = items[0]
        elif record and record["status"] == "succeeded":
            item = provider.invoke("read", {"reference": record["result"]["id"]})
        elif record:
            raise RuntimeError(
                "Creation remains uncertain; remote correlation not yet visible; refusing duplicate retry"
            )
        else:
            self.journal.begin(operation_id, {"provider": work["providers"]["tracker"], **payload})
            try:
                item = provider.invoke("create", payload)
            except Exception:
                self.journal.uncertain(operation_id)
                raise
        if record is None and items:
            self.journal.begin(operation_id, {"provider": work["providers"]["tracker"], **payload})
        self.journal.succeed(operation_id, item)
        work["artifacts"]["tracker"] = item["id"]
        self.save(work)
        if self.optional_tracker_operation(work, "prepare"):
            item = self.mutate(
                work, "prepare", "prepare", {"reference": item["id"]}, reconcile=True
            )
        return {"status": "published", "work_id": work_id, "tracker": item}

    def link(self, work_id, artifact_kind, reference, *, commit=True):
        work = self.load(work_id, True)
        if artifact_kind not in {"pr", "spec", "branch", "deployment", "tracker"}:
            raise ValueError("Unknown artifact kind")
        if not isinstance(reference, str) or not reference.strip():
            raise ValueError("Artifact reference is required")
        work["artifacts"][artifact_kind] = reference
        self.save(work)
        if (
            artifact_kind not in {"tracker", "branch"}
            and work["artifacts"].get("tracker")
            and reference.startswith("https://")
        ):
            action = "link:" + artifact_kind + ":" + reference
            self.mutate(
                work, action, "link", {"reference": work["artifacts"]["tracker"], "url": reference}
            )
        sha = (
            self.commit_record(work_id, f"chore(work): link {artifact_kind} for {work_id}")
            if commit
            else None
        )
        return {
            "status": "linked",
            "work_id": work_id,
            "artifacts": work["artifacts"],
            "commit": sha,
        }

    def optional_tracker_operation(self, work, operation):
        provider_id = work["providers"]["tracker"]
        if not getattr(self.registry, "declares", lambda _id, _operation: False)(
            provider_id, "capabilities"
        ):
            return False
        capabilities = self.registry.invoke(provider_id, "capabilities", {})
        return operation in capabilities["optional_operations"]

    def mutate(self, work, action, operation, payload, *, reconcile=False):
        operation_id = self.op_id(work, action)
        payload = {**payload, "operation_id": operation_id}
        record = self.journal.begin(
            operation_id, {"provider": work["providers"]["tracker"], **payload}
        )
        if record["status"] == "succeeded" and not reconcile:
            return record["result"]
        try:
            result = self.tracker(work).invoke(operation, payload)
        except Exception:
            self.journal.uncertain(operation_id)
            raise
        self.journal.succeed(operation_id, result)
        return result

    def git(self, *args, check=True):
        return run_git(self.root, *args, check=check, context="Git branch operation failed")

    def commit_record(self, work_id, message):
        """Commit only ``.ai-dlc/work/<id>.toml``; return the commit SHA or None if unchanged.

        ``git commit --only`` limits the commit to the record whatever else is staged, so
        other staged or dirty files are neither included nor disturbed.
        """
        record = f".ai-dlc/work/{work_id}.toml"
        context = "Git record commit failed"
        changed = run_git(
            self.root, "status", "--porcelain", "--", record, context=context
        ).stdout.strip()
        if not changed:
            return None
        run_git(self.root, "add", "--", record, context=context)
        run_git(
            self.root, "commit", "--quiet", "--only", "-m", message, "--", record, context=context
        )
        return run_git(self.root, "rev-parse", "HEAD", context=context).stdout.strip()

    def branch(self, work):
        branch = work["artifacts"].get("branch", "work/" + work["id"])
        self.git("check-ref-format", "--branch", branch)
        current = self.git("branch", "--show-current").stdout.strip()
        if current != branch:
            own_work = f".ai-dlc/work/{work['id']}.toml"
            changed = self.git("status", "--porcelain", "--untracked-files=all").stdout.splitlines()
            if any(line[3:] != own_work for line in changed):
                raise ValueError(
                    "Cannot switch work branch with dirty files; preserve or commit current work first"
                )
            exists = (
                self.git(
                    "show-ref", "--verify", "--quiet", f"refs/heads/{branch}", check=False
                ).returncode
                == 0
            )
            self.git("switch", branch) if exists else self.git("switch", "-c", branch)
        work["artifacts"]["branch"] = branch
        self.save(work)
        return branch

    def start(self, work_id, *, commit=True):
        with project_write_lock(self.root):
            result = self._start(work_id)
            result["commit"] = (
                self.commit_record(work_id, f"chore(work): start {work_id}") if commit else None
            )
            return result

    def _start(self, work_id):
        records = self.validated_records(work_id)
        work = records[work_id]
        for dependency in sorted(set(records) - {work_id}):
            required = records[dependency]
            reference = required["artifacts"].get("tracker")
            if not reference:
                raise ValueError(f"Dependency {dependency} is unpublished; completion unavailable")
            try:
                item = self.tracker(required).invoke("read", {"reference": reference})
            except Exception as exc:
                raise ValueError(f"Dependency {dependency} status unavailable: {exc}") from exc
            if item.get("state") != "closed":
                raise ValueError(f"Dependency {dependency} is not completed: {item.get('state')}")
        provider_id = work["providers"]["tracker"]
        declared = getattr(self.registry, "declares", lambda _id, _operation: False)(
            provider_id, "capabilities"
        )
        capabilities = self.registry.invoke(provider_id, "capabilities", {}) if declared else None
        branch = self.branch(work)
        if not work["artifacts"].get("tracker"):
            self.publish(work_id)
            work = self.load(work_id, True)
        if capabilities is not None and not capabilities["lifecycle"]["in_progress"]:
            item = self.tracker(work).invoke("read", {"reference": work["artifacts"]["tracker"]})
            transition = {
                "supported": False,
                "reason": "Tracker does not support the in_progress lifecycle state",
            }
        else:
            item = self.mutate(
                work,
                "start",
                "transition",
                {"reference": work["artifacts"]["tracker"], "state": "in_progress"},
                reconcile=capabilities is not None,
            )
            transition = {"supported": True, "state": "in_progress"}
            if capabilities is None:
                transition["verified"] = False
        return {
            "status": "started",
            "tracker": item,
            "branch": branch,
            "tracker_transition": transition,
        }

    def pr(self, work_id):
        """Open the pull request for the bound branch once, link it and commit the record."""
        with project_write_lock(self.root):
            return self._pr(work_id)

    def _pr(self, work_id):
        self._check_source()
        work = self.load(work_id)
        if not work["reviewed"]:
            raise RefusedError("Work must be reviewed before mutation")
        existing = work["artifacts"].get("pr")
        if existing:
            return {
                "status": "linked",
                "work_id": work_id,
                "created": False,
                "pr": {"url": existing},
            }
        head = work["artifacts"].get("branch")
        if not head:
            raise RefusedError(
                f"Work {work_id} has no bound branch; run `ai-dlc work start {work_id}` first"
            )
        if self.git("branch", "--show-current").stdout.strip() != head:
            raise RefusedError(f"Switch to the bound branch {head} before opening its pull request")
        base = self.config.get("scm", {}).get("target_branch", "main")
        tracker_id = work["providers"].get("tracker")
        tracker_cfg = self.config.get("providers", {}).get(tracker_id, {}) if tracker_id else {}
        reference = work["artifacts"].get("tracker", "")
        closes = (
            reference
            if tracker_cfg.get("kind", tracker_id) == "github-issues" and reference.isdigit()
            else None
        )
        payload = {"title": work["title"], "body": render_pull_request_body(work, closes=closes)}
        operation_id = self.op_id(work, "pr")
        record = self.journal.lookup(operation_id)
        if record and record["status"] in {"pending", "uncertain"}:
            raise UncertainError(
                "A previous pull request creation is uncertain; find the pull request for "
                f"{head} on the SCM and link it with `ai-dlc work link {work_id} pr <url>`"
            )
        if record and record["status"] == "succeeded":
            created = record["result"]
        else:
            # The journal fingerprints the pull request's identity, not its text, so a retry
            # with an edited record cannot conflict with, or repeat, an earlier creation.
            self.journal.begin(
                operation_id, {"provider": work["providers"].get("scm"), "base": base, "head": head}
            )
            scm = self.role(work, "scm", lambda: GitHubSCM(self.root, self.config))
            self.journal.uncertain(operation_id)
            try:
                created = scm.pull_request_create(payload["title"], payload["body"], base, head)
            except RefusedError:
                self.journal.refused(operation_id)
                raise
            except Exception:
                self.journal.uncertain(operation_id)
                raise
            self.journal.succeed(operation_id, created)
        linked = self.link(work_id, "pr", created["url"])
        return {
            "status": "created",
            "work_id": work_id,
            "created": True,
            "pr": created,
            "artifacts": linked["artifacts"],
            "commit": linked["commit"],
        }

    def status(self, work_id):
        work = self.load(work_id)
        item = (
            self.tracker(work).invoke("read", {"reference": work["artifacts"]["tracker"]})
            if work["artifacts"].get("tracker")
            else None
        )
        return {"work": work, "tracker": item}

    def role(self, work, role, fallback):
        provider_id = work["providers"].get(role)
        return self.registry.get(provider_id) if provider_id else fallback()

    def finish(self, work_id, handoff: str | None = None):
        work = self.load(work_id, True)
        gates = list(
            dict.fromkeys(
                ["pr-merged", "ci-green", "specification-current"]
                + list(self.config.get("gates", {}).get("finish", []))
            )
        )
        evidence = {}
        blocked = []
        merged = None
        scm = None
        for gate in gates:
            try:
                if gate == "specification-current":
                    evidence[gate] = (
                        self.role(work, "specs", lambda: OpenSpecProvider(self.root)).current(
                            work, revision=merged["sha"] if merged else ""
                        )
                        if work["requires_spec"]
                        else {"required": False, "reason": work["spec_reason"]}
                    )
                    if work["requires_spec"] and (
                        evidence[gate].get("current") is not True
                        or not merged
                        or evidence[gate].get("revision") != merged["sha"]
                    ):
                        raise ValueError("Specification provider did not confirm current archive")
                elif gate in {"pr-merged", "ci-green", "deployed"}:
                    scm = scm or self.role(work, "scm", lambda: GitHubSCM(self.root, self.config))
                    merged = merged or scm.merged(work["artifacts"].get("pr", ""))
                    evidence[gate] = (
                        merged
                        if gate == "pr-merged"
                        else scm.ci(merged["sha"])
                        if gate == "ci-green"
                        else self.role(work, "deploy", lambda scm=scm: scm).deployment(
                            merged["sha"]
                        )
                    )
                else:
                    raise ValueError(f"Unknown required gate: {gate}")
            except Exception as exc:  # noqa: BLE001 -- untrusted provider failures must block completion
                blocked.append({"gate": gate, "reason": str(exc)})
        if blocked:
            return {
                "status": "blocked",
                "work_id": work_id,
                "blocked": blocked,
                "evidence": evidence,
            }
        reference = work["artifacts"].get("tracker")
        if not reference:
            raise ValueError("Publish work before completion")
        # Remote read plus fresh gate evaluation prevents a local journal from authorizing completion.
        remote = self.tracker(work).invoke("read", {"reference": reference})
        completion_id = self.op_id(work, "finish")
        record = self.journal.begin(
            completion_id,
            {
                "provider": work["providers"]["tracker"],
                "reference": reference,
                "state": "closed",
                "operation_id": completion_id,
            },
        )
        if record["status"] == "succeeded" and remote["state"] != record["result"]["state"]:
            return {
                "status": "blocked",
                "blocked": [
                    {
                        "gate": "tracker-state",
                        "reason": "Tracker changed after completion; explicit reconciliation required",
                    }
                ],
            }
        if remote["state"] == "closed":
            # A previous transition can have succeeded despite losing its response.
            # The freshly read canonical remote state reconciles that uncertainty.
            item = remote
            if self.optional_tracker_operation(work, "reconcile_closed"):
                item = self.mutate(
                    work,
                    "reconcile_closed",
                    "reconcile_closed",
                    {"reference": reference},
                    reconcile=True,
                )
                if item["state"] != "closed":
                    raise RuntimeError("Terminal reconciliation did not confirm completed tracker")
            self.journal.succeed(completion_id, item)
        else:
            item = self.mutate(
                work, "finish", "transition", {"reference": reference, "state": "closed"}
            )
        result = {"status": "completed", "work_id": work_id, "tracker": item, "evidence": evidence}
        if handoff:
            operation_id = self.op_id(work, "handoff")
            payload = {"body": handoff}
            record = self.journal.begin(operation_id, payload)
            if record["status"] == "succeeded":
                result["handoff"] = record["result"]
                return result
            try:

                def fallback_knowledge():
                    from ai_dlc.documentation.knowledge import Knowledge

                    vault = self.config.get("paths", {}).get("vault")
                    if not vault:
                        raise ValueError("Configure paths.vault to append handoff")
                    return Knowledge(Path(vault))

                note = self.role(work, "knowledge", fallback_knowledge).append(
                    work["artifacts"].get("knowledge", f"ai-dlc/{work_id}.md"),
                    handoff,
                    operation_id,
                )
                self.journal.succeed(operation_id, note)
                result["handoff"] = note
            except Exception as exc:  # noqa: BLE001 -- completion must survive any handoff-provider failure
                self.journal.uncertain(operation_id)
                result["status"] = "completed,handoff_pending"
                result["handoff_error"] = str(exc)
        return result
