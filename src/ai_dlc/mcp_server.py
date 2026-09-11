"""Local stdio MCP; no raw provider mutations or alternate completion path."""

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from ai_dlc.cli import config_for
from ai_dlc.work.workflow import WorkService


def make_server(root: Path, machine: Path | None = None) -> FastMCP:
    config = config_for(root, machine)

    def work():
        return WorkService.from_project(root, machine=machine)

    server = FastMCP("AI-DLC")

    @server.tool()
    def work_publish(work_id: str) -> dict:
        """Publish a reviewed work record to its bound tracker."""
        return work().publish(work_id)

    @server.tool()
    def work_start(work_id: str) -> dict:
        """Start reviewed work and bind its branch."""
        return work().start(work_id)

    @server.tool()
    def work_status(work_id: str) -> dict:
        """Read tracker-authoritative work status."""
        return work().status(work_id)

    @server.tool()
    def work_link(work_id: str, kind: str, reference: str) -> dict:
        """Link an artifact to reviewed work."""
        return work().link(work_id, kind, reference)

    @server.tool()
    def work_finish(work_id: str, handoff: str | None = None) -> dict:
        """Verify completion gates, then complete work and optionally record handoff."""
        return work().finish(work_id, handoff)

    @server.tool()
    def doctor(target: str = "local") -> dict:
        """Inspect target readiness without installing or changing tools."""
        from ai_dlc.setup.provision import doctor as inspect

        return inspect(root, target, machine)

    @server.tool()
    def project_docs_check() -> dict:
        """Inspect local document ownership and review gaps; never fetch or publish content."""
        from ai_dlc.documentation.documents import check_documents

        return check_documents(root)

    @server.tool()
    def project_docs_impact(base: str) -> dict:
        """Read changed sources and documentation review candidates for a Git comparison."""
        from ai_dlc.documentation.document_impact import inspect_impact

        return inspect_impact(root, base=base)

    @server.tool()
    def project_docs_disposition(base: str, decisions: list[dict], reviewer: str) -> dict:
        """Prepare evidence from explicit reviewed dispositions without writing files."""
        from ai_dlc.documentation.document_impact import prepare_disposition

        return prepare_disposition(root, base=base, decisions=decisions, reviewer=reviewer)

    @server.tool()
    def project_docs_gate(
        evidence: str = ".ai-dlc/documentation/current.json",
        baseline: str = ".ai-dlc/documentation/baseline.json",
        base: str | None = None,
    ) -> dict:
        """Check reviewed documentation evidence and historical debt; no mutation."""
        from ai_dlc.documentation.document_impact import check_gate

        return check_gate(root, evidence_path=evidence, baseline_path=baseline, base=base)

    @server.tool()
    def project_docs_inventory() -> dict:
        """Discover repository Markdown paths and exclusions without reading bodies."""
        from ai_dlc.documentation.document_inventory import inventory_documents

        return inventory_documents(root)

    @server.tool()
    def project_docs_search(
        query: str, sources: list[str] | None = None, max_bytes: int = 64000, limit: int = 20
    ) -> dict:
        """Search docs/, openspec/ and declared project Markdown; bounded, never private notes."""
        from ai_dlc.documentation.document_access import search_project_documents

        return search_project_documents(
            root, query=query, sources=sources, max_bytes=max_bytes, limit=limit
        )

    @server.tool()
    def project_docs_read(
        path: str, sources: list[str] | None = None, max_bytes: int = 64000
    ) -> dict:
        """Read one complete eligible project document within a byte budget."""
        from ai_dlc.documentation.document_access import read_project_document

        return read_project_document(root, path=path, sources=sources, max_bytes=max_bytes)

    @server.tool()
    def project_docs_review(
        base: str, paths: list[str], max_bytes: int = 64000, source: str = "catalog"
    ) -> dict:
        """Prepare selected local document bodies and mapped evidence for a harness review."""
        from ai_dlc.documentation.document_review import prepare_review

        return prepare_review(root, paths=paths, base=base, max_bytes=max_bytes, source=source)

    @server.tool()
    def project_docs_review_check(packet: dict, review: dict) -> dict:
        """Validate a harness review's citations and scope against current local sources."""
        from ai_dlc.documentation.document_review import validate_review

        return validate_review(root, packet=packet, review=review)

    @server.tool()
    def project_workspace_preview(name: str | None = None, bases: bool = False) -> dict:
        """Preview an additive linked workspace using the configured private vault; no writes."""
        from ai_dlc.documentation.knowledge_workspace import setup_workspace

        return setup_workspace(
            root, vault=config.get("paths", {}).get("vault"), name=name, bases=bases
        )

    @server.tool()
    def project_vault_mount_preview(
        vault: str | None = None, name: str | None = None, adopt: bool = False
    ) -> dict:
        """Preview exact native mount paths and local binding; no filesystem writes."""
        from ai_dlc.documentation.vault_link import link_vault

        return link_vault(
            root,
            vault=vault or config.get("paths", {}).get("vault"),
            name=name,
            mode="mount",
            adopt=adopt,
            apply=False,
        ).as_dict()

    @server.tool()
    def project_workspace_check() -> dict:
        """Inspect installation, activation, local mounts and navigation; never mutates."""
        from ai_dlc.documentation.workspace_diagnostics import inspect_project_workspace

        return inspect_project_workspace(root, vault=config.get("paths", {}).get("vault"))

    def knowledge():
        from ai_dlc.documentation.knowledge import Knowledge

        vault = config.get("paths", {}).get("vault")
        if not vault:
            raise ValueError("knowledge unavailable: machine vault path is not configured")
        return Knowledge(vault)

    @server.tool()
    def knowledge_find(query: str) -> list[dict]:
        """Find notes in the explicitly configured existing vault."""
        return knowledge().find(query)

    @server.tool()
    def knowledge_append(path: str, body: str, operation_id: str) -> dict:
        """Append content idempotently to a vault note."""
        return knowledge().append(path, body, operation_id)

    @server.tool()
    def knowledge_note(path: str, body: str, operation_id: str) -> dict:
        """Create a vault note without replacing existing content."""
        return knowledge().note(path, body, operation_id)

    return server


def serve(root: Path, machine: Path | None = None):
    make_server(root, machine).run(transport="stdio")
