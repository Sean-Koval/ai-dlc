"""Compatibility scaffold outputs, with explicit conflict protection."""

from pathlib import Path

from ai_dlc.files import assets, inside


def scaffold(root: Path, providers: list[str], all_providers: bool = False) -> dict:
    source = assets("legacy")
    if all_providers:
        providers = sorted(p.name for p in source.iterdir() if p.is_dir())
    writes = []
    skipped = []
    for provider in providers:
        if provider not in {p.name for p in source.iterdir() if p.is_dir()}:
            skipped.append(provider)
            continue
        folder = source / provider / f".{provider}"
        if not folder.is_dir():
            folder = source / provider
        for file in sorted(folder.rglob("*")):
            if file.is_file():
                target = inside(root, str(Path(f".{provider}") / file.relative_to(folder)))
                if target.exists() and target.read_bytes() != file.read_bytes():
                    raise ValueError(f"scaffold conflict; existing content preserved: {target}")
                writes.append((file, target))
    for source_file, target in writes:
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_bytes(source_file.read_bytes())
    return {"files": len(writes), "skipped": skipped}
