"""Pure work dependency validation and first-publication presentation."""

import re
from pathlib import PurePosixPath, PureWindowsPath
from urllib.parse import urlsplit

WORK_ID = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,99}")


_PROVIDER_ARTIFACTS = {"tracker", "pr", "branch", "deployment", "knowledge"}
_DOCUMENT_SUFFIXES = {".md", ".markdown", ".rst", ".txt", ".json", ".toml", ".yaml", ".yml", ".pdf"}


def artifact_is_local(kind: str, reference: str, *, existing_path: bool = False) -> bool:
    """Classify document ownership, without interpreting a specification provider's IDs.

    Spec IDs (including slash IDs and provider URIs) belong to their provider.
    Filesystem notation, document suffixes and already existing repository paths
    explicitly identify local spec artifacts. Ambiguous bare directories use ./.
    """
    if kind in _PROVIDER_ARTIFACTS:
        return False
    if PureWindowsPath(reference).drive:
        return True
    parsed = urlsplit(reference)
    if parsed.scheme == "file":
        return True  # Filesystem URIs are reserved; the caller rejects unsupported notation.
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return False
    if kind != "spec":
        return True
    if reference.startswith(("./", "../", "/", "\\")):
        return True
    if parsed.scheme:
        return False
    return existing_path or PurePosixPath(parsed.path).suffix.lower() in _DOCUMENT_SUFFIXES


def validate_work_graph(records: dict[str, dict]) -> list[str]:
    """Return deterministic graph errors without inspecting files or provider state."""
    errors = []
    graph: dict[str, list[str]] = {}
    for key in sorted(records):
        if not WORK_ID.fullmatch(key):
            errors.append(f"Unsafe work ID: {key!r}")
            continue
        record = records[key]
        if record.get("id") != key:
            errors.append(f"Work {key}: id does not match its record key")
        dependencies = record.get("depends_on", [])
        if not isinstance(dependencies, list):
            errors.append(f"Work {key}: depends_on must be a list")
            continue
        graph[key] = []
        for dependency in dependencies:
            if not isinstance(dependency, str) or not WORK_ID.fullmatch(dependency):
                errors.append(f"Work {key}: Unsafe dependency ID {dependency!r}")
            elif dependency == key:
                errors.append(f"Work {key}: self dependency cycle")
            elif dependency not in records:
                errors.append(f"Work {key}: missing dependency {dependency}")
            elif dependency not in graph[key]:
                graph[key].append(dependency)
        graph[key].sort()

    # Iterative DFS keeps large, valid chains independent of Python's recursion limit.
    done: set[str] = set()
    for root in sorted(graph):
        if root in done:
            continue
        path = [root]
        active = {root: 0}
        stack = [iter(graph[root])]
        while stack:
            dependency = next(stack[-1], None)
            if dependency is None:
                finished = path.pop()
                done.add(finished)
                active.pop(finished)
                stack.pop()
            elif dependency in active:
                cycle = path[active[dependency] :] + [dependency]
                errors.append("Dependency cycle: " + " -> ".join(cycle))
            elif dependency not in done and dependency in graph:
                active[dependency] = len(path)
                path.append(dependency)
                stack.append(iter(graph[dependency]))
    return sorted(set(errors))


def render_ticket_body(work: dict) -> str:
    """Render supplied intent and references; the caller retains correlation ownership."""
    sections = ["## Scope", "", work["scope"], "", "## Requirements", ""]
    sections.extend(f"- {item}" for item in work.get("requirements", []))
    if not work.get("requirements"):
        sections.append("None recorded.")
    sections.extend(["", "## Dependencies", ""])
    sections.extend(f"- {item}" for item in work.get("depends_on", []))
    if not work.get("depends_on"):
        sections.append("None.")
    sections.extend(["", "## References", ""])
    sections.extend(
        f"- {kind}: {reference}" for kind, reference in sorted(work.get("artifacts", {}).items())
    )
    if not work.get("artifacts"):
        sections.append("None recorded.")
    sections.extend(
        [
            "",
            "## Specification decision",
            "",
            f"Required: {'yes' if work.get('requires_spec') else 'no'}. {work.get('spec_reason', '')}",
            "",
            "## Acceptance",
            "",
        ]
    )
    sections.extend(f"- {item}" for item in work.get("acceptance", []))
    return "\n".join(sections).rstrip() + "\n"
