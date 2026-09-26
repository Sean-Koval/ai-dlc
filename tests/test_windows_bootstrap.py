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
$original=[AiDlc.Bootstrap.DirectoryGuard]::new({quoted(owned)}, $true, $true)
$original.Dispose()
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


@NATIVE
@pytest.mark.parametrize("replace", [True, False])
def test_native_cold_publication_rejects_late_stage_changes(tmp_path, replace):
    mutation = (
        "$g.Publish('stage.exe', $g, 'retained.exe', $false); $g.WriteNew('stage.exe', [byte[]](1,2,3))"
        if replace
        else "[IO.File]::WriteAllBytes((Join-Path $g.PathName 'stage.exe'), [byte[]](9,9,9))"
    )
    # Replacement happens outside the guard's creator API, so the invocation cannot adopt it.
    if replace:
        mutation = "[IO.File]::Move((Join-Path $g.PathName 'stage.exe'), (Join-Path $g.PathName 'retained.exe')); [IO.File]::WriteAllBytes((Join-Path $g.PathName 'stage.exe'), [byte[]](1,2,3))"
    result = ps(
        helpers()
        + f"""
Initialize-NativeStorage
$g=[AiDlc.Bootstrap.DirectoryGuard]::new({quoted(tmp_path / "owned")}, $true, $true)
try {{
 $g.WriteNew('stage.exe', [byte[]](1,2,3))
 {mutation}
 try {{ $g.Publish('stage.exe', $g, 'selected.exe', $false); throw 'adopted changed stage' }}
 catch {{ if($_.Exception.Message -like '*adopted changed stage*') {{ throw }} }}
}} finally {{ $g.Dispose() }}
"""
    )
    assert result.returncode == 0, result.stderr
    assert not (tmp_path / "owned/selected.exe").exists()
    assert (tmp_path / "owned/stage.exe").read_bytes() == (
        b"\x01\x02\x03" if replace else b"\x09\x09\x09"
    )


def selection_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "native_bootstrap_selection", ROOT / "bootstrap/windows-select.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def engine_fixture(tmp_path, name):
    import sys

    environment = tmp_path / name
    scripts = environment / "Scripts"
    scripts.mkdir(parents=True)
    # Use a real uv-created, runnable console launcher; its interpreter binding stays intact.
    launcher = Path(sys.prefix) / "Scripts/ai-dlc.exe"
    assert launcher.is_file(), (
        "Native bootstrap acceptance requires an installed engine console launcher"
    )
    (scripts / "ai-dlc.exe").write_bytes(launcher.read_bytes())
    (environment / "ai-dlc-source-root").write_text(str(tmp_path / f"checkout-{name}"))
    (environment / "ai-dlc-source-revision").write_text("fixture-provenance")
    return environment


@NATIVE
def test_native_selection_preserves_working_source_until_explicit_publication(tmp_path):
    selection = selection_module()
    home = tmp_path / "home"
    (home / "bin").mkdir(parents=True)
    first = engine_fixture(tmp_path, "one")
    second = engine_fixture(tmp_path, "two")
    assert selection.select(home, first, "source", False)["published"]
    before = (home / "bin/ai-dlc-selection.json").read_bytes()
    result = selection.select(home, second, "source", False)
    assert not result["published"]
    assert (home / "bin/ai-dlc-selection.json").read_bytes() == before
    result = selection.select(home, second, "source", True)
    assert result["published"]
    assert result["selected"]["source_root"] == str(tmp_path / "checkout-two")
    executed = subprocess.run(
        [str(home / "bin/ai-dlc.exe"), "--version"], capture_output=True, check=False
    )
    assert executed.returncode == 0, executed.stderr


@NATIVE
def test_native_selection_sharing_failure_restores_all_previous_selection(tmp_path):
    selection = selection_module()
    home = tmp_path / "home"
    (home / "bin").mkdir(parents=True)
    first = engine_fixture(tmp_path, "one")
    second = engine_fixture(tmp_path, "two")
    selection.select(home, first, "source", False)
    names = ("ai-dlc.exe", "ai-dlc-cli.exe", "ai-dlc-selection.json")
    before = {name: (home / "bin" / name).read_bytes() for name in names}
    with (home / "bin/ai-dlc.exe").open("rb"), pytest.raises(OSError):
        selection.select(home, second, "source", True)
    assert {name: (home / "bin" / name).read_bytes() for name in names} == before
    assert selection.select(home, second, "source", True)["published"]


@NATIVE
def test_native_selection_refuses_authored_launcher_edits(tmp_path):
    selection = selection_module()
    home = tmp_path / "home"
    (home / "bin").mkdir(parents=True)
    first = engine_fixture(tmp_path, "one")
    selection.select(home, first, "source", False)
    (home / "bin/ai-dlc.exe").write_bytes(b"authored replacement")
    with pytest.raises(ValueError, match="authored changes"):
        selection.select(home, first, "source", True)
    assert (home / "bin/ai-dlc.exe").read_bytes() == b"authored replacement"


@NATIVE
def test_native_valid_cache_is_rehashed_and_reused_without_network(tmp_path):
    import hashlib

    payload = b"cached reviewed artifact"
    checksum = hashlib.sha256(payload).hexdigest()
    result = ps(
        helpers()
        + f"""
Initialize-NativeStorage
$g=[AiDlc.Bootstrap.DirectoryGuard]::new({quoted(tmp_path / "owned")}, $true, $true)
try {{
 $g.WriteNew('asset', [Text.Encoding]::UTF8.GetBytes('cached reviewed artifact'))
 $bytes=Get-VerifiedArtifact $g 'asset' 'https://example.invalid/no-network' '{checksum}'
 if([Text.Encoding]::UTF8.GetString($bytes) -ne 'cached reviewed artifact') {{ throw 'wrong cached bytes' }}
}} finally {{ $g.Dispose() }}
"""
    )
    assert result.returncode == 0, result.stderr


@NATIVE
def test_native_uv_archive_extracts_only_verified_x64_executables(tmp_path):
    import sys
    import zipfile

    # Real native PE bytes exercise the parser/extractor, without running fake tool names.
    executable = Path(sys.executable).read_bytes()
    archive = tmp_path / "valid.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("uv.exe", executable)
        output.writestr("uvx.exe", executable)
    result = ps(
        helpers()
        + f"""
Initialize-NativeStorage
$g=[AiDlc.Bootstrap.DirectoryGuard]::new({quoted(tmp_path / "stage")}, $true, $true)
try {{
 $digests=Expand-UvArchive ([IO.File]::ReadAllBytes({quoted(archive)})) $g
 if($digests.Count -ne 2) {{ throw 'incomplete uv toolchain' }}
}} finally {{ $g.Dispose() }}
"""
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "stage/uv.exe").read_bytes() == executable
    assert (tmp_path / "stage/uvx.exe").read_bytes() == executable


@NATIVE
def test_native_wrong_architecture_refused_before_use():
    result = ps(
        helpers()
        + """
$bytes=New-Object byte[] 128
$bytes[0]=77; $bytes[1]=90; $bytes[60]=64
$bytes[64]=80; $bytes[65]=69; $bytes[68]=100; $bytes[69]=170
Assert-X64Executable $bytes
"""
    )
    assert result.returncode != 0
    assert "x64" in result.stderr


@NATIVE
def test_native_managed_python_child_junction_is_refused(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    version = tmp_path / "python/cpython-3.12.11-windows-x86_64-none"
    version.parent.mkdir()
    result = ps(
        helpers()
        + f"""
Initialize-NativeStorage
New-Item -ItemType Junction -Path {quoted(version)} -Target {quoted(outside)} | Out-Null
$p=Open-ManagedPython {quoted(version.parent)} '3.12.11'
if($null -ne $p) {{ $p.Reader.Dispose(); $p.Guard.Dispose() }}
"""
    )
    assert result.returncode != 0
    assert not list(outside.iterdir())


@NATIVE
def test_native_release_stage_refuses_cache_swap_after_verification(tmp_path):
    import hashlib

    payload = b"reviewed wheel"
    sha = hashlib.sha256(payload).hexdigest()
    result = ps(
        helpers()
        + f"""
Initialize-NativeStorage
$g=[AiDlc.Bootstrap.DirectoryGuard]::new({quoted(tmp_path / "owned")}, $true, $true)
try {{
 $g.WriteNew('asset.whl', [Text.Encoding]::UTF8.GetBytes('reviewed wheel'))
 $verified=Get-VerifiedArtifact $g 'asset.whl' 'https://example.invalid/offline' '{sha}'
 [IO.File]::WriteAllText((Join-Path $g.PathName 'asset.whl'), 'authored replacement')
 $reader=Open-VerifiedArtifact $g 'asset.whl' '{sha}'
 $reader.Dispose()
}} finally {{ $g.Dispose() }}
"""
    )
    assert result.returncode != 0
    assert "digest" in result.stderr.lower()


@NATIVE
def test_native_missing_owned_primary_launcher_can_be_repaired(tmp_path):
    selection = selection_module()
    home = tmp_path / "home"
    (home / "bin").mkdir(parents=True)
    first = engine_fixture(tmp_path, "one")
    second = engine_fixture(tmp_path, "two")
    selection.select(home, first, "source", False)
    (home / "bin/ai-dlc.exe").unlink()
    result = selection.select(home, second, "source", False)
    assert result["published"]
    assert result["selected"]["source_root"] == str(tmp_path / "checkout-two")
    assert (home / "bin/ai-dlc.exe").is_file()


@NATIVE
def test_native_missing_companion_repairs_without_repointing_working_primary(tmp_path):
    selection = selection_module()
    home = tmp_path / "home"
    (home / "bin").mkdir(parents=True)
    first = engine_fixture(tmp_path, "one")
    second = engine_fixture(tmp_path, "two")
    selection.select(home, first, "source", False)
    (home / "bin/ai-dlc-cli.exe").unlink()
    result = selection.select(home, second, "source", False)
    assert not result["published"]
    assert result["selected"]["source_root"] == str(tmp_path / "checkout-one")
    assert (home / "bin/ai-dlc-cli.exe").read_bytes() == (home / "bin/ai-dlc.exe").read_bytes()


@NATIVE
def test_native_source_provenance_changes_for_docs_only_commit(tmp_path):
    def git(*arguments):
        return subprocess.run(
            ["git.exe", "-C", str(tmp_path), *arguments], capture_output=True, text=True, check=True
        ).stdout.strip()

    git("init", "-q")
    git("config", "user.name", "Bootstrap fixture")
    git("config", "user.email", "bootstrap-fixture@example.invalid")
    (tmp_path / "README.md").write_text("first\n")
    git("add", "README.md")
    git("commit", "-qm", "first")
    first = ps(helpers() + f"Get-SourceProvenance {quoted(tmp_path)}")
    assert first.returncode == 0, first.stderr
    assert first.stdout.strip() == git("rev-parse", "HEAD")
    (tmp_path / "README.md").write_text("docs only update\n")
    dirty = ps(helpers() + f"Get-SourceProvenance {quoted(tmp_path)}")
    assert dirty.returncode == 0, dirty.stderr
    assert "dirty:" in dirty.stdout and dirty.stdout != first.stdout
    git("add", "README.md")
    git("commit", "-qm", "docs update")
    second = ps(helpers() + f"Get-SourceProvenance {quoted(tmp_path)}")
    assert second.returncode == 0, second.stderr
    assert second.stdout.strip() == git("rev-parse", "HEAD")
    assert second.stdout != first.stdout and "dirty:" not in second.stdout


@NATIVE
def test_native_architecture_detection_ignores_process_environment_spoof(tmp_path):
    env = dict(
        os.environ,
        PROCESSOR_ARCHITECTURE="ARM64",
        PROCESSOR_ARCHITEW6432="ARM64",
        AI_DLC_BOOTSTRAP_HOME=str(tmp_path / "absent"),
    )
    result = ps(
        f"& {quoted(ROOT / 'scripts/bootstrap.ps1')} -Source -Plan -Root {quoted(ROOT)}", env=env
    )
    assert result.returncode == 0, result.stderr
    assert "Windows-x64" in result.stdout
    assert not (tmp_path / "absent").exists()


@NATIVE
def test_native_execution_sentinel_blocks_empty_directory_junction_attack(tmp_path):
    import ctypes as c
    import struct
    import sys
    from ctypes import wintypes as w

    from ai_dlc._windows_storage import opened

    outside = tmp_path / "outside"
    outside.mkdir()
    control = tmp_path / "control"
    control.mkdir()
    installed = tmp_path / "installed"
    substitute = ("\\??\\" + str(outside)).encode("utf-16-le")
    display = str(outside).encode("utf-16-le")
    paths = substitute + b"\0\0" + display + b"\0\0"
    data = (
        struct.pack(
            "<IHHHHHH",
            0xA0000003,
            8 + len(paths),
            0,
            0,
            len(substitute),
            len(substitute) + 2,
            len(display),
        )
        + paths
    )
    ioctl = c.WinDLL("kernel32", use_last_error=True).DeviceIoControl  # pyright: ignore[reportAttributeAccessIssue]
    ioctl.argtypes = [
        w.HANDLE,
        w.DWORD,
        c.c_void_p,
        w.DWORD,
        c.c_void_p,
        w.DWORD,
        c.POINTER(w.DWORD),
        c.c_void_p,
    ]
    ioctl.restype = w.BOOL

    def attack(path):
        with opened(path, access=0x100, share=7) as handle:
            count = w.DWORD()
            applied = bool(ioctl(handle, 0x900A4, data, len(data), None, 0, c.byref(count), None))
            return applied, c.get_last_error()  # pyright: ignore[reportAttributeAccessIssue]

    applied, code = attack(control)
    assert applied, f"Positive-control junction attack did not run: {code}"
    control.rmdir()
    script = (
        helpers()
        + f"""
Initialize-NativeStorage
$g=[AiDlc.Bootstrap.DirectoryGuard]::new({quoted(installed)}, $true, $true)
$reader=$g.ProtectForExecution()
try {{
 [Console]::WriteLine('ready')
 [Console]::ReadLine() | Out-Null
 & {quoted(sys.executable)} -c "import pathlib,sys; pathlib.Path(sys.argv[1]).write_text('inside')" (Join-Path $g.PathName 'result')
 if($LASTEXITCODE -ne 0) {{ throw 'external writer failed' }}
}} finally {{ $reader.Dispose(); $g.Dispose() }}
"""
    )
    process = subprocess.Popen(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert process.stdout and process.stdin
        assert process.stdout.readline().strip() == "ready"
        applied, code = attack(installed)
        assert not applied and code == 145, (
            f"Expected nonempty-directory refusal, got {applied}, {code}"
        )
        process.stdin.write("\n")
        process.stdin.flush()
        output, error = process.communicate(timeout=30)
        assert process.returncode == 0, output + error
        assert (installed / "result").read_text() == "inside"
        assert not list(outside.iterdir())
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


@NATIVE
def test_native_runtime_owner_acceptance_does_not_relax_private_metadata_or_dacl(tmp_path):
    import ctypes

    shell = ctypes.WinDLL("shell32")  # pyright: ignore[reportAttributeAccessIssue]
    if not shell.IsUserAnAdmin():
        pytest.skip("Admin-owned installer-output fixture requires an administrator token")
    result = ps(
        helpers()
        + f"""
Initialize-NativeStorage
$path={quoted(tmp_path / "runtime")}
$original=[AiDlc.Bootstrap.DirectoryGuard]::new($path, $true, $true)
$original.Dispose()
$acl=Get-Acl -LiteralPath $path
$acl.SetOwner([Security.Principal.SecurityIdentifier]::new('S-1-5-32-544'))
Set-Acl -LiteralPath $path -AclObject $acl
$runtime=[AiDlc.Bootstrap.DirectoryGuard]::OpenRuntimeDirectory($path)
$runtime.Dispose()
try {{
 $metadata=[AiDlc.Bootstrap.DirectoryGuard]::new($path, $false, $true)
 $metadata.Dispose()
 throw 'private metadata accepted a different owner'
}} catch {{
 if($_.Exception.Message -notlike '*Unsafe bootstrap namespace owner: S-1-5-32-544*') {{ throw }}
 Write-Output 'private-metadata-owner-refused'
}}
$acl=Get-Acl -LiteralPath $path
$acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new('Everyone','Read','ContainerInherit,ObjectInherit','None','Allow'))
Set-Acl -LiteralPath $path -AclObject $acl
try {{
 $unsafe=[AiDlc.Bootstrap.DirectoryGuard]::OpenRuntimeDirectory($path)
 $unsafe.Dispose()
 throw 'runtime accepted broad DACL'
}} catch {{
 if($_.Exception.Message -notlike '*Unsafe bootstrap namespace DACL: S-1-1-0*') {{ throw }}
 Write-Output 'broad-runtime-dacl-refused'
}}
Write-Output 'runtime-boundaries-verified'
"""
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        "private-metadata-owner-refused",
        "broad-runtime-dacl-refused",
        "runtime-boundaries-verified",
    ]
