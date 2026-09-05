"""Reviewed work, reconciled provider mutations, and evidence-gated completion."""

import hashlib
import json
import os
import re
import subprocess
import tomllib
from pathlib import Path

import tomli_w
from pydantic import BaseModel, ConfigDict, Field, field_validator

from ai_dlc.config import digest as config_digest
from ai_dlc.journal import Journal
from ai_dlc.locking import project_write_lock
from ai_dlc.providers import Registry
from ai_dlc.providers.openspec import OpenSpecProvider
from ai_dlc.providers.scm import GitHubSCM


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

    @field_validator("acceptance")
    @classmethod
    def criteria(cls, value):
        if any(not s.strip() for s in value):
            raise ValueError("Acceptance criteria cannot be empty")
        return value


def _project_source_digest(root: Path) -> str | None:
    project_file = root / "ai-dlc.toml"
    if not project_file.is_file():
        return None
    return config_digest(tomllib.loads(project_file.read_text()))


class WorkService:
    def __init__(
        self,
        root: Path,
        config: dict,
        state_path: Path | None = None,
        registry: Registry | None = None,
    ):
        self.root = Path(root).resolve()
        self.config = config
        state = (
            Path(state_path)
            if state_path
            else Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "ai-dlc"
        )
        self.journal = Journal(state / "operations.sqlite3")
        self.registry = registry or Registry(config, root=self.root)
        self.project_source_digest = _project_source_digest(self.root)

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
        aliases = {"specification": "specs", "deployment": "deploy"}
        source = raw.get("providers") or self.config.get("roles", {})
        raw["providers"] = {
            aliases.get(k, k): v
            for k, v in source.items()
            if aliases.get(k, k) in {"specs", "tracker", "scm", "deploy", "knowledge"}
        }
        work = Work.model_validate(raw).model_dump(by_alias=True)
        if work["id"] != work_id:
            raise ValueError("Work ID does not match filename")
        if mutation and not work["reviewed"]:
            raise ValueError("Work must be reviewed before mutation")
        defaults = {
            "specs": "openspec",
            "scm": "github",
            "deploy": "github-deployment",
            "knowledge": "obsidian",
        }
        for role, provider_id in {**defaults, **work["providers"]}.items():
            cfg = self.config.get("providers", {}).get(provider_id, {})
            identity = {"provider_id": provider_id, "configuration": cfg}
            # A vault's machine path is not its logical provider identity. Configure
            # providers.<id>.vault_id when distinct vaults must retain distinct bindings.
            if role in {"scm", "deploy"} or cfg.get("kind", provider_id) == "github-issues":
                identity["scm"] = self.config.get("scm", {})
            if role == "deploy":
                identity["deploy"] = self.config.get("deploy", {})
            account = cfg.get("account")
            if account:
                identity["account"] = self.config.get("accounts", {}).get(account, {})
            fingerprint = hashlib.sha256(
                json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            existing = work["bindings"].get(role)
            if existing and existing != fingerprint:
                raise ValueError(
                    f"Provider binding drift for {role}; explicitly review and rebind work"
                )
            work["bindings"][role] = fingerprint
        if mutation:
            self.save(work)
        return work

    def save(self, work):
        path = self.root / ".ai-dlc/work" / f"{work['id']}.toml"
        with project_write_lock(self.root):
            try:
                current_digest = _project_source_digest(self.root)
            except (OSError, tomllib.TOMLDecodeError):
                raise ValueError("Project configuration changed; retry the work mutation") from None
            if current_digest != self.project_source_digest:
                raise ValueError("Project configuration changed; retry the work mutation")
            tmp = path.with_suffix(".toml.tmp")
            tmp.write_text(tomli_w.dumps(work))
            tmp.replace(path)

    def op_id(self, work, action):
        repo = self.config.get("scm", {}).get("repository", str(self.root))
        identity = {"repository": repo, "work": work["id"], "action": action}
        if action != "work":
            role = "knowledge" if action == "handoff" else "tracker"
            identity["provider"] = work["providers"].get(role)
            identity["binding"] = work["bindings"].get(role)
            if role == "knowledge":
                identity["artifact"] = work["artifacts"].get("knowledge", f"ai-dlc/{work['id']}.md")
            if role == "tracker" and action != "publish":
                identity["artifact"] = work["artifacts"].get("tracker")
        return hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()

    def tracker(self, work):
        provider = work["providers"].get("tracker")
        if not provider:
            raise ValueError("Work has no pinned tracker provider")
        return self.registry.get(provider)

    def publish(self, work_id):
        work = self.load(work_id, True)
        provider = self.tracker(work)
        operation_id = self.op_id(work, "publish")
        payload = {
            "title": work["title"],
            "body": "\n".join(work["acceptance"]),
            "correlation": f"<!-- ai-dlc:{self.op_id(work, 'work')} -->",
            "operation_id": operation_id,
        }
        record = self.journal.begin(
            operation_id, {"provider": work["providers"]["tracker"], **payload}
        )
        # Always reconcile remote state, including after an interrupted process or on a different computer.
        mapped = work["artifacts"].get("tracker")
        items = (
            [provider.invoke("read", {"reference": mapped})]
            if mapped
            else provider.invoke("find", {"correlation": payload["correlation"]})["items"]
        )
        if len(items) > 1:
            raise ValueError("Duplicate correlation conflict")
        if items:
            item = items[0]
        elif record["status"] == "succeeded":
            item = provider.invoke("read", {"reference": record["result"]["id"]})
        elif record["status"] == "uncertain" or not record["created"]:
            # Search can be eventually consistent: absence is not proof that creation failed.
            raise RuntimeError(
                "Creation remains uncertain; remote correlation not yet visible; refusing duplicate retry"
            )
        else:
            try:
                item = provider.invoke("create", payload)
            except Exception:
                self.journal.uncertain(operation_id)
                raise
        self.journal.succeed(operation_id, item)
        work["artifacts"]["tracker"] = item["id"]
        self.save(work)
        return {"status": "published", "work_id": work_id, "tracker": item}

    def link(self, work_id, artifact_kind, reference):
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
        return {"status": "linked", "work_id": work_id, "artifacts": work["artifacts"]}

    def mutate(self, work, action, operation, payload):
        operation_id = self.op_id(work, action)
        payload = {**payload, "operation_id": operation_id}
        record = self.journal.begin(
            operation_id, {"provider": work["providers"]["tracker"], **payload}
        )
        if record["status"] == "succeeded":
            return record["result"]
        try:
            result = self.tracker(work).invoke(operation, payload)
        except Exception:
            self.journal.uncertain(operation_id)
            raise
        self.journal.succeed(operation_id, result)
        return result

    def git(self, *args, check=True):
        result = subprocess.run(
            ["git", *args], cwd=self.root, capture_output=True, text=True, timeout=30, check=False
        )
        if check and result.returncode:
            raise ValueError("Git branch operation failed: " + result.stderr.strip())
        return result

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

    def start(self, work_id):
        work = self.load(work_id)
        if not work["reviewed"]:
            raise ValueError("Work must be reviewed before mutation")
        branch = self.branch(work)
        if not work["artifacts"].get("tracker"):
            self.publish(work_id)
            work = self.load(work_id, True)
        provider_id = work["providers"]["tracker"]
        cfg = self.config.get("providers", {}).get(provider_id, {})
        if cfg.get("kind", cfg.get("type", provider_id)) == "github-issues":
            item = self.tracker(work).invoke("read", {"reference": work["artifacts"]["tracker"]})
            transition = {
                "supported": False,
                "reason": "GitHub Issues supports open/closed; in_progress is unavailable",
            }
        else:
            item = self.mutate(
                work,
                "start",
                "transition",
                {"reference": work["artifacts"]["tracker"], "state": "in_progress"},
            )
            transition = {"supported": True, "state": "in_progress"}
        return {
            "status": "started",
            "tracker": item,
            "branch": branch,
            "tracker_transition": transition,
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
            self.journal.succeed(completion_id, remote)
            item = remote
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
                    from ai_dlc.knowledge import Knowledge

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
