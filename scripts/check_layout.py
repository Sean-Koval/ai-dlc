"""Check AI-DLC's own layout; does not impose this source tree on adopted projects."""

import argparse
from pathlib import Path

ROOT_MARKDOWN = {
    "README.md",
    "CONTRIBUTING.md",
    "AGENTS.md",
    "CLAUDE.md",
    "LICENSE.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
}
ROOT_MODULES = {
    "__init__.py",
    "__main__.py",
    "cli.py",
    "mcp_server.py",
    "conformance.py",
    "config.py",
    "contracts.py",
    "files.py",
    "locking.py",
    "provider_definitions.py",
}
DOC_ENTRY_POINTS = {
    "index.md",
    "product-direction.md",
    "roadmap.md",
    "architecture.md",
    "release-verification.md",
    "github-ticket-setup.md",
    "migration.md",
    "development-workflow.md",
}


def findings(root: Path) -> list[str]:
    errors = []
    for path in sorted(root.glob("*.md")):
        if path.name not in ROOT_MARKDOWN:
            errors.append(
                f"{path.name}: put formal change artifacts in openspec/changes and durable guidance in docs/."
            )
    for path in sorted((root / "src/ai_dlc").glob("*.py")):
        if path.name not in ROOT_MODULES:
            errors.append(
                f"{path.relative_to(root)}: use the responsible application subpackage; update the architecture map for a new boundary."
            )
    for path in sorted((root / "docs").glob("*.md")):
        if path.name not in DOC_ENTRY_POINTS:
            errors.append(
                f"{path.relative_to(root)}: use design/, runbooks/, workflows/, verification/ or archive/ and link the document from the index/catalog."
            )
    for relative in [".superpowers", "docs/superpowers"]:
        if (root / relative).exists() or (root / relative).is_symlink():
            errors.append(
                f"{relative}: keep temporary execution artifacts in ignored .ai-dlc/local/; formal work belongs in OpenSpec."
            )
    claude = root / "CLAUDE.md"
    if (claude.exists() or claude.is_symlink()) and (
        claude.is_symlink() or claude.read_bytes() != b"@AGENTS.md\n"
    ):
        errors.append(
            "CLAUDE.md: repository context belongs in AGENTS.md; keep only @AGENTS.md followed by a newline."
        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    errors = findings(args.root)
    print("\n".join(errors) if errors else "Repository layout passed")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
