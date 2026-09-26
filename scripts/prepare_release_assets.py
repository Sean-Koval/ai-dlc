"""Assemble exact bootstrap assets and their digest inventory without publication."""

import argparse
import hashlib
from pathlib import Path

from release_manifest import manifest

BOOTSTRAP_ASSETS = (
    "scripts/bootstrap.sh",
    "bootstrap/versions.sh",
    "bootstrap/download.sh",
    "scripts/bootstrap.ps1",
    "bootstrap/windows.json",
    "bootstrap/windows.ps1",
    "bootstrap/windows-native.cs",
    "bootstrap/windows-select.py",
)


def prepare(artifacts: Path, source: Path, base_url: str, version: str) -> None:
    content = manifest(artifacts, base_url, version).encode()
    outputs = {"release.sh": content}
    for relative in BOOTSTRAP_ASSETS:
        asset = source / "project-templates/project" / relative
        if asset.is_symlink() or not asset.is_file():
            raise ValueError(f"Missing regular bootstrap asset: {relative}")
        outputs[asset.name] = asset.read_bytes()
    for name in (*outputs, "SHA256SUMS"):
        if (artifacts / name).exists() or (artifacts / name).is_symlink():
            raise ValueError(f"Refusing to replace artifact: {name}")
    inputs = list(artifacts.glob("ai_dlc-*.whl")) + list(artifacts.glob("ai_dlc-*.tar.gz"))
    inputs.append(artifacts / "requirements.txt")
    for path in inputs:
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Artifact must be regular: {path.name}")
    digests = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs}
    digests.update({name: hashlib.sha256(body).hexdigest() for name, body in outputs.items()})
    for name, body in outputs.items():
        with (artifacts / name).open("xb") as output:
            output.write(body)
    with (artifacts / "SHA256SUMS").open("x", encoding="utf-8", newline="\n") as output:
        output.write("".join(f"{digest}  {name}\n" for name, digest in sorted(digests.items())))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    prepare(args.artifacts, args.source, args.base_url, args.version)


if __name__ == "__main__":
    main()
