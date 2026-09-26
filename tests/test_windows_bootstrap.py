"""Real PowerShell/native storage acceptance; skipped on non-Windows hosts."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NATIVE = pytest.mark.skipif(os.name != "nt", reason="requires native Windows PowerShell 5.1")


def ps(script: str, *, env=None):
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def quoted(path):
    return "'" + str(path).replace("'", "''") + "'"


def helpers():
    return f"$ErrorActionPreference='Stop'; . {quoted(ROOT / 'bootstrap/windows.ps1')}; "


def test_native_bootstrap_assets_are_distributable():
    # Missing any helper makes a generated consumer bootstrap unusable.
    for name in (
        "scripts/bootstrap.ps1",
        "bootstrap/windows.ps1",
        "bootstrap/windows-native.cs",
        "bootstrap/windows.json",
    ):
        assert (ROOT / name).is_file(), name
        assert (ROOT / name).read_bytes() == (
            ROOT / "project-templates/project" / name
        ).read_bytes()


@NATIVE
def test_native_plan_has_no_filesystem_effects(tmp_path):
    home = tmp_path / "uncreated space ü"
    env = dict(os.environ, AI_DLC_BOOTSTRAP_HOME=str(home))
    result = ps(
        f"& {quoted(ROOT / 'scripts/bootstrap.ps1')} -Source -Plan -Root {quoted(ROOT)}", env=env
    )
    assert result.returncode == 0, result.stderr
    assert "0.9.11" in result.stdout and "3.12.11" in result.stdout
    assert not home.exists()


@NATIVE
@pytest.mark.parametrize(
    "extra",
    [
        "AI_DLC_ENGINE_VERSION=0.4.0",
        "evil=$(Set-Content injected yes)",
        "AI_DLC_WHEEL_URL=https://good.test/a;Write-Output injected",
        "AI_DLC_UNEXPECTED=value",
    ],
)
def test_native_manifest_rejects_expressions_unknowns_and_duplicates(tmp_path, extra):
    manifest = tmp_path / "release.sh"
    manifest.write_text(
        "AI_DLC_ENGINE_VERSION=0.4.0\nAI_DLC_WHEEL_NAME=ai_dlc-0.4.0-py3-none-any.whl\nAI_DLC_WHEEL_URL=https://example.test/ai_dlc-0.4.0-py3-none-any.whl\nAI_DLC_WHEEL_SHA256="
        + "a" * 64
        + "\nAI_DLC_CONSTRAINTS_URL=https://example.test/requirements.txt\nAI_DLC_CONSTRAINTS_SHA256="
        + "b" * 64
        + "\n"
        + extra
        + "\n"
    )
    result = ps(helpers() + f"Read-ReleaseManifest {quoted(manifest)}")
    assert result.returncode != 0
    assert not (tmp_path / "injected").exists()


@NATIVE
def test_native_cold_publication_is_complete_refuses_sharing_and_recovers(tmp_path):
    result = ps(
        helpers()
        + f"""
Initialize-NativeStorage
$g = [AiDlc.Bootstrap.DirectoryGuard]::new({quoted(tmp_path / "owned")}, $true, $true)
try {{
  $g.WriteNew('tool.exe', [byte[]](1,2,3))
  $g.WriteNew('next.exe', [byte[]](4,5,6))
  $reader = $g.OpenRead('tool.exe')
  try {{
    try {{ $g.Publish('next.exe', $g, 'tool.exe', $true); throw 'unexpected success' }}
    catch {{ if ($_.Exception.Message -like '*unexpected success*') {{ throw }} }}
    if (($g.Read('tool.exe') -join ',') -ne '1,2,3') {{ throw 'old executable changed' }}
  }} finally {{ $reader.Dispose() }}
  $g.Publish('next.exe', $g, 'tool.exe', $true)
  if (($g.Read('tool.exe') -join ',') -ne '4,5,6') {{ throw 'retry failed' }}
}} finally {{ $g.Dispose() }}
"""
    )
    assert result.returncode == 0, result.stderr


@NATIVE
def test_native_cache_corruption_is_refused_without_execution(tmp_path):
    result = ps(
        helpers()
        + f"""
Initialize-NativeStorage
$g = [AiDlc.Bootstrap.DirectoryGuard]::new({quoted(tmp_path / "owned")}, $true, $true)
try {{
  $g.WriteNew('uv.zip', [byte[]](1,2,3))
  Get-VerifiedArtifact $g 'uv.zip' 'https://example.invalid/unreachable' '{"0" * 64}'
}} finally {{ $g.Dispose() }}
"""
    )
    assert result.returncode != 0
    assert "digest" in result.stderr.lower()


@NATIVE
def test_native_cold_namespace_refuses_junction(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    junction = tmp_path / "redirect"
    result = ps(
        helpers()
        + f"""
Initialize-NativeStorage
New-Item -ItemType Junction -Path {quoted(junction)} -Target {quoted(outside)} | Out-Null
$g = [AiDlc.Bootstrap.DirectoryGuard]::new({quoted(junction / "owned")}, $true, $true)
$g.Dispose()
"""
    )
    assert result.returncode != 0
    assert not list(outside.iterdir())


@NATIVE
def test_native_manifest_valid_data_is_inert_and_complete(tmp_path):
    manifest = tmp_path / "release.sh"
    manifest.write_text(
        "# generated\nAI_DLC_ENGINE_VERSION=0.4.0\nAI_DLC_WHEEL_NAME=ai_dlc-0.4.0-py3-none-any.whl\nAI_DLC_WHEEL_URL=https://example.test/ai_dlc-0.4.0-py3-none-any.whl\nAI_DLC_WHEEL_SHA256="
        + "a" * 64
        + "\nAI_DLC_CONSTRAINTS_URL=https://example.test/requirements.txt\nAI_DLC_CONSTRAINTS_SHA256="
        + "b" * 64
        + "\n"
    )
    result = ps(
        helpers()
        + f"$m=Read-ReleaseManifest {quoted(manifest)}; if($m.Count -ne 6 -or $m.AI_DLC_ENGINE_VERSION -ne '0.4.0') {{ throw 'identity lost' }}"
    )
    assert result.returncode == 0, result.stderr


@NATIVE
@pytest.mark.parametrize("entry", ["../uv.exe", "/uv.exe", "dir/../../uv.exe", "uv.exe:alternate"])
def test_native_archive_escape_is_refused_without_writes(tmp_path, entry):
    import zipfile

    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr(entry, b"untrusted")
    result = ps(
        helpers()
        + f"""
Initialize-NativeStorage
$g=[AiDlc.Bootstrap.DirectoryGuard]::new({quoted(tmp_path / "stage")}, $true, $true)
try {{ Expand-UvArchive ([IO.File]::ReadAllBytes({quoted(archive)})) $g }} finally {{ $g.Dispose() }}
"""
    )
    assert result.returncode != 0
    assert not list((tmp_path / "stage").iterdir())


@NATIVE
def test_native_cold_lock_excludes_concurrent_publisher_and_recovers(tmp_path):
    result = ps(
        helpers()
        + f"""
Initialize-NativeStorage
$g=[AiDlc.Bootstrap.DirectoryGuard]::new({quoted(tmp_path / "owned")}, $true, $true)
try {{
 $first=$g.Lock('publish.lock')
 try {{
  try {{ $second=$g.Lock('publish.lock'); $second.Dispose(); throw 'concurrent publisher admitted' }}
  catch {{ if($_.Exception.Message -like '*concurrent publisher admitted*') {{ throw }} }}
 }} finally {{ $first.Dispose() }}
 $retry=$g.Lock('publish.lock'); $retry.Dispose()
}} finally {{ $g.Dispose() }}
"""
    )
    assert result.returncode == 0, result.stderr


@NATIVE
def test_native_cold_namespace_refuses_broad_dacl(tmp_path):
    owned = tmp_path / "broad"
    result = ps(
        helpers()
        + f"""
Initialize-NativeStorage
New-Item -ItemType Directory -Path {quoted(owned)} | Out-Null
$acl=Get-Acl -LiteralPath {quoted(owned)}
$acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new('Everyone','FullControl','ContainerInherit,ObjectInherit','None','Allow'))
Set-Acl -LiteralPath {quoted(owned)} -AclObject $acl
$g=[AiDlc.Bootstrap.DirectoryGuard]::new({quoted(owned)}, $true, $true)
$g.Dispose()
"""
    )
    assert result.returncode != 0
    assert "DACL" in result.stderr


@NATIVE
@pytest.mark.parametrize("plan", [True, False])
def test_native_root_junction_refused_before_installation(tmp_path, plan):
    junction = tmp_path / "redirect"
    home = tmp_path / "must-not-exist"
    setup = ps(
        f"New-Item -ItemType Junction -Path {quoted(junction)} -Target {quoted(ROOT)} | Out-Null"
    )
    assert setup.returncode == 0, setup.stderr
    result = ps(
        f"& {quoted(ROOT / 'scripts/bootstrap.ps1')} -Source {'-Plan' if plan else ''} -Root {quoted(junction)}",
        env=dict(os.environ, AI_DLC_BOOTSTRAP_HOME=str(home)),
    )
    assert result.returncode != 0
    assert "reparse" in result.stderr.lower()
    assert not home.exists()
