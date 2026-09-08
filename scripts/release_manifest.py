"""Prepare an unpublished, hash-bound bootstrap manifest from candidate assets."""

import argparse
import hashlib
import io
import re
import shlex
import sys
import zipfile
from email.parser import BytesParser
from pathlib import Path
from urllib.parse import urlsplit


def manifest(artifacts: Path, base_url: str, version: str) -> str:
    parsed = urlsplit(base_url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or not re.fullmatch(r"[A-Za-z0-9:/._~%+-]+", base_url)
    ):
        raise ValueError("an explicit HTTPS artifact base URL without credentials is required")
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)*(?:(?:a|b|rc)[0-9]+)?", version):
        raise ValueError("invalid engine version")
    wheels = list(artifacts.glob("*.whl"))
    if len(wheels) != 1:
        raise ValueError("exactly one engine wheel is required")
    wheel = wheels[0]
    if wheel.is_symlink() or not wheel.is_file():
        raise ValueError("wheel must be a regular artifact")
    if wheel.name != f"ai_dlc-{version}-py3-none-any.whl":
        raise ValueError("wheel filename does not match the requested engine version")
    wheel_bytes = wheel.read_bytes()
    with zipfile.ZipFile(io.BytesIO(wheel_bytes)) as archive:
        metadata_names = [
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        ]
        if metadata_names != [f"ai_dlc-{version}.dist-info/METADATA"]:
            raise ValueError("wheel metadata identity is ambiguous")
        metadata = BytesParser().parsebytes(archive.read(metadata_names[0]))
        if metadata.get_all("Name") != ["ai-dlc"] or metadata.get_all("Version") != [version]:
            raise ValueError("wheel metadata identity/version mismatch")
    constraints = artifacts / "requirements.txt"
    if constraints.is_symlink() or not constraints.is_file() or not constraints.stat().st_size:
        raise ValueError("nonempty regular requirements.txt is required")
    base = base_url.rstrip("/")
    values = {
        "AI_DLC_ENGINE_VERSION": version,
        "AI_DLC_WHEEL_NAME": wheel.name,
        "AI_DLC_WHEEL_URL": base + "/" + wheel.name,
        "AI_DLC_WHEEL_SHA256": hashlib.sha256(wheel_bytes).hexdigest(),
        "AI_DLC_CONSTRAINTS_URL": base + "/requirements.txt",
        "AI_DLC_CONSTRAINTS_SHA256": hashlib.sha256(constraints.read_bytes()).hexdigest(),
    }
    return (
        "# Unpublished release candidate; verify and publish exact assets separately.\n"
        + "".join(f"{key}={shlex.quote(value)}\n" for key, value in values.items())
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        content = manifest(args.artifacts, args.base_url, args.version)
        with args.output.open("x") as output:
            output.write(content)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"Candidate manifest: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
