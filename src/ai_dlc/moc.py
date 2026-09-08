"""5-pillar documentation scaffolding and Map of Content (MOC) generator."""

from pathlib import Path


def scaffold_5_pillar_docs(docs_root: Path, project_name: str) -> list[str]:
    """Scaffold the 5-pillar documentation hierarchy in a non-destructive manner."""
    docs_root = Path(docs_root).resolve()
    docs_root.mkdir(parents=True, exist_ok=True)
    created: list[str] = []

    pillars = ["architecture", "adr", "specs", "runbooks", "reference"]
    for pillar in pillars:
        (docs_root / pillar).mkdir(parents=True, exist_ok=True)

    # 1. Map of Content (index.md)
    index_file = docs_root / "index.md"
    if not index_file.exists():
        index_content = f"""# {project_name} Documentation

> Knowledge base and architectural documentation for **{project_name}**.

```mermaid
graph TD
    MOC["docs/index.md (Map of Content)"] --> ARCH["Architecture<br/>• System Design<br/>• Component Boundaries"]
    MOC --> ADR["ADRs<br/>• Architecture Decisions<br/>• Trade-off Records"]
    MOC --> SPEC["Specs<br/>• Product Requirements<br/>• Delta Specifications"]
    MOC --> RUN["Runbooks<br/>• Operations & Dev<br/>• Deployment & Triage"]
    MOC --> REF["Reference<br/>• API Contracts<br/>• Data Models & Enums"]
```

## Documentation Pillars

- [Architecture](architecture/system-design.md): System components, data flows, and design decisions.
- [Architecture Decision Records (ADRs)](adr/): Durable records of architectural choices.
- [Specifications](specs/README.md): Requirements, feature specifications, and contracts.
- [Runbooks](runbooks/README.md): Operational workflows, local setup, and debugging guides.
- [Reference](reference/README.md): Data schemas, configuration, and API references.
"""
        index_file.write_text(index_content, encoding="utf-8")
        created.append(str(index_file.relative_to(docs_root)))

    # 2. Architecture starter
    arch_file = docs_root / "architecture" / "system-design.md"
    if not arch_file.exists():
        arch_content = f"""# System Design: {project_name}

## High-Level Architecture

System architecture and component boundaries for `{project_name}`.

```mermaid
graph LR
    Client --> API
    API --> CoreService
```

## Core Components
- `Client`: Consumer interface or agent harness.
- `API`: Communication contracts.
- `CoreService`: Business logic and persistence.
"""
        arch_file.write_text(arch_content, encoding="utf-8")
        created.append(str(arch_file.relative_to(docs_root)))

    # 3. ADR template
    adr_template = docs_root / "adr" / "0000-template.md"
    if not adr_template.exists():
        adr_content = """# ADR-0000: Title

- **Status**: Proposed | Accepted | Deprecated | Superseded
- **Date**: YYYY-MM-DD
- **Deciders**:

## Context and Problem Statement

What is the context and why is a decision required?

## Considered Options

1. Option 1
2. Option 2

## Decision Outcome

Chosen option: "Option 1" because ...

### Positive Consequences
- ...

### Negative Consequences
- ...
"""
        adr_template.write_text(adr_content, encoding="utf-8")
        created.append(str(adr_template.relative_to(docs_root)))

    # 4. Specs README
    specs_readme = docs_root / "specs" / "README.md"
    if not specs_readme.exists():
        specs_readme.write_text(
            f"# Specifications: {project_name}\n\nFeature specifications and behavioral contracts.\n",
            encoding="utf-8",
        )
        created.append(str(specs_readme.relative_to(docs_root)))

    # 5. Runbooks README
    runbooks_readme = docs_root / "runbooks" / "README.md"
    if not runbooks_readme.exists():
        runbooks_readme.write_text(
            f"# Runbooks: {project_name}\n\nOperational playbooks, triage procedures, and dev environment setups.\n",
            encoding="utf-8",
        )
        created.append(str(runbooks_readme.relative_to(docs_root)))

    # 6. Reference README
    ref_readme = docs_root / "reference" / "README.md"
    if not ref_readme.exists():
        ref_readme.write_text(
            f"# Reference: {project_name}\n\nData dictionaries, API schemas, and token guides.\n",
            encoding="utf-8",
        )
        created.append(str(ref_readme.relative_to(docs_root)))

    return created
