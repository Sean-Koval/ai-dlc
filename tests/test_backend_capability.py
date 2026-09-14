"""Optional backend scaffolds carry pinned contract checks without changing default roles."""

import json
import subprocess
import sys
import tomllib

import pytest
import yaml

from ai_dlc.setup.templates import adopt, plan_toolset


@pytest.mark.parametrize("preset", ["python", "node", "generic", "rust"])
def test_backend_contract_catalog_and_pinned_offline_checks(tmp_path, preset):
    root = tmp_path / preset
    result = adopt(root, preset=preset, capabilities=["backend"], initialize=True, apply=True)
    assert result["status"] == "applied"
    assert result["toolset"]["roles"] == {}
    contract = yaml.safe_load((root / "docs/api/openapi.yaml").read_text())
    assert contract["openapi"] == "3.1.0"
    assert set(contract["paths"]) == {"/health"}
    manifest = tomllib.loads((root / "ai-dlc.toml").read_text())
    assert "api-contract" in manifest["checks"]["required"]
    check = manifest["checks"]["commands"]["api-contract"]
    assert "--offline" in check
    assert "latest" not in check
    pin = "@redocly/cli@1.34.16" if preset == "node" else "openapi-spec-validator==0.7.2"
    assert pin in check
    assert any(pin in step["command"] for step in manifest["setup"]["steps"])
    if preset == "node":
        assert "--no-install" in check
    assert ("api-contract-drift" in manifest["checks"]["required"]) == (preset == "python")
    catalog = tomllib.loads((root / "docs/catalog.toml").read_text())
    assert any(entry["path"] == "docs/api/openapi.yaml" for entry in catalog["documents"])
    assert "backend" in yaml.safe_load((root / ".copier-answers.yml").read_text())["capabilities"]


def test_backend_is_opt_in_and_combines_with_provider_roles(tmp_path):
    default = tmp_path / "default"
    adopt(default, initialize=True, apply=True)
    assert not (default / "docs/api/openapi.yaml").exists()
    planned = plan_toolset(capabilities=["backend", "scm"])
    assert planned["roles"] == {"scm": "github"}


def run_drift(root):
    return subprocess.run(
        [sys.executable, "scripts/check_api_contract_drift.py"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_python_drift_skips_absent_or_other_framework_app(tmp_path):
    adopt(tmp_path, preset="python", capabilities=["backend"], initialize=True, apply=True)
    assert run_drift(tmp_path).returncode == 0
    assert "skipped" in run_drift(tmp_path).stdout
    pkg = tmp_path / "src/service"
    pkg.mkdir()
    (pkg / "app.py").write_text('raise RuntimeError("not FastAPI; must not import")\n')
    result = run_drift(tmp_path)
    assert result.returncode == 0 and "skipped" in result.stdout


def test_python_drift_compares_contract_and_reports_import_failure(tmp_path):
    adopt(tmp_path, preset="python", capabilities=["backend"], initialize=True, apply=True)
    # A bounded fixture supplies only the FastAPI surface used by the drift script.
    source = tmp_path / "src"
    (source / "fastapi.py").write_text(
        'class FastAPI:\n    def openapi(self):\n        return {"openapi": "3.1.0", "info": {"title": "Changed", "version": "1"}, "paths": {}}\n'
    )
    pkg = source / "service"
    pkg.mkdir()
    app = pkg / "app.py"
    app.write_text("from fastapi import FastAPI\napp = FastAPI()\n")
    contract = tmp_path / "docs/api/openapi.yaml"
    before = contract.read_bytes()
    result = run_drift(tmp_path)
    assert result.returncode == 1 and "--- docs/api/openapi.yaml" in result.stdout
    assert "+" in result.stdout and "Changed" in result.stdout
    assert contract.read_bytes() == before
    contract.write_text(
        json.dumps({"openapi": "3.1.0", "info": {"title": "Changed", "version": "1"}, "paths": {}})
    )
    assert run_drift(tmp_path).returncode == 0
    app.write_text('from fastapi import FastAPI\nraise RuntimeError("broken app")\n')
    result = run_drift(tmp_path)
    assert result.returncode != 0 and "broken app" in result.stderr
