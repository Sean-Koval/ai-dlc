"""Local stdio MCP; no raw provider mutations or alternate completion path."""

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from ai_dlc.cli import config_for
from ai_dlc.workflow import WorkService


def make_server(root: Path, machine: Path | None = None) -> FastMCP:
    config = config_for(root, machine)

    def work():
        return WorkService(root, config)

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
        from ai_dlc.provision import doctor as inspect

        return inspect(root, target, machine)

    def knowledge():
        from ai_dlc.knowledge import Knowledge

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
