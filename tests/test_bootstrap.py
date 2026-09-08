import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_bootstrap_plan_needs_no_python_or_mise():
    result = subprocess.run(
        ["sh", str(ROOT / "scripts/bootstrap.sh"), "--source", "--plan"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "mode=source" in result.stdout
    assert "github.com/astral-sh/uv/releases/download/0.9.11" in result.stdout


def test_digest_mismatch_never_installs_download(tmp_path):
    fakebin = tmp_path / "bin"
    fakebin.mkdir()
    curl = fakebin / "curl"
    curl.write_text(
        '#!/bin/sh\nfor arg do previous=$last; last=$arg; done\nprintf tampered > "$last"\n'
    )
    curl.chmod(0o755)
    destination = tmp_path / "download"
    script = '. "$1"; ai_dlc_download https://example.test/file "$2" "$3"'
    result = subprocess.run(
        [
            "sh",
            "-c",
            script,
            "sh",
            str(ROOT / "bootstrap/download.sh"),
            hashlib.sha256(b"expected").hexdigest(),
            str(destination),
        ],
        env={**os.environ, "PATH": str(fakebin) + ":" + os.environ["PATH"]},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "digest mismatch" in result.stderr
    assert not destination.exists()


def test_devcontainer_keeps_linux_environment_off_the_host_checkout():
    config = json.loads((ROOT / ".devcontainer/devcontainer.json").read_text())

    assert (
        "source=${devcontainerId}-venv,target=${containerWorkspaceFolder}/.venv,type=volume"
        in config["mounts"]
    )
    assert config["postCreateCommand"].startswith("sudo chown -R vscode:vscode .venv && ")


def _executable(path, body):
    path.write_text(body)
    path.chmod(0o755)


def _bootstrap_fixture(tmp_path):
    """Real bootstrap with pinned local tool fixtures, no package/network operations."""
    import io
    import shutil
    import sys
    import tarfile

    project = tmp_path / "project"
    (project / "bootstrap").mkdir(parents=True)
    shutil.copy(ROOT / "bootstrap/download.sh", project / "bootstrap/download.sh")
    home = tmp_path / "bootstrap-home"
    downloads = home / "downloads"
    downloads.mkdir(parents=True)
    installed = home / "bin"
    installed.mkdir()
    uv = (
        f"#!{sys.executable}\n"
        "import os, pathlib, sys\n"
        "if sys.argv[1:3] == ['python', 'find']: print(sys.executable)\n"
        "if sys.argv[1:2] == ['sync']:\n"
        " p = pathlib.Path(os.environ['UV_PROJECT_ENVIRONMENT']) / 'bin'\n"
        " p.mkdir(parents=True, exist_ok=True)\n"
        " cli = p / 'ai-dlc'\n"
        " cli.write_text('#!/bin/sh\\nexit 0\\n')\n"
        " cli.chmod(0o755)\n"
    ).encode()
    contents = {"uv": uv, "uvx": b"#!/bin/sh\nexit 0\n", "mise": b"#!/bin/sh\nexit 0\n"}
    archive = downloads / "uv-fixture-fixture.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        for name in ("uv", "uvx"):
            entry = tarfile.TarInfo("uv-fixture/" + name)
            entry.size = len(contents[name])
            entry.mode = 0o755
            bundle.addfile(entry, io.BytesIO(contents[name]))
    (downloads / "mise-fixture-fixture").write_bytes(contents["mise"])
    (project / "bootstrap/versions.sh").write_text(
        "AI_DLC_UV_VERSION=fixture\nAI_DLC_UV_TARGET=fixture\n"
        "AI_DLC_UV_URL=https://example.test/uv\n"
        f"AI_DLC_UV_SHA256={hashlib.sha256(archive.read_bytes()).hexdigest()}\n"
        "AI_DLC_PYTHON_VERSION=fixture\nAI_DLC_ENGINE_VERSION=fixture\n"
        "AI_DLC_MISE_VERSION=fixture\nAI_DLC_MISE_TARGET=fixture\n"
        "AI_DLC_MISE_URL=https://example.test/mise\n"
        f"AI_DLC_MISE_SHA256={hashlib.sha256(contents['mise']).hexdigest()}\n"
    )
    fakebin = tmp_path / "fakebin"
    fakebin.mkdir()
    _executable(fakebin / "curl", "#!/bin/sh\necho unexpected-network >&2\nexit 91\n")
    environment = {
        **os.environ,
        "AI_DLC_BOOTSTRAP_HOME": str(home),
        "PATH": str(fakebin) + ":" + os.environ["PATH"],
    }
    command = ["sh", str(ROOT / "scripts/bootstrap.sh"), "--source", "--root", str(project)]
    return command, environment, installed, contents, fakebin


@pytest.mark.parametrize("tool", ["uv", "uvx", "mise"])
def test_real_bootstrap_publication_preserves_open_previous_executables(tmp_path, tool):
    """Would fail when real-script cp mutates an executable retained by an old reader."""
    import contextlib
    import stat

    command, environment, installed, contents, _ = _bootstrap_fixture(tmp_path)
    with contextlib.ExitStack() as opened:
        previous = {}
        for name in contents:
            path = installed / name
            _executable(path, "#!/bin/sh\n# previous " + name + "\nexit 77\n")
            previous[name] = (opened.enter_context(path.open("rb")), path.read_bytes())
        result = subprocess.run(
            command, env=environment, capture_output=True, text=True, check=False, timeout=15
        )
        assert result.returncode == 0, result.stderr
        for name, expected in contents.items():
            path = installed / name
            held, old_bytes = previous[name]
            assert path.read_bytes() == expected
            assert stat.S_IMODE(path.stat().st_mode) == 0o755
            if name == tool:
                assert held.read() == old_bytes, f"{name}: old executable reader observed mutation"
                assert os.fstat(held.fileno()).st_ino != path.stat().st_ino


def _await_path(path):
    import time

    deadline = time.monotonic() + 8
    while not path.exists():
        if time.monotonic() > deadline:
            raise AssertionError(f"process did not reach barrier {path.name}")
        time.sleep(0.01)


def test_overlapping_downloads_verify_independent_staging(tmp_path):
    """Two real helper processes must not hash the other download's shared partial file."""
    import sys

    fakebin = tmp_path / "bin"
    fakebin.mkdir()
    _executable(
        fakebin / "curl",
        f"#!{sys.executable}\n"
        "import os, pathlib, sys, time\n"
        "root = pathlib.Path(os.environ['BARRIER_ROOT'])\n"
        "name = os.environ['DOWNLOAD_NAME']\n"
        "output = pathlib.Path(sys.argv[sys.argv.index('--output') + 1])\n"
        "output.write_text(name)\n"
        "(root / (name + '.ready')).write_text(str(output))\n"
        "deadline = time.monotonic() + 10\n"
        "while not (root / (name + '.release')).exists():\n"
        " if time.monotonic() > deadline: sys.exit(90)\n"
        " time.sleep(0.01)\n",
    )
    destination = tmp_path / "download"
    command = [
        "sh",
        "-c",
        '. "$1"; ai_dlc_download https://example.test/file "$2" "$3"',
        "sh",
        str(ROOT / "bootstrap/download.sh"),
    ]
    processes = []
    try:
        for name in ("first", "second"):
            processes.append(
                subprocess.Popen(
                    [*command, hashlib.sha256(name.encode()).hexdigest(), str(destination)],
                    env={
                        **os.environ,
                        "PATH": str(fakebin) + ":" + os.environ["PATH"],
                        "BARRIER_ROOT": str(tmp_path),
                        "DOWNLOAD_NAME": name,
                    },
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
            )
            _await_path(tmp_path / (name + ".ready"))
        (tmp_path / "first.release").touch()
        first_output = processes[0].communicate(timeout=12)
        (tmp_path / "second.release").touch()
        second_output = processes[1].communicate(timeout=12)
        assert processes[0].returncode == 0, first_output
        assert processes[1].returncode == 0, second_output
        assert destination.read_bytes() == b"second"
        assert (tmp_path / "first.ready").read_text() != (tmp_path / "second.ready").read_text()
    finally:
        for name in ("first", "second"):
            (tmp_path / (name + ".release")).touch()
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)


@pytest.mark.parametrize("operation,tool", [("cp", "mise"), ("chmod", "uv"), ("mv", "uv")])
def test_bootstrap_publication_failure_preserves_installed_executable(tmp_path, operation, tool):
    import shutil
    import sys

    command, environment, installed, _, fakebin = _bootstrap_fixture(tmp_path)
    path = installed / tool
    _executable(path, "#!/bin/sh\n# previously installed\nexit 77\n")
    before = path.read_bytes(), path.stat().st_ino, path.stat().st_mode
    real = shutil.which(operation)
    assert real is not None
    _executable(
        fakebin / operation,
        f"#!{sys.executable}\n"
        "import os, pathlib, sys\n"
        f"operation = {operation!r}\n"
        "args = sys.argv[1:]\n"
        "target = pathlib.Path(args[-1])\n"
        "fail = (operation == 'cp' and pathlib.Path(args[-2]).name.startswith('mise-')) or "
        "(operation == 'chmod' and target.name == 'uv') or "
        "(operation == 'mv' and pathlib.Path(args[-2]).name == 'uv')\n"
        "if fail:\n"
        " if operation == 'cp': target.write_bytes(b'partial staging bytes')\n"
        " sys.exit(75)\n"
        f"os.execv({real!r}, [{real!r}, *args])\n",
    )
    result = subprocess.run(
        command, env=environment, capture_output=True, text=True, check=False, timeout=15
    )
    assert result.returncode != 0
    assert (path.read_bytes(), path.stat().st_ino, path.stat().st_mode) == before
    stage = next(installed.glob(".install.*"))
    assert str(stage) in result.stderr
    assert stage.is_dir()


def test_failed_extraction_retains_replaced_stage_occupant(tmp_path):
    import shutil
    import sys

    command, environment, installed, _, fakebin = _bootstrap_fixture(tmp_path)
    real_tar = shutil.which("tar")
    displaced = tmp_path / "displaced-extraction"
    _executable(
        fakebin / "tar",
        f"#!{sys.executable}\n"
        "import pathlib, subprocess, sys\n"
        f"subprocess.run([{real_tar!r}, *sys.argv[1:]], check=True)\n"
        "stage = pathlib.Path(sys.argv[sys.argv.index('-C') + 1])\n"
        f"stage.rename({str(displaced)!r})\n"
        "stage.mkdir()\n"
        "(stage / 'authored.md').write_bytes(b'authored replacement')\n"
        "sys.exit(75)\n",
    )
    result = subprocess.run(
        command, env=environment, capture_output=True, text=True, check=False, timeout=15
    )
    assert result.returncode != 0
    authored = list(installed.parent.rglob("authored.md"))
    assert len(authored) == 1
    assert authored[0].read_bytes() == b"authored replacement"
    assert str(authored[0].parent) in result.stderr
    assert (displaced / "uv-fixture/uv").is_file()


@pytest.mark.parametrize("kind", ["directory", "symlink"])
def test_bootstrap_refuses_unexpected_executable_destination(tmp_path, kind):
    command, environment, installed, _, _ = _bootstrap_fixture(tmp_path)
    target = installed / "uv"
    authored = tmp_path / "authored-target"
    authored.mkdir()
    (authored / "keep.md").write_bytes(b"authored")
    if kind == "directory":
        target.mkdir()
    else:
        target.symlink_to(authored, target_is_directory=True)
    result = subprocess.run(
        command, env=environment, capture_output=True, text=True, check=False, timeout=15
    )
    assert result.returncode != 0
    assert list(authored.iterdir()) == [authored / "keep.md"]
    assert (authored / "keep.md").read_bytes() == b"authored"
    assert target.is_symlink() if kind == "symlink" else target.is_dir()


def test_failed_download_retains_replacement_and_previous_cache(tmp_path):
    import sys

    fakebin = tmp_path / "bin"
    fakebin.mkdir()
    _executable(
        fakebin / "curl",
        f"#!{sys.executable}\n"
        "import pathlib, sys\n"
        "path = pathlib.Path(sys.argv[sys.argv.index('--output') + 1])\n"
        "path.write_bytes(b'partial download')\n"
        "path.rename(path.with_name('displaced-partial'))\n"
        "path.mkdir()\n"
        "(path / 'authored.md').write_bytes(b'authored replacement')\n"
        "sys.exit(75)\n",
    )
    destination = tmp_path / "download"
    destination.write_bytes(b"previous verified cache")
    before = destination.stat().st_ino
    result = subprocess.run(
        [
            "sh",
            "-c",
            '. "$1"; ai_dlc_download https://example.test/file "$2" "$3"',
            "sh",
            str(ROOT / "bootstrap/download.sh"),
            hashlib.sha256(b"expected").hexdigest(),
            str(destination),
        ],
        env={**os.environ, "PATH": str(fakebin) + ":" + os.environ["PATH"]},
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert result.returncode != 0
    assert destination.read_bytes() == b"previous verified cache"
    assert destination.stat().st_ino == before
    authored = next(tmp_path.glob("download.partial*/authored.md"))
    assert authored.read_bytes() == b"authored replacement"
    assert str(authored.parent) in result.stderr


def test_overlapping_bootstraps_publish_from_distinct_stages(tmp_path):
    import shutil
    import sys

    command, environment, installed, contents, fakebin = _bootstrap_fixture(tmp_path)
    second_project = tmp_path / "second-project"
    shutil.copytree(tmp_path / "project", second_project)
    # Global CLI alias last-writer behavior is outside executable publication.
    _executable(fakebin / "ln", "#!/bin/sh\nexit 0\n")
    real_mv = shutil.which("mv")
    _executable(
        fakebin / "mv",
        f"#!{sys.executable}\n"
        "import os, pathlib, sys, time\n"
        "source = pathlib.Path(sys.argv[-2])\n"
        "if source.name == 'uv':\n"
        " root = pathlib.Path(os.environ['BARRIER_ROOT'])\n"
        " name = os.environ['BOOTSTRAP_NAME']\n"
        " (root / (name + '.ready')).write_text(str(source))\n"
        " deadline = time.monotonic() + 10\n"
        " while not (root / 'release').exists():\n"
        "  if time.monotonic() > deadline: sys.exit(90)\n"
        "  time.sleep(0.01)\n"
        f"os.execv({real_mv!r}, [{real_mv!r}, *sys.argv[1:]])\n",
    )
    _executable(installed / "uv", "#!/bin/sh\n# previous reader\nexit 77\n")
    old_bytes = (installed / "uv").read_bytes()
    processes = []
    with (installed / "uv").open("rb") as held:
        try:
            for name, root in (("first", tmp_path / "project"), ("second", second_project)):
                processes.append(
                    subprocess.Popen(
                        [*command[:-1], str(root)],
                        env={**environment, "BARRIER_ROOT": str(tmp_path), "BOOTSTRAP_NAME": name},
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                    )
                )
                _await_path(tmp_path / (name + ".ready"))
            first_stage = Path((tmp_path / "first.ready").read_text())
            second_stage = Path((tmp_path / "second.ready").read_text())
            assert first_stage != second_stage
            assert first_stage.is_relative_to(installed)
            assert second_stage.is_relative_to(installed)
            (tmp_path / "release").touch()
            for process in processes:
                output = process.communicate(timeout=15)
                assert process.returncode == 0, output
            assert held.read() == old_bytes
            for name, expected in contents.items():
                assert (installed / name).read_bytes() == expected
            assert first_stage.parent.is_dir() and second_stage.parent.is_dir()
        finally:
            (tmp_path / "release").touch()
            for process in processes:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=5)
