"""Replay exact candidate/published assets through native Windows consumers; never publish."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import tomllib
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
NATIVE_ASSETS = {
    "bootstrap.ps1": "scripts/bootstrap.ps1",
    "windows.ps1": "bootstrap/windows.ps1",
    "windows.json": "bootstrap/windows.json",
    "windows-native.cs": "bootstrap/windows-native.cs",
    "windows-select.py": "bootstrap/windows-select.py",
}
MANIFEST_KEYS = {
    "AI_DLC_ENGINE_VERSION",
    "AI_DLC_WHEEL_NAME",
    "AI_DLC_WHEEL_URL",
    "AI_DLC_WHEEL_SHA256",
    "AI_DLC_CONSTRAINTS_URL",
    "AI_DLC_CONSTRAINTS_SHA256",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def artifact_bytes(directory: Path, name: str) -> bytes:
    require(
        bool(name) and name not in {".", ".."} and not any(c in name for c in "/\\:"),
        "unsafe artifact filename",
    )
    path = directory / name
    require(path.is_file() and not path.is_symlink(), f"regular artifact required: {name}")
    return path.read_bytes()


def validate_artifacts(directory: Path) -> dict:
    """Bind every supplied checksum and the native manifest before copying/executing anything."""
    sums = artifact_bytes(directory, "SHA256SUMS")
    hashes: dict[str, str] = {}
    for line in sums.decode("utf-8").splitlines():
        match = re.fullmatch(r"([a-f0-9]{64}) [ *](.+)", line)
        require(match is not None, "invalid SHA256SUMS entry")
        assert match is not None
        expected, name = match.groups()
        require(name not in hashes and name != "SHA256SUMS", "duplicate/recursive checksum entry")
        require(
            digest(artifact_bytes(directory, name)) == expected, f"artifact digest mismatch: {name}"
        )
        hashes[name] = expected
    require(
        set(NATIVE_ASSETS) | {"release.sh", "requirements.txt"} <= hashes.keys(),
        "native bootstrap artifacts/checksums are incomplete",
    )
    manifest = {}
    for line in artifact_bytes(directory, "release.sh").decode("utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(r"([A-Z0-9_]+)=([A-Za-z0-9:/._~%+-]+)", line)
        require(match is not None, "manifest must contain inert allowlisted assignments")
        assert match is not None
        key, value = match.groups()
        require(key in MANIFEST_KEYS and key not in manifest, "unknown/duplicate manifest key")
        manifest[key] = value
    require(manifest.keys() == MANIFEST_KEYS, "incomplete release manifest")
    version, wheel = manifest["AI_DLC_ENGINE_VERSION"], manifest["AI_DLC_WHEEL_NAME"]
    require(
        re.fullmatch(r"\d+(?:\.\d+)*(?:(?:a|b|rc)\d+)?", version) is not None,
        "invalid engine version",
    )
    require(wheel == f"ai_dlc-{version}-py3-none-any.whl", "wheel/version mismatch")
    for prefix, name in (("WHEEL", wheel), ("CONSTRAINTS", "requirements.txt")):
        require(
            hashes.get(name) == manifest[f"AI_DLC_{prefix}_SHA256"],
            f"{prefix} manifest digest mismatch",
        )
        url = urlsplit(manifest[f"AI_DLC_{prefix}_URL"])
        require(
            url.scheme == "https"
            and bool(url.hostname)
            and url.username is None
            and url.password is None
            and not url.query
            and not url.fragment
            and unquote(url.path.rsplit("/", 1)[-1]) == name,
            "invalid manifest artifact HTTPS URL",
        )
    return {"manifest": manifest, "hashes": hashes, "checksum_file_sha256": digest(sums)}


def quote_ps(path: Path | str) -> str:
    return "'" + str(path).replace("'", "''") + "'"


def controlled_environment(workspace: Path, git: Path, system: Path) -> dict[str, str]:
    """Pass no tokens, account configuration, source imports, or preinstalled runtimes."""
    powershell = system / "System32/WindowsPowerShell/v1.0"
    directories = [system / "System32", system, powershell, git.parent]
    path = os.pathsep.join(map(str, directories))
    for name in ("python", "python3", "node", "sh", "bash", "uv", "mise"):
        require(
            shutil.which(name, path=path) is None,
            f"controlled consumer PATH contains preinstalled {name}",
        )
    env = {
        key: os.environ[key]
        for key in (
            "SystemRoot",
            "WINDIR",
            "PROCESSOR_ARCHITECTURE",
            "PROCESSOR_ARCHITEW6432",
            "NUMBER_OF_PROCESSORS",
            "OS",
            "PATHEXT",
        )
        if key in os.environ
    }
    env.update(
        PATH=path,
        COMSPEC=str(system / "System32/cmd.exe"),
        PYTHONNOUSERSITE="1",
        NO_COLOR="1",
        TERM="dumb",
        GIT_CONFIG_NOSYSTEM="1",
        GIT_TERMINAL_PROMPT="0",
    )
    for key, relative in {
        "HOME": "account",
        "USERPROFILE": "account",
        "TEMP": "temp",
        "TMP": "temp",
        "XDG_CONFIG_HOME": "config",
        "XDG_CACHE_HOME": "cache",
        "XDG_DATA_HOME": "data",
        "XDG_STATE_HOME": "state",
        "MISE_DATA_DIR": "mise-data",
        "MISE_CACHE_DIR": "mise-cache",
        "MISE_CONFIG_DIR": "mise-config",
        "UV_CACHE_DIR": "uv-cache",
    }.items():
        directory = workspace / relative
        directory.mkdir(exist_ok=True)
        env[key] = str(directory)
    global_config = workspace / "gitconfig"
    global_config.write_bytes(b"")
    env["GIT_CONFIG_GLOBAL"] = str(global_config)
    env["AI_DLC_BOOTSTRAP_HOME"] = str(workspace / "private bootstrap é")
    return env


class Journey:
    def __init__(self, evidence: Path, report: dict):
        self.evidence, self.report = evidence, report

    def save(self) -> None:
        (self.evidence / "result.json").write_text(
            json.dumps(self.report, indent=2) + "\n", encoding="utf-8"
        )

    def run(
        self,
        label: str,
        argv: list[str | Path],
        *,
        cwd: Path,
        env: dict[str, str],
        succeeds: bool = True,
    ) -> subprocess.CompletedProcess:
        arguments = list(map(str, argv))
        start = time.monotonic()
        item = {"label": label, "argv": arguments, "cwd": str(cwd)}
        self.report["commands"].append(item)
        self.save()
        result = subprocess.run(
            arguments,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=1800,
            check=False,
        )
        for stream in ("stdout", "stderr"):
            (self.evidence / f"{label}.{stream}.txt").write_text(
                getattr(result, stream), encoding="utf-8"
            )
        item.update(exit_code=result.returncode, elapsed_seconds=round(time.monotonic() - start, 3))
        self.save()
        require(
            (result.returncode == 0) == succeeds,
            f"{label}: unexpected exit {result.returncode}; inspect command logs in {self.evidence}\n{result.stderr[-2000:]}",
        )
        return result

    def check(
        self,
        label: str,
        cli: Path,
        project: Path,
        env: dict[str, str],
        *,
        succeeds: bool = True,
        failing_check: str | None = None,
    ) -> dict:
        receipt_path = self.evidence / f"{label}.receipt.json"
        self.run(
            label,
            [
                cli,
                "project",
                "check",
                "--root",
                project,
                "--required",
                "--json",
                "--receipt",
                receipt_path,
            ],
            cwd=project,
            env=env,
            succeeds=succeeds,
        )
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        required = receipt["required"]
        outcomes = receipt["outcomes"]
        require(
            bool(required)
            and len(outcomes) == len(required)
            and {row["id"] for row in outcomes} == set(required),
            "consumer receipt has incomplete required coverage",
        )
        require(
            receipt["engine_version"]
            == self.report["artifacts"]["manifest"]["AI_DLC_ENGINE_VERSION"],
            "receipt engine version differs from consumed manifest",
        )
        if succeeds:
            require(
                receipt["dirty"] is False
                and all(row["status"] == "passed" and row["exit_code"] == 0 for row in outcomes),
                "required receipt is not clean and passing",
            )
        else:
            require(
                any(
                    row["id"] == failing_check
                    and row["status"] == "failed"
                    and row["exit_code"] != 0
                    for row in outcomes
                ),
                "deliberate behavioral failure was not detected",
            )
        return receipt


def generated_identity(project: Path, artifacts: Path) -> None:
    for name, relative in {**NATIVE_ASSETS, "release.sh": "bootstrap/release.sh"}.items():
        require(
            (project / relative).read_bytes() == artifact_bytes(artifacts, name),
            f"generated asset identity differs: {relative}",
        )


def failed_bootstrap_preserves_session(
    journey: Journey,
    seed: Path,
    workspace: Path,
    env: dict[str, str],
    powershell: Path,
) -> None:
    failing = workspace / "deliberately failing consumer"
    shutil.copytree(seed, failing)
    (failing / "ai-dlc.toml").write_text(
        'schema = 4\n[[setup.steps]]\nid = "deliberate-failure"\n'
        'command = {argv = ["ai-dlc-deliberately-missing-consumer-executable"]}\n',
        encoding="utf-8",
    )
    directory = Path(env["AI_DLC_BOOTSTRAP_HOME"]) / "bin"
    before = {
        name: (directory / name).read_bytes()
        for name in ("ai-dlc.exe", "ai-dlc-cli.exe", "ai-dlc-selection.json")
    }
    script = f"""
$ErrorActionPreference='Stop'
$originalPath=$env:PATH
$originalCommand=(Get-Command ai-dlc.exe -ErrorAction Stop).Source
$failed=$false
try {{ & {quote_ps(seed / "scripts/bootstrap.ps1")} -Root {quote_ps(failing)} }}
catch {{ $failed=$true }}
if(-not $failed) {{ throw 'Deliberately failing setup unexpectedly succeeded' }}
if($env:PATH -cne $originalPath) {{ throw 'Failed bootstrap changed the caller PATH' }}
if((Get-Command ai-dlc.exe -ErrorAction Stop).Source -cne $originalCommand) {{ throw 'Failed bootstrap changed command resolution' }}
& $originalCommand --version
if($LASTEXITCODE -ne 0) {{ throw 'Previous selected CLI stopped working' }}
"""
    journey.run(
        "failure-preserves-current-session",
        [powershell, "-NoProfile", "-NonInteractive", "-Command", script],
        cwd=workspace,
        env=env,
    )
    require(
        all((directory / name).read_bytes() == body for name, body in before.items()),
        "failed setup changed previously selected launcher or provenance bytes",
    )
    journey.report["failed_setup_recovery"] = {
        "previous_launcher": "runnable-and-unchanged",
        "caller_path_and_command": "unchanged-in-same-powershell-session",
    }


def consumer(
    journey: Journey,
    preset: str,
    seed_cli: Path,
    artifacts: Path,
    workspace: Path,
    env: dict[str, str],
    powershell: Path,
    git: Path,
) -> dict:
    project = workspace / f"{preset} consumer é"
    journey.run(
        f"{preset}-init",
        [
            seed_cli,
            "project",
            "init",
            project,
            "--preset",
            preset,
            "--capability",
            "agent-client",
            "--agent-client",
            "antigravity",
        ],
        cwd=workspace,
        env=env,
    )
    generated_identity(project, artifacts)
    if preset == "generic":
        config_path = project / "ai-dlc.toml"
        text = config_path.read_text(encoding="utf-8")
        required = tomllib.loads(text)["checks"]["required"] + ["team-acceptance"]
        text, count = re.subn(r"(?m)^required = .*", "required = " + json.dumps(required), text)
        require(count == 1, "generic checks configuration is ambiguous")
        text = text.replace(
            "[checks.commands]\n",
            '[checks.commands]\nteam-acceptance = {argv = ["python", "acceptance.py"]}\n',
            1,
        )
        require(
            tomllib.loads(text)["checks"]["commands"]["team-acceptance"]["argv"]
            == ["python", "acceptance.py"],
            "generic acceptance command was not installed",
        )
        config_path.write_text(text, encoding="utf-8")
        (project / "acceptance.py").write_text(
            'from pathlib import Path\nassert Path("result.txt").read_text() == "expected"\n',
            encoding="utf-8",
        )
        (project / "result.txt").write_text("expected", encoding="utf-8")
    journey.run(
        f"{preset}-bootstrap",
        [
            powershell,
            "-NoProfile",
            "-NonInteractive",
            "-File",
            project / "scripts/bootstrap.ps1",
            "-Root",
            project,
        ],
        cwd=project,
        env=env,
    )
    home = Path(env["AI_DLC_BOOTSTRAP_HOME"])
    selection = json.loads((home / "bin/ai-dlc-selection.json").read_text())
    cli = Path(selection["cli"])
    require(
        selection["mode"] == "release"
        and (cli.parent.parent / "release.sh").read_bytes()
        == artifact_bytes(artifacts, "release.sh"),
        "installed consumer engine lost manifest identity",
    )
    child = {
        **env,
        "PATH": str(cli.parent) + os.pathsep + str(home / "bin") + os.pathsep + env["PATH"],
    }
    journey.run(f"{preset}-git-init", [git, "init", "-q"], cwd=project, env=child)
    journey.run(f"{preset}-git-add", [git, "add", "."], cwd=project, env=child)
    journey.run(
        f"{preset}-git-commit",
        [
            git,
            "-c",
            "user.name=AI-DLC verification",
            "-c",
            "user.email=verification@example.invalid",
            "commit",
            "-qm",
            "Consumer fixture",
        ],
        cwd=project,
        env=child,
    )
    baseline = journey.check(f"{preset}-baseline", cli, project, child)
    lock = (project / "uv.lock").read_bytes() if preset == "python" else None
    journey.run(
        f"{preset}-repeat-setup",
        [cli, "project", "setup", "--root", project],
        cwd=project,
        env=child,
    )
    if lock is not None:
        require(
            (project / "uv.lock").read_bytes() == lock, "repeated setup changed dependency lock"
        )
    repeated = journey.check(f"{preset}-repeated", cli, project, child)
    target = project / ("src/main.py" if preset == "python" else "result.txt")
    original = target.read_bytes()
    target.write_bytes(b'print("Regression")\n' if preset == "python" else b"regression")
    failure = journey.check(
        f"{preset}-regression",
        cli,
        project,
        child,
        succeeds=False,
        failing_check="application-tests" if preset == "python" else "team-acceptance",
    )
    if preset == "python":
        require(
            any(
                row["id"] == "language-check" and row["status"] == "passed"
                for row in failure["outcomes"]
            ),
            "behavioral regression unexpectedly failed syntax",
        )
    target.write_bytes(original)
    restored = journey.check(f"{preset}-restored", cli, project, child)
    for field in ("commit", "checks_digest", "environment_digest"):
        require(
            baseline[field] == repeated[field] == restored[field],
            f"consumer receipt binding changed: {field}",
        )
    ownership = json.loads((project / ".ai-dlc/agent-ownership.json").read_text())
    names = sorted(name for name in ownership["files"] if name.endswith("/SKILL.md"))
    require(bool(names), "no generated owned skill available for conflict acceptance")
    relative = PurePosixPath(names[0])
    require(not relative.is_absolute() and ".." not in relative.parts, "unsafe owned skill path")
    managed = project.joinpath(*relative.parts)
    before = managed.read_bytes()
    edited = before + b"\nAuthored consumer edit must be preserved.\n"
    managed.write_bytes(edited)
    journey.run(
        f"{preset}-authored-conflict",
        [cli, "agents", "render", "--root", project, "--apply"],
        cwd=project,
        env=child,
        succeeds=False,
    )
    require(managed.read_bytes() == edited, "render overwrote an authored managed-file edit")
    managed.write_bytes(before)
    journey.run(
        f"{preset}-render-restored",
        [cli, "agents", "render", "--root", project, "--check"],
        cwd=project,
        env=child,
    )
    status = journey.run(f"{preset}-clean", [git, "status", "--porcelain"], cwd=project, env=child)
    require(not status.stdout.strip(), "consumer checks/recovery left repository changes")
    return {
        "project": str(project),
        "engine_selection": selection,
        "baseline": f"{preset}-baseline.receipt.json",
        "restored": f"{preset}-restored.receipt.json",
        "repeated_setup": "passed",
        "behavioral_regression": "failed-as-required",
        "authored_conflict": "preserved",
        "final_clean": True,
    }


def verify(artifacts: Path, workspace: Path, evidence: Path) -> dict:
    require(
        os.name == "nt",
        "consumer execution requires actual native Windows; no simulated qualification",
    )
    require(
        not workspace.exists() and not evidence.exists(),
        "workspace and evidence must be fresh paths",
    )
    require(
        not evidence.is_relative_to(workspace) and not workspace.is_relative_to(evidence),
        "workspace and evidence must be separate directories",
    )
    evidence.mkdir(parents=True)
    report = {
        "schema": 1,
        "status": "failed",
        "platform": {
            "system": platform.platform(),
            "machine": platform.machine(),
            "edition": platform.win32_edition(),
        },
        "commands": [],
        "consumers": {},
        "limitations": [
            "Native Windows runner evidence only; no clean Windows 11 desktop qualification inferred.",
            "Installed harness recognition and account authentication are not assessed.",
            "Prerequisites/dependencies may download during explicit setup; no publication or remote mutation.",
        ],
    }
    journey = Journey(evidence, report)
    try:
        report["artifacts"] = validate_artifacts(artifacts)
        workspace.mkdir(parents=True)
        git_value = shutil.which("git.exe")
        require(git_value is not None, "Git prerequisite is unavailable")
        git = Path(git_value or "")
        system = Path(os.environ["SystemRoot"])
        powershell = system / "System32/WindowsPowerShell/v1.0/powershell.exe"
        require(powershell.is_file(), "inbox Windows PowerShell is unavailable")
        env = controlled_environment(workspace, git, system)
        report["initial_path"] = env["PATH"]
        revision = journey.run(
            "controller-revision", [git, "rev-parse", "HEAD"], cwd=ROOT, env=env
        ).stdout.strip()
        controller_status = journey.run(
            "controller-status", [git, "status", "--porcelain"], cwd=ROOT, env=env
        ).stdout.strip()
        report["controller"] = {
            "revision": revision,
            "dirty": bool(controller_status),
            "script_sha256": digest(Path(__file__).read_bytes()),
        }
        shell = journey.run(
            "powershell-version",
            [
                powershell,
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "$PSVersionTable.PSVersion.ToString()",
            ],
            cwd=workspace,
            env=env,
        )
        report["platform"]["powershell"] = shell.stdout.strip()
        seed = workspace / "bare seed é"
        for name, relative in {**NATIVE_ASSETS, "release.sh": "bootstrap/release.sh"}.items():
            target = seed / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(artifact_bytes(artifacts, name))
        (seed / "ai-dlc.toml").write_text("schema = 4\n", encoding="utf-8")
        manifest = report["artifacts"]["manifest"]
        home = Path(env["AI_DLC_BOOTSTRAP_HOME"])
        cache = home / "downloads"
        # Only the reviewed native helper creates the private namespace. A normal
        # mkdir/copy would inherit broad temp-directory permissions and be refused.
        script = f"$ErrorActionPreference='Stop'; . {quote_ps(seed / 'bootstrap/windows.ps1')}; Initialize-NativeStorage; $homeGuard=[AiDlc.Bootstrap.DirectoryGuard]::new({quote_ps(home)},$true,$true); try {{ $cache=[AiDlc.Bootstrap.DirectoryGuard]::new({quote_ps(cache)},$true,$true); try {{ "
        for source, destination, expected in (
            (
                manifest["AI_DLC_WHEEL_NAME"],
                manifest["AI_DLC_WHEEL_NAME"],
                manifest["AI_DLC_WHEEL_SHA256"],
            ),
            (
                "requirements.txt",
                "constraints-" + manifest["AI_DLC_CONSTRAINTS_SHA256"] + ".txt",
                manifest["AI_DLC_CONSTRAINTS_SHA256"],
            ),
        ):
            script += f"$bytes=[IO.File]::ReadAllBytes({quote_ps(artifacts / source)}); if((Get-BytesHash $bytes) -cne {quote_ps(expected)}) {{ throw 'Candidate cache source changed' }}; $cache.WriteNew({quote_ps(destination)},$bytes); "
        script += "} finally { $cache.Dispose() } } finally { $homeGuard.Dispose() }"
        journey.run(
            "prefill-verified-private-cache",
            [powershell, "-NoProfile", "-NonInteractive", "-Command", script],
            cwd=workspace,
            env=env,
        )
        journey.run(
            "bare-release-bootstrap",
            [
                powershell,
                "-NoProfile",
                "-NonInteractive",
                "-File",
                seed / "scripts/bootstrap.ps1",
                "-Root",
                seed,
            ],
            cwd=seed,
            env=env,
        )
        selection = json.loads((home / "bin/ai-dlc-selection.json").read_text())
        seed_cli = Path(selection["cli"])
        require(
            selection["mode"] == "release"
            and (seed_cli.parent.parent / "release.sh").read_bytes()
            == artifact_bytes(artifacts, "release.sh"),
            "bare installed engine lost exact manifest identity",
        )
        report["bare_seed"] = {"selection": selection, "manifest_preserved": True}
        # Subsequent consumers may use only the tools installed by this replay,
        # plus the original controlled system/Git PATH.
        env["PATH"] = str(home / "bin") + os.pathsep + env["PATH"]
        failed_bootstrap_preserves_session(journey, seed, workspace, env, powershell)
        for preset in ("generic", "python"):
            report["consumers"][preset] = consumer(
                journey, preset, seed_cli, artifacts, workspace, env, powershell, git
            )
            journey.save()
        require(
            validate_artifacts(artifacts) == report["artifacts"],
            "original artifacts changed during verification",
        )
        report["status"] = "passed"
    except BaseException as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        journey.save()
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    try:
        verify(args.artifacts.absolute(), args.workspace.absolute(), args.evidence.absolute())
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps({"status": "passed", "evidence": str(args.evidence / "result.json")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
