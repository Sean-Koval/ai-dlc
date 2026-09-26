import json
import os
import subprocess
from pathlib import Path

import pytest


def test_frontend_scaffold_fails_before_package_tools_without_a_target_url(tmp_path):
    import tomllib

    from ai_dlc.setup.templates import adopt

    root = tmp_path / "app"
    adopt(root, "node", True, initialize=True, capabilities=["frontend"])
    config = tomllib.loads((root / "ai-dlc.toml").read_text())
    assert "frontend-smoke" in config["checks"]["required"]
    assert "frontend" not in config["roles"]
    assert "## Frontend" in (root / "docs/workflows/design-to-implementation.md").read_text()
    assert (root / "tests/e2e/smoke.spec.ts").is_file()
    assert (root / "playwright.config.ts").is_file()
    assert (
        json.loads((root / "package.json").read_text())["devDependencies"]["@playwright/test"]
        == "1.58.2"
    )
    marker = tmp_path / "npx-called"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    npx = fake_bin / "npx"
    npx.write_text(
        "#!/bin/sh\n"
        ': > "$FAKE_NPX_MARKER"\n'
        'printf "%s" "$*" > "$FAKE_NPX_ARGS"\n'
        'exit "${FAKE_NPX_EXIT:-0}"\n'
    )
    npx.chmod(0o755)
    arguments = tmp_path / "npx-args"
    env = dict(
        os.environ,
        PATH=f"{fake_bin}:/usr/bin:/bin",
        FAKE_NPX_MARKER=str(marker),
        FAKE_NPX_ARGS=str(arguments),
    )
    env.pop("BASE_URL", None)
    result = subprocess.run(
        config["checks"]["commands"]["frontend-smoke"],
        shell=True,
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "BASE_URL" in result.stdout + result.stderr
    assert "running app" in result.stdout + result.stderr
    assert not marker.exists()
    assert not (root / "node_modules").exists()

    env["BASE_URL"] = "http://127.0.0.1:1"
    env["FAKE_NPX_EXIT"] = "7"
    failed = subprocess.run(
        config["checks"]["commands"]["frontend-smoke"],
        shell=True,
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert failed.returncode == 7
    assert marker.is_file()
    assert arguments.read_text() == "--offline --no-install playwright test --reporter=line"
    marker.unlink()
    env["FAKE_NPX_EXIT"] = "0"
    passed = subprocess.run(
        config["checks"]["commands"]["frontend-smoke"],
        shell=True,
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert passed.returncode == 0
    assert marker.is_file()
    with pytest.raises(ValueError, match="node preset"):
        adopt(tmp_path / "wrong", "python", True, capabilities=["frontend"])


def test_capture_manifest_and_containment(tmp_path, monkeypatch):
    from ai_dlc.harness.design_capture import capture_design

    calls = []

    def screenshot(args, **kwargs):
        calls.append((args, kwargs))
        Path(args[-1]).write_bytes(b"\x89PNG\r\n\x1a\nfixture")
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(subprocess, "run", screenshot)
    result = capture_design(
        tmp_path,
        url="http://localhost:8000",
        out=Path(".ai-dlc/local/design/demo"),
        viewports=["1280x800", "390x844"],
        states=["ready=#ready"],
    )
    manifest = json.loads(Path(result["manifest"]).read_text())
    assert len(manifest["files"]) == 2
    assert manifest["states"] == [{"name": "ready", "selector": "#ready"}]
    assert all((Path(result["manifest"]).parent / file).is_file() for file in manifest["files"])
    assert all("--no-install" in args and "--wait-for-selector" in args for args, _ in calls)
    assert all(kwargs["env"]["PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD"] == "1" for _, kwargs in calls)
    for destination in [Path("../outside"), tmp_path.parent / "outside"]:
        with pytest.raises(ValueError):
            capture_design(tmp_path, url="http://localhost", out=destination)
    assert len(calls) == 2


def test_capture_refuses_unsafe_states_symlinks_and_failed_capture(tmp_path, monkeypatch):
    from ai_dlc.harness.design_capture import capture_design

    (tmp_path / "linked").symlink_to(tmp_path.parent, target_is_directory=True)
    for kwargs in [
        {"out": Path("linked/capture")},
        {"states": ["../escape=body"]},
        {"viewports": ["0x800"]},
    ]:
        with pytest.raises(ValueError):
            capture_design(tmp_path, url="http://localhost", **kwargs)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda args, **kwargs: subprocess.CompletedProcess(args, 1, "", "browser unavailable"),
    )
    with pytest.raises(RuntimeError, match="browser unavailable"):
        capture_design(tmp_path, url="http://localhost", out=Path("capture"))
    assert not (tmp_path / "capture/manifest.json").exists()


@pytest.mark.parametrize("capabilities", [["frontend"], ["backend", "frontend"]])
def test_frontend_capture_and_smoke_against_real_local_page(tmp_path, monkeypatch, capabilities):
    """Optional local qualification after explicit pinned Playwright/browser setup."""
    import contextlib
    import functools
    import http.server
    import threading
    import tomllib

    from ai_dlc.harness.design_capture import capture_design
    from ai_dlc.setup.templates import adopt

    configured = os.environ.get("AI_DLC_PLAYWRIGHT_TEST_ROOT")
    if not configured:
        pytest.skip("Explicit Playwright/browser setup is required for live local qualification")
    runtime = Path(configured)
    root = tmp_path / "app"
    adopt(root, "node", True, initialize=True, capabilities=capabilities)
    (root / "node_modules").symlink_to(runtime / "node_modules", target_is_directory=True)
    missing_env = dict(os.environ)
    missing_env.pop("BASE_URL", None)
    direct = subprocess.run(
        ["npx", "--offline", "--no-install", "playwright", "test", "--reporter=line"],
        cwd=root,
        env=missing_env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert direct.returncode != 0
    assert "BASE_URL" in direct.stdout + direct.stderr
    assert "running app" in direct.stdout + direct.stderr
    (root / "index.html").write_text(
        '<!doctype html><title>Frontend fixture</title><main id="ready">Ready</main>'
    )
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    with http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}"
            monkeypatch.setenv("BASE_URL", url)
            config = tomllib.loads((root / "ai-dlc.toml").read_text())
            smoke = subprocess.run(
                config["checks"]["commands"]["frontend-smoke"],
                cwd=root,
                shell=True,
                text=True,
                capture_output=True,
                check=False,
            )
            assert smoke.returncode == 0, smoke.stdout + smoke.stderr
            assert (root / ".ai-dlc/local/design/smoke/smoke.png").is_file()
            result = capture_design(
                root,
                url=url,
                out=Path(".ai-dlc/local/design/capture"),
                viewports=["1280x800", "390x844"],
                states=["ready=#ready"],
            )
            manifest = json.loads(Path(result["manifest"]).read_text())
            assert len(manifest["files"]) == 2
            import struct

            for dimensions, filename in zip(manifest["viewports"], manifest["files"], strict=True):
                data = (Path(result["manifest"]).parent / filename).read_bytes()
                assert struct.unpack(">II", data[16:24]) == tuple(map(int, dimensions.split("x")))
        finally:
            server.shutdown()
            with contextlib.suppress(RuntimeError):
                thread.join(timeout=5)


def test_frontend_adoption_preserves_application_and_default_scaffold(tmp_path):
    from ai_dlc.setup.templates import adopt

    default = tmp_path / "default"
    adopt(default, "node", True, initialize=True)
    assert not (default / "playwright.config.ts").exists()
    assert not (default / "tests/e2e/smoke.spec.ts").exists()
    assert "@playwright/test" not in (default / "package.json").read_text()
    existing = tmp_path / "existing"
    existing.mkdir()
    manifest = '{"name":"user-owned","dependencies":{"example":"1.0.0"}}\n'
    (existing / "package.json").write_text(manifest)
    adopt(existing, "node", True, capabilities=["frontend"])
    assert (existing / "package.json").read_text() == manifest
    assert (existing / "playwright.config.ts").is_file()


def test_design_capture_cli_emits_manifest_and_refuses_invalid_input(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    from ai_dlc.cli import app

    def screenshot(args, **kwargs):
        Path(args[-1]).write_bytes(b"\x89PNG\r\n\x1a\nfixture")
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(subprocess, "run", screenshot)
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "design",
            "capture",
            "--url",
            "http://localhost",
            "--root",
            str(tmp_path),
            "--out",
            "capture",
            "--viewport",
            "800x600",
            "--state",
            "ready=main",
        ],
    )
    assert result.exit_code == 0, result.output
    assert Path(json.loads(result.stdout)["manifest"]).is_file()
    refused = runner.invoke(
        app, ["design", "capture", "--url", "file:///etc/passwd", "--root", str(tmp_path)]
    )
    assert refused.exit_code != 0
    assert "HTTP(S)" in refused.output


@pytest.mark.parametrize("packs", [["backend", "frontend"], ["frontend", "backend"]])
@pytest.mark.parametrize("with_scm", [False, True])
def test_joint_node_packs_preserve_selection_setup_and_checks(tmp_path, packs, with_scm):
    import tomllib

    import yaml

    from ai_dlc.setup.templates import adopt

    capabilities = packs + (["scm"] if with_scm else [])
    root = tmp_path / "joint"
    result = adopt(root, "node", True, initialize=True, capabilities=capabilities)
    expected_roles = {"scm": "github"} if with_scm else {}
    assert result["toolset"]["roles"] == expected_roles
    config = tomllib.loads((root / "ai-dlc.toml").read_text())
    assert config["roles"] == expected_roles
    saved = yaml.safe_load((root / ".copier-answers.yml").read_text())["capabilities"]
    assert set(saved) == set(capabilities)
    assert len(saved) == len(capabilities)
    assert set(config["checks"]["required"]) == {
        "generated",
        "work-records",
        "language-check",
        "frontend-smoke",
        "api-contract",
    }
    assert "api-contract-drift" not in config["checks"]["commands"]
    steps = config["setup"]["steps"]
    assert [step["id"] for step in steps] == ["dependencies", "api-contract-tools"]
    assert "PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm ci" in steps[0]["command"]
    assert "@redocly/cli@1.34.16" in steps[1]["command"]
    assert tomllib.loads((root / ".mise.toml").read_text())["tools"]["node"] == "22.23.1"
    assert (
        json.loads((root / "package.json").read_text())["devDependencies"]["@playwright/test"]
        == "1.58.2"
    )
    assert (root / "docs/api/openapi.yaml").is_file()
    assert (root / "playwright.config.ts").is_file()
    assert (root / "tests/e2e/smoke.spec.ts").is_file()
    assert not (root / "scripts/check_api_contract_drift.py").exists()
    assert (root / ".github").exists() == with_scm
    authored = tmp_path / "authored"
    authored.mkdir()
    manifest = '{"name":"keep-authored","scripts":{"test":"custom"}}\n'
    (authored / "package.json").write_text(manifest)
    adopt(authored, "node", True, capabilities=capabilities)
    assert (authored / "package.json").read_text() == manifest
