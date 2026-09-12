"""Read-only project workspace diagnostics; filesystem state never qualifies a native client."""

from __future__ import annotations

import os
import re
import shlex
import shutil
import stat
import subprocess
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import unquote, urlsplit

from ai_dlc import __version__
from ai_dlc.documentation.document_access import _reason, _repository, _scope, markdown_links
from ai_dlc.documentation.document_files import directory, read_bounded, read_document
from ai_dlc.documentation.vault_mount import read_mount_bindings
from ai_dlc.harness.agents import read_managed_section

REQUIRED_COMMANDS = ("docs-search", "docs-read", "workspace-check")
MOUNT_ROOTS = ("docs", "openspec")
PROJECT_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}")
PROBE_TIMEOUT = 5.0
PROBE_BYTES = 65536
NAVIGATION_BYTES = 262144
MAX_LINKS = 200
REPAIR = "Rerun the existing AI-DLC bootstrap and `ai-dlc setup apply` to reconcile activation."
MOUNT_PREVIEW = "Preview `ai-dlc project link-vault --mode mount` from the stable checkout root."
LIMITATIONS = [
    "Read-only: no alias, shell entry, binding or mount is created or repaired.",
    "Only the AI-DLC-owned shell section is parsed; authored shell content is never returned.",
    "Filesystem links cannot establish Obsidian indexing, search, backlinks or refresh behavior.",
    "Link classification checks local reachability, not semantic correctness.",
]


def _finding(section: str, code: str, message: str, action: str | None = None) -> dict:
    return {"section": section, "code": code, "message": message, "action": action}


def _probe(executable: str, arguments: list[str], environ: Mapping[str, str]) -> dict:
    """Run one explicit informational command with bounded time and retained output."""
    try:
        completed = subprocess.run(
            [executable, *arguments],
            capture_output=True,
            check=False,
            env={**environ, "NO_COLOR": "1", "TERM": "dumb", "COLUMNS": "200"},
            stdin=subprocess.DEVNULL,
            timeout=PROBE_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "output": ""}
    except OSError:
        return {"status": "failed", "output": ""}
    output = completed.stdout[:PROBE_BYTES].decode("utf-8", errors="replace")
    return {"status": "ok" if completed.returncode == 0 else "failed", "output": output}


def _installation(environ: Mapping[str, str]) -> dict:
    result: dict = {
        "status": "missing",
        "executable": None,
        "resolved_executable": None,
        "observed_version": None,
        "current_process_version": __version__,
        "probes": {"version": "not-run", "help": "not-run"},
        "commands": dict.fromkeys(REQUIRED_COMMANDS),
    }
    lexical = shutil.which("ai-dlc", path=environ.get("PATH", ""))
    if lexical is None:
        return result
    executable = os.path.abspath(lexical)
    result["executable"] = executable
    result["resolved_executable"] = os.path.realpath(executable)
    version = _probe(executable, ["--version"], environ)
    result["probes"]["version"] = version["status"]
    if version["status"] == "ok":
        match = re.search(r"\bai-dlc\s+(\d[\w.+-]*)", version["output"])
        result["observed_version"] = match.group(1) if match else None
    listing = _probe(executable, ["project", "--help"], environ)
    result["probes"]["help"] = listing["status"]
    if listing["status"] == "ok":
        result["commands"] = {
            name: re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", listing["output"]) is not None
            for name in REQUIRED_COMMANDS
        }
    if result["observed_version"] is None or listing["status"] != "ok":
        result["status"] = "unverified"
    elif result["observed_version"] == __version__ and all(result["commands"].values()):
        result["status"] = "current"
    else:
        result["status"] = "different"
    return result


def _bootstrap_bin(environ: Mapping[str, str], home: Path) -> Path:
    data = environ.get("XDG_DATA_HOME") or str(home / ".local/share")
    return Path(environ.get("AI_DLC_BOOTSTRAP_HOME") or f"{data}/ai-dlc/bootstrap") / "bin"


def _configured_bin(body: str) -> str | None:
    for line in body.splitlines():
        if not line.startswith("export PATH="):
            continue
        try:
            words = shlex.split(line.removeprefix("export PATH="))
        except ValueError:
            return None
        if len(words) == 1 and words[0].endswith(":$PATH"):
            return words[0].removesuffix(":$PATH")
    return None


def _alias_checkout(alias: Path, root: Path) -> dict:
    """Attribute the shared alias to a checkout through the environment it selects."""
    result = {"alias_environment": None, "alias_checkout": None, "alias_is_this_checkout": None}
    if not os.path.exists(alias):
        return result
    environment = Path(os.path.realpath(alias)).parent.parent
    result["alias_environment"] = str(environment)
    try:
        recorded = read_document(environment / "ai-dlc-source-root").decode("utf-8").strip()
    except (OSError, ValueError, UnicodeDecodeError):
        return result
    if not recorded:
        return result
    result["alias_checkout"] = recorded
    result["alias_is_this_checkout"] = os.path.realpath(recorded) == os.path.realpath(root)
    return result


def _activation(environ: Mapping[str, str], home: Path, installation: dict, root: Path) -> dict:
    bin_dir = _bootstrap_bin(environ, home)
    alias = bin_dir / "ai-dlc"
    if not os.path.lexists(alias):
        alias_state = "missing"
    elif not os.path.exists(alias):
        alias_state = "broken"
    else:
        alias_state = "present"
    entries = [entry for entry in environ.get("PATH", "").split(os.pathsep) if entry]
    current = {
        "bootstrap_bin": str(bin_dir),
        "bootstrap_alias": alias_state,
        **_alias_checkout(alias, root),
        "bootstrap_bin_on_path": any(
            os.path.realpath(entry) == os.path.realpath(bin_dir) for entry in entries
        ),
        "path_selects_bootstrap_alias": alias_state == "present"
        and installation["resolved_executable"] == os.path.realpath(alias),
    }
    shell = Path(environ.get("SHELL", "")).name or None
    configured = {
        "shell": shell,
        "rc_file": None,
        "section": "unsupported-shell",
        "configured_bin": None,
        "matches_bootstrap_bin": None,
    }
    if shell in ("bash", "zsh"):
        rc = home / (".zshrc" if shell == "zsh" else ".bashrc")
        configured["rc_file"] = str(rc)
        try:
            found = read_managed_section(read_document(rc).decode("utf-8"), toml=True)
        except FileNotFoundError:
            configured["section"] = "absent"
        except (OSError, ValueError):
            configured["section"] = "unreadable"
        else:
            configured["section"] = found["state"]
            if found["state"] == "present":
                value = _configured_bin(found["body"])
                configured["configured_bin"] = value
                configured["matches_bootstrap_bin"] = value is not None and os.path.realpath(
                    value
                ) == os.path.realpath(bin_dir)
    if current["path_selects_bootstrap_alias"]:
        status = "active"
    elif configured["section"] == "present":
        ready = configured["matches_bootstrap_bin"] and alias_state == "present"
        status = "configured-for-next-shell" if ready else "stale"
    elif configured["section"] == "absent":
        status = "missing"
    else:
        status = "unverified"
    return {"status": status, "current": current, "configured": configured}


def _mount(target: Path, checkout: Path, part: str) -> dict:
    source = checkout / part
    try:
        mode = os.lstat(source).st_mode
        source_state = (
            "symlink"
            if stat.S_ISLNK(mode)
            else "directory"
            if stat.S_ISDIR(mode)
            else "not-directory"
        )
    except FileNotFoundError:
        source_state = "missing"
    except OSError:
        source_state = "unavailable"
    entry = {
        "root": part,
        "source": str(source),
        "source_state": source_state,
        "destination": str(target / part),
        "raw_target": None,
    }
    try:
        with directory(target) as parent:
            try:
                info = os.stat(part, dir_fd=parent, follow_symlinks=False)
            except FileNotFoundError:
                missing_source = part == "openspec" and source_state == "missing"
                return entry | {"status": "not-initialized" if missing_source else "missing-link"}
            if not stat.S_ISLNK(info.st_mode):
                return entry | {"status": "conflict"}
            raw = os.readlink(part, dir_fd=parent)
    except FileNotFoundError:
        return entry | {"status": "missing-link"}
    except (OSError, ValueError):
        return entry | {"status": "unavailable"}
    entry["raw_target"] = raw
    if Path(os.path.abspath(target / raw)) != source:
        return entry | {"status": "changed-link"}
    if source_state != "directory":
        return entry | {"status": "missing-source"}
    return entry | {"status": "connected"}


def _binding(root: Path, binding: dict) -> dict:
    if "error" in binding:
        return {
            "binding_path": binding["binding_path"],
            "status": "malformed",
            "reason": binding["error"],
        }
    report = {
        "binding_path": binding["binding_path"],
        "project_name": binding["project_name"],
        "project_root": binding["project_root"],
        "vault_path": binding["vault_path"],
    }
    if (
        not PROJECT_NAME.fullmatch(binding["project_name"])
        or not os.path.isabs(binding["project_root"])
        or not os.path.isabs(binding["vault_path"])
    ):
        return report | {"status": "malformed", "reason": "unsafe project name or relative path"}
    checkout = Path(binding["project_root"])
    target = Path(binding["vault_path"]) / "Projects" / binding["project_name"]
    report["link_path"] = str(target)
    report["current_checkout"] = os.path.realpath(checkout) == os.path.realpath(root)
    try:
        available = stat.S_ISDIR(os.lstat(checkout).st_mode)
    except OSError:
        available = False
    if not available:
        return report | {"status": "checkout-missing", "mounts": []}
    mounts = [_mount(target, checkout, part) for part in MOUNT_ROOTS]
    healthy = mounts[0]["status"] == "connected" and mounts[1]["status"] in {
        "connected",
        "not-initialized",
    }
    return report | {"status": "connected" if healthy else "attention", "mounts": mounts}


def _vault(vault: str | None) -> dict:
    """Describe the configured vault directory itself; its notes are never listed."""
    if not vault:
        return {"status": "not-configured", "path": None}
    path = Path(vault).expanduser()
    try:
        mode = os.lstat(path).st_mode
    except FileNotFoundError:
        return {"status": "missing", "path": str(path)}
    except OSError:
        return {"status": "unavailable", "path": str(path), "reason": "inaccessible"}
    if stat.S_ISLNK(mode):
        return {"status": "unavailable", "path": str(path), "reason": "symlink not followed"}
    if not stat.S_ISDIR(mode):
        return {"status": "unavailable", "path": str(path), "reason": "not a directory"}
    return {"status": "unbound", "path": str(path)}


def _workspace(root: Path, vault: str | None) -> dict:
    try:
        bindings, error = read_mount_bindings(root, strict=False), None
    except (OSError, ValueError) as exc:
        bindings, error = [], str(exc)
    reports = [_binding(root, binding) for binding in bindings]
    return {
        "bindings": reports,
        "binding_directory_error": error,
        "vault": None if reports else _vault(vault),
    }


def _exists(root: Path, relative: str) -> bool | None:
    """Existence without following links; None marks an unsafe symlink component."""
    cursor = root
    for part in relative.split("/"):
        cursor = cursor / part
        try:
            mode = os.lstat(cursor).st_mode
        except FileNotFoundError:
            return False
        except OSError:
            return None
        if stat.S_ISLNK(mode):
            return None
    return True


def _classify(root: Path, source: str, target: str, connected: set[str]) -> dict | None:
    try:
        parsed = urlsplit(target)
    except ValueError:
        return {"path": None, "status": "malformed"}
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None
    destination = Path(os.path.abspath((root / source).parent / unquote(parsed.path)))
    try:
        relative = destination.relative_to(root).as_posix()
    except ValueError:
        return {"path": None, "status": "outside-repository"}
    exists = _exists(root, relative)
    if exists is None:
        status = "unsafe"
    elif not exists:
        status = "missing"
    elif relative.split("/", 1)[0] in MOUNT_ROOTS:
        status = "mounted" if relative.split("/", 1)[0] in connected else "unmounted"
    else:
        status = "repository-only"
    return {"path": relative, "status": status}


def _navigation(root: Path, workspace: dict) -> dict:
    connected = {
        mount["root"]
        for binding in workspace["bindings"]
        if binding.get("current_checkout")
        for mount in binding.get("mounts", [])
        if mount["status"] == "connected"
    }
    scope = _scope(root, [])
    remaining, links, omitted = NAVIGATION_BYTES, [], []
    examined, truncated = 0, False
    for relative in sorted(scope["eligible"]):
        if truncated:
            omitted.append({"path": relative, "reason": "link limit reached"})
            continue
        try:
            body = read_bounded(root, relative, remaining)
        except (OSError, ValueError) as exc:
            omitted.append({"path": relative, "reason": _reason(exc)})
            continue
        remaining -= len(body["content"].encode("utf-8"))
        examined += 1
        for line, target in markdown_links(body["content"]):
            classified = _classify(root, relative, target, connected)
            if classified is None:
                continue
            if len(links) >= MAX_LINKS:
                truncated = True
                omitted.append({"path": relative, "reason": "link limit reached"})
                break
            links.append({"source": relative, "line": line, "target": target} | classified)
    return {
        "connected_roots": sorted(connected),
        "links": links,
        "summary": dict(sorted(Counter(link["status"] for link in links).items())),
        "coverage": {
            "complete": not (omitted or scope["inventory"]["omitted"]),
            "documents_examined": examined,
            "omitted": omitted,
            "inventory_omitted": scope["inventory"]["omitted"],
        },
    }


def _installation_findings(installation: dict, activation: dict) -> list[dict]:
    status = installation["status"]
    if status == "missing":
        action = (
            f"Open a new terminal or run `source {activation['configured']['rc_file']}`."
            if activation["status"] == "configured-for-next-shell"
            else REPAIR
        )
        return [_finding("installation", "executable-missing", "No ai-dlc is on PATH.", action)]
    if status == "unverified":
        absent = [name for name, present in installation["commands"].items() if present is False]
        message = "The PATH-selected ai-dlc did not report its version within the probe bounds"
        if absent:
            message += f"; missing commands: {', '.join(absent)}."
            action = (
                "Rerun the existing bootstrap for the intended toolkit, then open a new terminal."
            )
        else:
            message += "."
            action = (
                "Run `ai-dlc --version` in the intended shell; rerun the bootstrap if it fails."
            )
        return [_finding("installation", "executable-unverified", message, action)]
    if status == "different":
        absent = [name for name, present in installation["commands"].items() if not present]
        message = (
            f"The PATH-selected ai-dlc reports {installation['observed_version']} "
            f"(this process: {__version__}); missing commands: {', '.join(absent) or 'none'}."
        )
        action = "Rerun the existing bootstrap for the intended toolkit, then open a new terminal."
        return [_finding("installation", "executable-different", message, action)]
    return []


def _activation_findings(activation: dict) -> list[dict]:
    status, configured = activation["status"], activation["configured"]
    if status == "configured-for-next-shell":
        message = f"{configured['rc_file']} activates the bootstrap bin; this PATH does not."
        action = (
            f"Open a new terminal or run `source {configured['rc_file']}`; "
            "do not add another alias or PATH entry."
        )
        return [_finding("activation", "activation-next-shell", message, action)]
    if status == "stale":
        message = "Owned shell activation or the bootstrap alias does not match the installation."
        return [_finding("activation", "activation-stale", message, REPAIR)]
    if status == "missing":
        message = "No owned shell activation exists and PATH does not select the bootstrap alias."
        return [_finding("activation", "activation-missing", message, REPAIR)]
    if status == "unverified":
        message = f"Shell activation cannot be proved safely: {configured['section']}."
        action = "Inspect shell activation manually; diagnostics return no authored shell content."
        return [_finding("activation", "activation-unverified", message, action)]
    if activation["current"]["alias_is_this_checkout"] is False:
        message = (
            "The selected shared bootstrap alias runs another checkout: "
            f"{activation['current']['alias_checkout']}."
        )
        action = (
            "Use this checkout's own environment, or rerun its bootstrap with "
            "`--publish-aliases` to repoint the shared alias deliberately."
        )
        return [_finding("activation", "alias-other-checkout", message, action)]
    return []


def _workspace_findings(workspace: dict) -> list[dict]:
    findings = []
    if workspace["binding_directory_error"]:
        findings.append(
            _finding(
                "workspace",
                "bindings-unavailable",
                workspace["binding_directory_error"],
                "Inspect the ignored local binding directory; it is not followed or repaired.",
            )
        )
    for binding in workspace["bindings"]:
        path = binding["binding_path"]
        if binding["status"] == "malformed":
            message = f"{path}: {binding['reason']}"
            action = "Inspect the local binding; it is not followed or repaired."
            findings.append(_finding("workspace", "binding-malformed", message, action))
        elif binding["status"] == "checkout-missing":
            message = f"{path} names an unavailable checkout: {binding['project_root']}"
            action = f"{MOUNT_PREVIEW} Remove an obsolete ignored binding only after inspection."
            findings.append(_finding("workspace", "binding-checkout-missing", message, action))
        for mount in binding.get("mounts", []):
            if mount["status"] not in {"connected", "not-initialized"}:
                message = f"{mount['destination']}: {mount['status']}"
                action = f"{MOUNT_PREVIEW} Conflicting paths are never replaced automatically."
                findings.append(_finding("workspace", f"mount-{mount['status']}", message, action))
    vault = workspace["vault"]
    if vault is not None:
        messages = {
            "not-configured": "No machine vault is configured and this checkout has no binding.",
            "missing": "The configured vault directory does not exist.",
            "unavailable": "The configured vault is not an accessible real directory.",
            "unbound": "The configured vault exists, but this checkout has no mount binding.",
        }
        findings.append(
            _finding(
                "workspace", f"vault-{vault['status']}", messages[vault["status"]], MOUNT_PREVIEW
            )
        )
    return findings


def _navigation_findings(navigation: dict) -> list[dict]:
    summary, findings = navigation["summary"], []
    if summary.get("repository-only"):
        message = (
            f"{summary['repository-only']} local links resolve in Git but outside docs/ and "
            "openspec/, so native mounts cannot open them."
        )
        action = "Open those targets from the repository; mounts do not add other source roots."
        findings.append(_finding("navigation", "repository-only-links", message, action))
    if summary.get("missing"):
        message = f"{summary['missing']} local link targets are missing."
        action = "Repair the links with ordinary edits, then run `ai-dlc project docs-check`."
        findings.append(_finding("navigation", "missing-link-targets", message, action))
    unsafe = sum(summary.get(key, 0) for key in ("unsafe", "outside-repository", "malformed"))
    if unsafe:
        message = f"{unsafe} links are malformed, escape the repository or traverse symlinks."
        action = "Review those links; diagnostics did not follow them."
        findings.append(_finding("navigation", "unsafe-link-targets", message, action))
    if not navigation["coverage"]["complete"]:
        message = "Some project documents or links were not examined."
        findings.append(_finding("navigation", "navigation-partial", message))
    return findings


def inspect_project_workspace(
    root: Path | str, *, vault: str | None = None, environ: Mapping[str, str] | None = None
) -> dict:
    """Report each workspace boundary separately without one aggregate readiness claim."""
    environment = dict(os.environ if environ is None else environ)
    home = Path(environment.get("HOME") or Path.home())
    repository = _repository(root)
    installation = _installation(environment)
    activation = _activation(environment, home, installation, repository)
    workspace = _workspace(repository, None if vault is None else str(vault))
    navigation = _navigation(repository, workspace)
    native_client = {
        "status": "not-assessed",
        "reason": "Observed Obsidian navigation, search, backlinks, external refresh and "
        "edit-in-Git evidence belongs in the verification record.",
    }
    findings = [
        *_installation_findings(installation, activation),
        *_activation_findings(activation),
        *_workspace_findings(workspace),
        *_navigation_findings(navigation),
        _finding(
            "native_client",
            "native-client-not-assessed",
            "Filesystem inspection cannot qualify the native client.",
            "Record observed client behavior separately before relying on it.",
        ),
    ]
    return {
        "schema": 1,
        "project_root": str(repository),
        "installation": installation,
        "activation": activation,
        "workspace": workspace,
        "navigation": navigation,
        "native_client": native_client,
        "findings": findings,
        "limitations": LIMITATIONS,
    }
