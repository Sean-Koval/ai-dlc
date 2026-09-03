"""Provider registry with verified executable and Python distribution boundaries."""

import hashlib
import importlib.machinery
import importlib.metadata
import importlib.util
import json
import math
import queue
import re
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

from ai_dlc.contracts import manifest, validate_request, validate_response


def verify_artifact(path, expected):
    p = Path(path)
    if not expected or hashlib.sha256(p.read_bytes()).hexdigest() != expected:
        raise ValueError(f"Provider artifact digest mismatch: {p}")
    return p


def reject_unsafe_imports(files):
    """Refuse import state that cannot be tied to the verified source closure.

    Python providers requiring already imported third-party modules should use
    the executable interface in a dedicated environment instead.
    """
    paths = {Path(file).resolve() for file in files}
    for path in paths:
        if path.suffix == ".py" and (
            path.with_suffix(".pyc").exists()
            or any((path.parent / "__pycache__").glob(path.stem + ".*.pyc"))
        ):
            raise ValueError(f"Unchecked Python bytecode may shadow verified source: {path}")
    for module in tuple(sys.modules.values()):
        origin = getattr(module, "__file__", None)
        if origin and Path(origin).resolve() in paths:
            raise ValueError(
                "Python provider dependency already imported; use an isolated executable provider"
            )


class ExecutableProvider:
    def __init__(self, config, *, bundled=False):
        self.config = config
        self.bundled = bundled
        self.command = config["command"]
        if not bundled:
            verify_artifact(self.command, config.get("sha256"))
        for artifact in config.get("skills", []):
            verify_artifact(artifact["path"], artifact.get("sha256"))

    def invoke(self, operation, payload):
        request = validate_request(operation, payload)
        if not self.bundled:
            verify_artifact(self.command, self.config.get("sha256"))
        command = self.command if isinstance(self.command, list) else [self.command]
        result = subprocess.run(
            command,
            input=request.model_dump_json(),
            text=True,
            capture_output=True,
            timeout=self.config.get("timeout", 30),
            check=False,
        )
        if result.returncode:
            raise RuntimeError(f"Provider failed: {result.stderr.strip()}")
        return validate_response(operation, json.loads(result.stdout))

    def current(self, work, revision=None):
        return self.invoke("current", {"work": work, "revision": revision})

    def merged(self, reference):
        return self.invoke("merged", {"reference": reference})

    def ci(self, sha):
        return self.invoke("ci", {"sha": sha})

    def deployment(self, sha):
        return self.invoke("deployment", {"sha": sha})

    def append(self, path, body, operation_id):
        return self.invoke("append", {"path": path, "body": body, "operation_id": operation_id})


class PythonProvider(ExecutableProvider):
    """Bounded caller deadline; timed-out trusted code may still be executing.

    Mutations therefore remain uncertain and must reconcile remote state.
    """

    def __init__(self, provider, *, timeout=30):
        if not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Provider timeout must be positive and finite")
        self.provider = provider
        self.timeout = timeout

    def invoke(self, operation, payload):
        request = validate_request(operation, payload)
        completed = queue.Queue(maxsize=1)

        def call():
            try:
                if operation in {"current", "merged", "ci", "deployment", "append"}:
                    result = getattr(self.provider, operation)(**request.payload)
                else:
                    result = self.provider.invoke(operation, request.payload)
                completed.put((True, result))
            except Exception as exc:  # noqa: BLE001 -- preserve provider errors across the worker boundary
                completed.put((False, exc))

        thread = threading.Thread(target=call, daemon=True)
        thread.start()
        try:
            success, result = completed.get(timeout=self.timeout)
        except queue.Empty as exc:
            raise TimeoutError(
                "Python provider deadline exceeded; operation outcome is uncertain"
            ) from exc
        if not success:
            raise result
        return validate_response(operation, result)


def module_manifest(distribution, files, hashes):
    modules = {}
    for name, file in files.items():
        relative = Path(name)
        if ".." in relative.parts or any(
            part.endswith((".dist-info", ".data")) for part in relative.parts
        ):
            continue
        package = relative.name == "__init__.py"
        native = next(
            (suffix for suffix in importlib.machinery.EXTENSION_SUFFIXES if name.endswith(suffix)),
            None,
        )
        if not (name.endswith(".py") or native):
            continue
        parts = list(relative.parts)
        if package:
            parts.pop()
        else:
            parts[-1] = parts[-1][: -len(native)] if native else relative.stem
        modules[".".join(parts)] = {
            "path": str(distribution.locate_file(file)),
            "sha256": hashes[name],
            "package": package,
            "native": bool(native),
        }
    return modules


class IsolatedPythonProvider(ExecutableProvider):
    def __init__(self, config, modules, entry_point):
        self.config, self.modules, self.entry_point = config, modules, entry_point

    def invoke(self, operation, payload):
        request = validate_request(operation, payload)
        message = {
            "request": request.model_dump(),
            "config": self.config,
            "modules": self.modules,
            "entry_point": self.entry_point,
        }
        result = subprocess.run(
            [sys.executable, "-I", "-S", str(Path(__file__).with_name("python_exec.py"))],
            input=json.dumps(message),
            text=True,
            capture_output=True,
            timeout=self.config.get("timeout", 30),
            check=False,
        )
        if result.returncode:
            raise RuntimeError("Isolated Python provider failed: " + result.stderr.strip())
        return validate_response(operation, json.loads(result.stdout))


class Registry:
    def __init__(self, config=None, *, root=None):
        self.root = Path(root or Path.cwd())
        self.config = config or {}
        self.cache = {}

    def register(self, id, provider):
        self.cache[id] = provider

    def get(self, id) -> Any:
        if id in self.cache:
            return self.cache[id]
        cfg = self.config.get("providers", {}).get(id, {})
        kind = cfg.get("kind", cfg.get("type", id))
        if kind == "openspec":
            from .openspec import OpenSpecProvider

            provider = OpenSpecProvider(self.root)
        elif kind in {"github", "github-scm", "github-deployment", "cloudflare"}:
            from .scm import GitHubSCM

            provider = GitHubSCM(self.root, self.config)
        elif kind in {"obsidian", "knowledge"}:
            from ai_dlc.knowledge import Knowledge

            vault = self.config.get("paths", {}).get("vault")
            if not vault:
                raise ValueError("Configure paths.vault for knowledge provider")
            provider = Knowledge(Path(vault))
        elif kind == "linear":
            from .linear import LinearProvider

            provider = LinearProvider(cfg)
        elif kind == "github-issues":
            provider = ExecutableProvider(
                {
                    **cfg,
                    "command": [
                        sys.executable,
                        "-m",
                        "ai_dlc.providers.github_issues",
                        json.dumps(cfg),
                    ],
                },
                bundled=True,
            )
        elif kind == "executable":
            provider = ExecutableProvider(cfg)
        elif kind == "python":
            # A verified dependency lock plus the full installed distribution file set is mandatory.
            verify_artifact(cfg["dependency_lock"], cfg.get("dependency_lock_sha256"))
            distribution = importlib.metadata.distribution(cfg["distribution"])
            expected = cfg.get("distribution_files", {})
            files = {
                str(f): f
                for f in distribution.files or []
                if not str(f).endswith((".pyc", "/RECORD"))
            }
            if not expected or set(expected) != set(files):
                raise ValueError("Full Python distribution integrity manifest required")
            for name, f in files.items():
                verify_artifact(distribution.locate_file(f), expected[name])
            import_files = [distribution.locate_file(f) for f in files.values()]
            modules = module_manifest(distribution, files, expected)
            pending = list(distribution.requires or [])
            checked = {cfg["distribution"].lower().replace("_", "-")}
            closure = cfg.get("dependency_distributions", {})
            while pending:
                requirement = pending.pop()
                match = re.match(r"[A-Za-z0-9_.-]+", requirement)
                if not match:
                    raise ValueError("Invalid dependency requirement")
                name = match.group().lower().replace("_", "-")
                if name in checked:
                    continue
                # Verify optional dependencies too: plugins can import them at runtime.
                locked = closure.get(name)
                if not locked:
                    raise ValueError(f"Missing dependency distribution integrity: {name}")
                dependency = importlib.metadata.distribution(name)
                if dependency.version != locked.get("version"):
                    raise ValueError(f"Dependency version mismatch: {name}")
                dep_files = {
                    str(f): f
                    for f in dependency.files or []
                    if not str(f).endswith((".pyc", "/RECORD"))
                }
                if not dep_files or set(dep_files) != set(locked.get("files", {})):
                    raise ValueError(f"Incomplete dependency file integrity: {name}")
                for dep_path, dep_file in dep_files.items():
                    verify_artifact(dependency.locate_file(dep_file), locked["files"][dep_path])
                    import_files.append(dependency.locate_file(dep_file))
                modules.update(module_manifest(dependency, dep_files, locked["files"]))
                checked.add(name)
                pending.extend(dependency.requires or [])
            for artifact in cfg.get("skills", []):
                verify_artifact(artifact["path"], artifact.get("sha256"))
            matches = [
                ep
                for ep in distribution.entry_points
                if ep.group == "ai_dlc.providers" and ep.name == cfg["entry_point"]
            ]
            if len(matches) != 1:
                raise ValueError("Provider entry point missing or ambiguous")
            entry_point = matches[0].value
            if entry_point.split(":", 1)[0] not in modules:
                raise ValueError("Python provider import origin is outside verified distribution")
            provider = IsolatedPythonProvider(cfg, modules, entry_point)
        else:
            raise ValueError(f"Unknown provider: {id}")
        self.cache[id] = provider
        return provider

    def invoke(self, provider_id, operation, payload):
        # Public generic invocation cannot authorize completion. The workflow service
        # calls providers internally only after fresh evidence checks.
        cfg = self.config.get("providers", {}).get(provider_id, {})
        terminal = {"closed", "done", "completed", "complete", "canceled", "cancelled"}
        terminal.update(
            str(v).lower() for k, v in cfg.get("statuses", {}).items() if k.lower() in terminal
        )
        if operation == "complete":
            raise ValueError("Terminal transitions require work.finish and its gates")
        request = validate_request(operation, payload)
        if (
            operation == "transition"
            and str(request.payload.get("state", "")).strip().lower() in terminal
        ):
            raise ValueError("Terminal transitions require work.finish and its gates")
        provider = self.get(provider_id)
        if operation in {"current", "merged", "ci", "deployment", "append"}:
            result = getattr(provider, operation)(**request.payload)
        else:
            result = provider.invoke(operation, request.payload)
        return validate_response(operation, result)

    def discover(self):
        discovered = manifest()
        for entry in self.config.get("contracts", {}).get("manifests", []):
            path = verify_artifact(self.root / entry["path"], entry.get("sha256"))
            document = json.loads(path.read_text())
            if document.get("schema") != 1 or not isinstance(document.get("roles"), dict):
                raise ValueError("Invalid role/client contract manifest")
            for role, contract in document["roles"].items():
                if role in discovered["roles"]:
                    raise ValueError(f"Duplicate contract role: {role}")
                if not isinstance(contract, dict) or not isinstance(contract.get("version"), int):
                    raise TypeError(f"Role {role} must declare a contract version")
                discovered["roles"][role] = contract
        return {
            "manifest": discovered,
            "providers": list(self.config.get("providers", {})),
            "builtins": [
                "linear",
                "github-issues",
                "openspec",
                "github",
                "github-deployment",
                "obsidian",
            ],
            "release": "ai-dlc/0.4.0",
        }
