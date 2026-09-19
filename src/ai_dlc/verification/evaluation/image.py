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


def _run(args, *, cwd=None, timeout=None):
    return subprocess.run(
        args, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False
    )


def _must(args, what: str, **options):
    done = _run(args, **options)
    if done.returncode:
        raise RuntimeError(f"{what} failed: {done.stderr.strip()}")
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


def resolve_profile(profile: dict, built: dict) -> dict:
    """A copy of the profile bound to this build; the original file is never edited."""
    resolved = copy.deepcopy(profile)
    resolved["image"] = built["base"]
    resolved["engine"] = built["engine"]
    return resolved
