"""Build the treatment arm's candidate image: the baseline image plus a verified engine.

This mirrors the release path (`uv build`, locked hash-pinned constraints, then the wheel
with no dependency resolution) inside `docker build`. It is an equivalent engine install,
not a run of `scripts/bootstrap.sh`: bootstrap's managed Python, uv and mise are absent,
and the base image's Python is used. The build needs a package index; attempts never do.
"""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import tempfile
import urllib.request
from pathlib import Path

from ai_dlc.verification.evaluation.attempt import PINNED
from ai_dlc.verification.evaluation.run import derived_from

DOCKERFILE = """FROM {base}
COPY requirements.txt {wheel} /opt/ai-dlc/
RUN python -m venv /opt/ai-dlc/engine \\
 && /opt/ai-dlc/engine/bin/pip install --no-cache-dir --require-hashes -r /opt/ai-dlc/requirements.txt \\
 && /opt/ai-dlc/engine/bin/pip install --no-cache-dir --no-deps /opt/ai-dlc/{wheel} \\
 && ln -s /opt/ai-dlc/engine/bin/ai-dlc /usr/local/bin/ai-dlc
"""


RELEASES = "https://downloads.claude.ai/claude-code-releases"
PLATFORMS = {"amd64": "linux-x64", "arm64": "linux-arm64"}
AGENT_CHECK = ["docker", "run", "--rm", "--network=none", "--cap-drop=ALL", "--user=1000:1000"]
# The controller downloads and verifies the client; the build itself downloads none.
# Plain COPY keeps the context file's mode, so this works without BuildKit.
BASE_DOCKERFILE = """FROM {parent}
RUN apt-get update \\
 && apt-get install -y --no-install-recommends {packages} \\
 && rm -rf /var/lib/apt/lists/*
COPY claude /usr/local/bin/claude
"""


def _fetch(url: str) -> bytes:
    if not url.startswith("https://"):
        raise ValueError("The client is fetched over https only")
    with urllib.request.urlopen(url, timeout=600) as response:
        return response.read()


def _run(args, *, cwd=None, timeout=None):
    return subprocess.run(
        args, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False
    )


def _must(args, what: str, **options):
    done = _run(args, **options)
    if done.returncode:
        tail = "\n".join(done.stderr.strip().splitlines()[-5:])
        raise RuntimeError(f"{what} failed: {tail}")
    return done


def _layers(image: str) -> list[str]:
    done = _must(
        ["docker", "image", "inspect", "--format", "{{json .RootFS.Layers}}", image],
        f"inspecting {image}",
        timeout=60,
    )
    return json.loads(done.stdout)


def build_candidate(root: Path, base: str) -> dict:
    """Return the built image, the wheel identity and the engine block a profile needs."""
    if not PINNED.fullmatch(base):
        raise ValueError("The baseline image must be pinned by digest")
    with tempfile.TemporaryDirectory(prefix="ai-dlc-candidate-") as folder:
        context = Path(folder)
        _must(
            ["uv", "build", "--wheel", "--out-dir", str(context)],
            "building the wheel",
            cwd=root,
            timeout=600,
        )
        _must(
            ["uv", "export", "--locked", "--no-dev", "--no-emit-project", "--format",
             "requirements-txt", "--output-file", str(context / "requirements.txt")],
            "exporting locked constraints", cwd=root, timeout=300,
        )  # fmt: skip
        wheels = sorted(context.glob("ai_dlc-*.whl"))
        if len(wheels) != 1:
            raise RuntimeError("Expected exactly one built ai_dlc wheel")
        wheel = wheels[0]
        for stray in context.iterdir():
            if stray not in (wheel, context / "requirements.txt"):
                stray.unlink()  # uv may leave a .gitignore; the context holds only what is installed
        (context / "Dockerfile").write_text(DOCKERFILE.format(base=base, wheel=wheel.name))
        digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
        built = _must(
            ["docker", "build", "-q", str(context)], "building the candidate image", timeout=1800
        )
        image = built.stdout.strip().splitlines()[-1]
    if not derived_from(_layers(image), _layers(base)):
        raise RuntimeError("The built image is not derived from the baseline image")
    smoke = _run(
        ["docker", "run", "--rm", "--network=none", "--cap-drop=ALL", image, "ai-dlc", "--version"],
        timeout=120,
    )
    if smoke.returncode:
        raise RuntimeError(f"The installed engine does not run in {image}: {smoke.stderr.strip()}")
    return {
        "base": base,
        "image": image,
        "engine": {"artifact": wheel.name, "sha256": digest, "image": image},
        "version": smoke.stdout.strip(),
    }


def build_base(recipe: object) -> dict:
    """Build the image both arms share and prove Git and the pinned client run offline.

    Distribution packages are not version-pinned; the result is identified by its image
    ID, and both arms use that same ID, so the arms cannot differ in them.
    """
    from ai_dlc.verification.evaluation.contracts import BaseImage
    from ai_dlc.verification.evaluation.planning import _validated

    declared = _validated(BaseImage, recipe, "base image")
    arch = _must(
        ["docker", "version", "--format", "{{.Server.Arch}}"], "reading the daemon", timeout=60
    ).stdout.strip()
    platform = PLATFORMS.get(arch)
    if platform is None or platform not in declared.client.sha256:
        raise ValueError(f"The base image recipe has no client sha256 for architecture {arch}")
    version = declared.client.version
    binary = _fetch(f"{RELEASES}/{version}/{platform}/claude")
    actual = hashlib.sha256(binary).hexdigest()
    if actual != declared.client.sha256[platform]:
        raise RuntimeError(f"The downloaded client's sha256 is {actual}, not the recipe's")
    with tempfile.TemporaryDirectory(prefix="ai-dlc-base-") as folder:
        context = Path(folder)
        (context / "claude").write_bytes(binary)
        (context / "claude").chmod(0o755)
        (context / "Dockerfile").write_text(
            BASE_DOCKERFILE.format(parent=declared.parent, packages=" ".join(declared.packages))
        )
        built = _must(["docker", "build", "-q", folder], "building the base image", timeout=1800)
    image = built.stdout.strip().splitlines()[-1]
    if not derived_from(_layers(image), _layers(declared.parent)):
        raise RuntimeError("The built image is not derived from its declared parent")
    git = _must([*AGENT_CHECK, image, "git", "--version"], "running git offline", timeout=120)
    client = _must(
        [*AGENT_CHECK, image, "claude", "--version"], "running the client offline", timeout=120
    )
    if client.stdout.split()[:1] != [version]:
        raise RuntimeError(f"The client reports {client.stdout.strip()!r}, not {version}")
    return {
        "image": image,
        "from": declared.parent,
        "client": {"kind": declared.client.kind, "version": version, "platform": platform},
        "git": git.stdout.strip(),
    }


def resolve_profile(profile: dict, built: dict) -> dict:
    """A copy of the profile bound to this build; the original file is never edited."""
    resolved = copy.deepcopy(profile)
    resolved["image"] = built["base"]
    resolved["engine"] = built["engine"]
    return resolved
