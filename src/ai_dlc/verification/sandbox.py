"""Fail-closed Docker conformance runner; never falls back to host execution."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path


def validate_test_manifest(manifest: dict, live: bool = False) -> None:
    if not re.fullmatch(r"[^\s]+@sha256:[0-9a-f]{64}", manifest.get("image", "")):
        raise ValueError("provider test image must be pinned by digest")
    if live:
        if not manifest.get("sandbox_workspace") or not manifest.get("credential_env"):
            raise ValueError(
                "live tests require designated sandbox workspace and explicit credential_env"
            )
        for field in ["proxy_image", "enforcement_image"]:
            if not re.fullmatch(r"[^\s]+@sha256:[0-9a-f]{64}", manifest.get(field, "")):
                raise ValueError(f"{field} must be pinned by digest")
        if not manifest.get("allow_hosts"):
            raise ValueError("live tests require explicit allow_hosts")
        for host in manifest["allow_hosts"]:
            if not re.fullmatch(r"[a-z0-9.-]+", host) or "." not in host:
                raise ValueError("allow_hosts must contain exact DNS names")
        for name in manifest["credential_env"]:
            if not re.fullmatch(r"[A-Z_][A-Z0-9_]*", name) or not os.environ.get(name):
                raise ValueError(f"explicit live credential unavailable: {name}")


def _docker(*args: str, check: bool = True, timeout: int = 120):
    return subprocess.run(
        ["docker", *args], check=check, capture_output=True, text=True, timeout=timeout
    )


_COMMON_RUN_ARGS = [
    "--rm",
    "--read-only",
    "--cap-drop=ALL",
    "--security-opt=no-new-privileges",
    "--pids-limit=128",
    "--memory=512m",
    "--tmpfs=/tmp:rw,noexec,nosuid,size=128m",
    "--tmpfs=/work:rw,exec,nosuid,mode=1777,size=128m",
    "--env=TMPDIR=/work",
]


def _require_docker(name: str, manifest: dict, live: bool) -> None:
    """Fail closed unless Docker is present, ready and the manifest names this provider."""
    if not shutil.which("docker"):
        raise RuntimeError(
            "provider test environment unavailable: Docker is required; host fallback disabled"
        )
    validate_test_manifest(manifest, live)
    try:
        _docker("info", timeout=15)
    except (subprocess.SubprocessError, OSError) as exc:
        raise RuntimeError(
            "provider test environment unavailable: Docker daemon not ready"
        ) from exc
    if name not in manifest.get("providers", []):
        raise ValueError(f"unsupported test target: {name} has no compatible artifact")


def _stage_fixtures(manifest: dict, fixtures: str) -> None:
    """Copy packaged conformance fixtures only; never host home/credential directories."""
    fixture_source = manifest.get("fixtures")
    if fixture_source:
        source = Path(fixture_source).resolve()
        if any(p.is_symlink() for p in source.rglob("*")):
            raise ValueError("test fixtures cannot include symlinks")
        shutil.copytree(source, fixtures, dirs_exist_ok=True)


def _firewall_rules(proxy_ip: str) -> str:
    """OUTPUT policy installed by the namespace owner: loopback, established, proxy only."""
    return "\n".join(
        [
            "set -eu",
            "iptables -P OUTPUT DROP",
            "ip6tables -P OUTPUT DROP",
            "iptables -A OUTPUT -o lo -j ACCEPT",
            "iptables -A OUTPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT",
            f"iptables -A OUTPUT -p tcp -d {proxy_ip} --dport 8080 -j ACCEPT",
            "touch /tmp/enforced",
            "exec sleep 3600",
        ]
    )


def _live_env_args(manifest: dict, proxy_ip: str) -> list[str]:
    """Provider environment routing every request through the allowlist proxy."""
    env_args = [
        "--env",
        "HTTPS_PROXY=http://" + proxy_ip + ":8080",
        "--env",
        "HTTP_PROXY=http://" + proxy_ip + ":8080",
        "--env",
        "NO_PROXY=",
        "--env",
        "AI_DLC_SANDBOX_WORKSPACE=" + manifest["sandbox_workspace"],
    ]
    for variable in manifest["credential_env"]:
        env_args.extend(["--env", variable])
    return env_args


def _egress_probe(proxy_ip: str) -> str:
    """Python snippet proving direct egress is blocked and undeclared hosts are refused."""
    return (
        "import socket; "
        "s=socket.socket(); s.settimeout(2); "
        "code=s.connect_ex(('1.1.1.1',443)); assert code!=0,'direct egress allowed'; "
        f"p=socket.create_connection(('{proxy_ip}',8080),5); "
        "p.sendall(b'CONNECT undeclared.invalid:443 HTTP/1.1\\r\\n\\r\\n'); "
        "assert b'403' in p.recv(1024),'undeclared host allowed'"
    )


def _start_proxy(
    uid: str, manifest: dict, common: list[str], networks: list[str], containers: list[str]
) -> tuple[str, str]:
    """Create the internal/external networks and the allowlist proxy; return (internal, ip)."""
    internal, external = uid + "-internal", uid + "-external"
    _docker("network", "create", "--internal", internal)
    networks.append(internal)
    _docker("network", "create", external)
    networks.append(external)
    proxy = uid + "-proxy"
    proxy_file = Path(__file__).with_name("test_proxy.py").resolve()
    _docker(
        "run",
        "-d",
        "--name",
        proxy,
        *common[1:],
        "--network",
        external,
        "--env",
        "ALLOW_HOSTS=" + ",".join(manifest["allow_hosts"]),
        "--mount",
        f"type=bind,src={proxy_file},dst=/proxy.py,readonly",
        manifest["proxy_image"],
        "python",
        "/proxy.py",
    )
    containers.append(proxy)
    _docker("network", "connect", internal, proxy)
    proxy_ip = _docker(
        "inspect",
        "--format",
        '{{(index .NetworkSettings.Networks "' + internal + '").IPAddress}}',
        proxy,
    ).stdout.strip()
    if not re.fullmatch(r"[0-9.]+", proxy_ip):
        raise RuntimeError("enforcement backend returned invalid proxy address")
    return internal, proxy_ip


def _start_enforcement(
    uid: str,
    manifest: dict,
    common: list[str],
    internal: str,
    proxy_ip: str,
    containers: list[str],
) -> str:
    """Start the namespace owner that installs the OUTPUT policy; return its network ref."""
    keeper = uid + "-network"
    # Dedicated namespace owner installs OUTPUT policy. Provider shares the
    # namespace without NET_ADMIN and cannot loosen these firewall rules.
    _docker(
        "run",
        "-d",
        "--name",
        keeper,
        *common[1:],
        "--cap-add=NET_ADMIN",
        "--network",
        internal,
        manifest["enforcement_image"],
        "sh",
        "-c",
        _firewall_rules(proxy_ip),
    )
    containers.append(keeper)
    _docker(
        "exec",
        keeper,
        "sh",
        "-c",
        "for n in 1 2 3 4 5; do test -f /tmp/enforced && exit 0; sleep 1; done; exit 1",
    )
    return "container:" + keeper


def _prepare_live_isolation(
    uid: str, manifest: dict, common: list[str], networks: list[str], containers: list[str]
) -> tuple[str, list[str]]:
    """Bring up proxy and firewall, probe enforcement; return (network, env_args)."""
    internal, proxy_ip = _start_proxy(uid, manifest, common, networks, containers)
    network = _start_enforcement(uid, manifest, common, internal, proxy_ip, containers)
    env_args = _live_env_args(manifest, proxy_ip)
    _docker(
        "run",
        *common,
        "--network",
        network,
        manifest["proxy_image"],
        "python",
        "-c",
        _egress_probe(proxy_ip),
    )
    return network, env_args


def _summarize_run(name: str, result, live: bool) -> dict:
    """Shape the conformance container outcome into the reported result."""
    return {
        "provider": name,
        "passed": result.returncode == 0,
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "live": live,
        "isolation": "namespace-firewall-and-allowlist-proxy" if live else "network-none",
    }


def test_provider(name: str, manifest: dict, live: bool = False) -> dict:
    _require_docker(name, manifest, live)
    uid = "ai-dlc-test-" + uuid.uuid4().hex[:12]
    networks: list[str] = []
    containers: list[str] = []
    common = list(_COMMON_RUN_ARGS)
    with tempfile.TemporaryDirectory(prefix="ai-dlc-fixtures-") as fixtures:
        _stage_fixtures(manifest, fixtures)
        try:
            env_args = ["--env", "AI_DLC_TEST_TOKEN=fake-credential"]
            network = "none"
            if live:
                network, env_args = _prepare_live_isolation(
                    uid, manifest, common, networks, containers
                )
            result = _docker(
                "run",
                *common,
                "--network",
                network,
                "--user",
                "65534:65534",
                "--mount",
                f"type=bind,src={fixtures},dst=/fixtures,readonly",
                *env_args,
                manifest["image"],
                "ai-dlc-conformance",
                name,
                *(["--live"] if live else []),
                check=False,
                timeout=300,
            )
            return _summarize_run(name, result, live)
        except subprocess.SubprocessError as exc:
            raise RuntimeError(
                "provider test environment unavailable or enforcement failed; no host fallback"
            ) from exc
        finally:
            for container in reversed(containers):
                _docker("rm", "-f", container, check=False)
            for network_name in reversed(networks):
                _docker("network", "rm", network_name, check=False)
