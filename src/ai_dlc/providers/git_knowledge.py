"""The ``git`` provider for the ``knowledge`` role: read records, propose by pull request.

The store is a git repository of knowledge records that pins its format in
``knowledge.toml``. Configure it per provider::

    [providers.team-knowledge]
    kind = "git"
    location = "https://github.com/<owner>/<repo>.git"  # or set KNOWLEDGE_REPO
    repository = "<owner>/<repo>"                        # where pull requests open
    base = "main"

``location`` is a local clone or a URL; without it the ``KNOWLEDGE_REPO`` environment
variable names one. A URL is cloned once into the user cache and refreshed on read.
``propose`` writes the records on a new branch in a temporary worktree, checks them,
pushes that branch and opens a draft pull request through the ``scm`` role. It never
commits to, pushes to or merges into the base branch. ``get`` and ``search``
return ``boundary: customer`` records only to a caller that passes their ``project``.
"""

import hashlib
import os
import re
import shutil
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from ai_dlc.documentation import knowledge_records, record_index
from ai_dlc.documentation.knowledge_check import check_records, project_of, team_inputs
from ai_dlc.documentation.knowledge_notes import split
from ai_dlc.errors import RefusedError
from ai_dlc.files import inside, run_git

LOCATION_ENV = "KNOWLEDGE_REPO"
_URL = re.compile(r"^(?:[a-z][a-z0-9+.-]*://|[^/\s]+@[^:\s]+:)")
_GITHUB = re.compile(r"github\.com[:/]([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?$")
_REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
_IDENTITY = {
    "GIT_AUTHOR_NAME": "ai-dlc",
    "GIT_AUTHOR_EMAIL": "ai-dlc@localhost",
    "GIT_COMMITTER_NAME": "ai-dlc",
    "GIT_COMMITTER_EMAIL": "ai-dlc@localhost",
}

ScmFactory = Callable[[Path, str, str], Any]


class GitKnowledge:
    def __init__(
        self,
        config: Mapping[str, Any],
        *,
        scm: ScmFactory,
        environ: Mapping[str, str] | None = None,
    ):
        self.config = dict(config)
        self.environ = dict(os.environ if environ is None else environ)
        self.scm = scm
        self.base = str(self.config.get("base") or "main")
        location = self.config.get("location") or self.environ.get(LOCATION_ENV)
        if not location:
            raise ValueError(
                f"knowledge unavailable: set {LOCATION_ENV} or the provider's location"
            )
        self.location = str(location)
        self.remote = bool(_URL.match(self.location))

    # Reading

    def _git(self, root: Path | None, *args: str, check: bool = True):
        return run_git(
            root, *args, environ=self.environ, check=check, context="Knowledge repository"
        )

    def _cache(self) -> Path:
        home = self.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
        key = hashlib.sha256(self.location.encode()).hexdigest()[:16]
        return Path(home) / "ai-dlc" / "knowledge" / key

    def repository_root(self) -> Path:
        """The checkout records are read from; a URL's cache is refreshed to the base."""
        if not self.remote:
            root = Path(self.location).expanduser().resolve()
            if not (root / ".git").exists():
                raise ValueError(f"knowledge unavailable: {root} is not a git checkout")
            return root
        root = self._cache()
        if not (root / ".git").exists():
            root.parent.mkdir(parents=True, exist_ok=True)
            self._git(None, "clone", "--quiet", "--branch", self.base, self.location, str(root))
        else:
            self._git(root, "fetch", "--quiet", "origin", self.base)
            self._git(root, "checkout", "--quiet", "--detach", f"origin/{self.base}")
            self._git(root, "reset", "--quiet", "--hard", f"origin/{self.base}")
        return root

    def get(self, id: str, project: str | None = None) -> dict:
        """The record named ``id``; a customer record only for its own ``project``.

        Customer records of other projects are left out before matching, so the
        answer is not-found and an error never names their paths (KAN-465).
        """
        root = self.repository_root()
        entries, _invalid = record_index.scan(root)
        matches = [
            entry
            for entry in team_inputs(entries, project)
            if id in (entry["record"].id, *(entry["record"].aliases or ()))
        ]
        if not matches:
            raise LookupError(f"no knowledge record has id or alias {id}")
        if len(matches) > 1:
            paths = ", ".join(entry["path"] for entry in matches)
            raise ValueError(f"id or alias {id} is ambiguous: {paths}")
        _data, _raw, body = split((root / matches[0]["path"]).read_text(errors="replace"))
        record = matches[0]["record"]
        return {
            "id": record.id,
            "path": matches[0]["path"],
            "header": record.model_dump(mode="json"),
            "body": body,
        }

    def search(
        self,
        type: str | None = None,
        scope: str | None = None,
        labels: list[str] | None = None,
        status: str | None = None,
        text: str | None = None,
        project: str | None = None,
    ) -> dict:
        """Records matching every filter; customer records only for their own ``project``.

        A ``boundary: customer`` record is returned only when ``project`` names the
        project it sits under (KAN-465). Refused files under another project's
        directory are left out too, since their errors may repeat header values.
        """
        found = record_index.search(self.repository_root(), type, scope, labels or (), status, text)
        return {
            **found,
            "items": team_inputs(found["items"], project),
            "invalid": [
                entry for entry in found["invalid"] if project_of(entry["path"]) in (None, project)
            ],
        }

    def captured(self, source: Path) -> dict:
        return record_index.check_source(self.repository_root(), source)

    def list_changed(self, since: str) -> dict:
        root = self.repository_root()
        head = self._git(root, "rev-parse", "HEAD").stdout.strip()
        if self._git(
            root, "rev-parse", "--verify", "--quiet", f"{since}^{{commit}}", check=False
        ).returncode:
            raise RefusedError(f"unknown revision in the knowledge repository: {since}")
        output = self._git(
            root, "diff", "--name-status", "--no-renames", f"{since}..{head}", "--", "*.md"
        ).stdout
        kinds = {"A": "added", "M": "modified", "D": "deleted"}
        changed = []
        for line in output.splitlines():
            status, _, path = line.partition("\t")
            change = kinds.get(status[:1], "modified")
            item: dict[str, Any] = {"path": path, "change": change}
            if change != "deleted":
                try:
                    header = record_index.read_header(root / path)
                except ValueError:
                    header = None
                if header and isinstance(header.get("id"), str):
                    item["id"] = header["id"]
            changed.append(item)
        return {"since": since, "head": head, "changed": changed}

    # Proposing

    def _repository(self, root: Path) -> str:
        configured = self.config.get("repository")
        if configured:
            if not _REPOSITORY.fullmatch(str(configured)):
                raise ValueError("knowledge provider repository must be owner/repo")
            return str(configured)
        url = self._git(root, "remote", "get-url", "origin", check=False).stdout.strip()
        match = _GITHUB.search(url)
        if not match:
            raise RefusedError(
                "set the knowledge provider's repository (owner/repo) to open pull requests"
            )
        return match.group(1)

    def _check(self, tree: Path, proposed: list[dict]) -> list[str]:
        """Checks of the proposed files alone, before they are committed."""
        problems = record_index.pin(tree)
        for entry in proposed:
            try:
                record, _body = knowledge_records.parse(entry["text"])
            except ValueError as exc:
                problems.append(f"{entry['path']}: {exc}")
                continue
            entry["record"] = record
        if problems:
            return problems
        existing, _invalid = record_index.scan(tree)
        problems.extend(record_index.duplicates(existing, proposed))
        mine = {entry["path"] for entry in proposed}
        taken = {}
        for entry in (entry for entry in existing if entry["path"] not in mine):
            for key in (entry["record"].id, *(entry["record"].aliases or ())):
                taken[key] = entry["path"]
        for entry in proposed:
            owner = taken.get(entry["record"].id)
            if owner and owner != entry["path"]:
                problems.append(f"{entry['path']}: id {entry['record'].id} is used by {owner}")
            taken[entry["record"].id] = entry["path"]
        return problems

    def propose(self, records: list[dict], branch: str, title: str, body: str = "") -> dict:
        root = self.repository_root()
        if (
            branch == self.base
            or self._git(root, "check-ref-format", "--branch", branch, check=False).returncode
        ):
            raise RefusedError(f"propose needs a new branch other than {self.base}: {branch}")
        paths = [entry["path"] for entry in records]
        if len(set(paths)) != len(paths):
            raise RefusedError("propose names a record path twice")
        for path in paths:
            if not path.endswith(".md"):
                raise RefusedError(f"a record file ends in .md: {path}")
            try:
                inside(root, path)
            except ValueError as exc:
                raise RefusedError(str(exc)) from exc
        repository = self._repository(root)
        if (
            self._git(
                root, "ls-remote", "--exit-code", "--heads", "origin", branch, check=False
            ).returncode
            == 0
        ):
            raise RefusedError(f"branch {branch} already exists on the remote")
        self._git(root, "fetch", "--quiet", "origin", self.base)
        workspace = Path(tempfile.mkdtemp(prefix="ai-dlc-knowledge-"))
        tree = workspace / "tree"
        self._git(
            root, "worktree", "add", "--quiet", "-b", branch, str(tree), f"origin/{self.base}"
        )
        try:
            return self._propose_in(tree, repository, records, branch, title, body)
        finally:
            self._git(root, "worktree", "remove", "--force", str(tree), check=False)
            self._git(root, "branch", "-D", branch, check=False)
            shutil.rmtree(workspace, ignore_errors=True)

    def _propose_in(self, tree, repository, records, branch, title, body) -> dict:
        proposed = [{"path": entry["path"], "text": entry["text"]} for entry in records]
        for entry in proposed:
            target = inside(tree, entry["path"])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(entry["text"])
        problems = self._check(tree, proposed)
        if problems:
            raise RefusedError("knowledge check failed: " + "; ".join(problems))
        self._git(tree, "add", "--", *[entry["path"] for entry in proposed])
        staged = self._git(tree, "diff", "--cached", "--name-only").stdout.split()
        if not staged:
            raise RefusedError("propose changes nothing: the records already match the base")
        environ = {**self.environ, **{k: v for k, v in _IDENTITY.items() if k not in self.environ}}
        run_git(tree, "commit", "--quiet", "-m", title, environ=environ, context="Knowledge commit")
        commit = self._git(tree, "rev-parse", "HEAD").stdout.strip()
        # The whole tree must pass `knowledge check` against the base before any push.
        checked = check_records(tree, base=f"origin/{self.base}")
        if checked["failures"]:
            raise RefusedError(
                "knowledge check failed: "
                + "; ".join(
                    f"{item['path']}{'#' + item['pointer'] if item['pointer'] else ''}: "
                    f"{item['message']}"
                    for item in checked["failures"]
                )
            )
        # An explicit refspec: the push can only create refs/heads/<branch>.
        self._git(tree, "push", "--quiet", "-u", "origin", f"HEAD:refs/heads/{branch}")
        self._git(tree, "branch", "--set-upstream-to", f"origin/{branch}", branch)
        pull_request = self.scm(tree, repository, self.base).pull_request_create(
            title, body, self.base, branch, draft=True
        )
        return {
            "status": "proposed",
            "branch": branch,
            "commit": commit,
            "files": sorted(staged),
            "pull_request": pull_request,
        }
