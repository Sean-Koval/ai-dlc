"""Local stdio MCP; no raw provider mutations or alternate completion path."""

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from ai_dlc.cli import config_for
from ai_dlc.work.workflow import WorkService


def _register_work_tools(
    server: FastMCP, root: Path, machine: Path | None, registry: Any = None
) -> None:
    def work():
        return WorkService.from_project(root, machine=machine, registry=registry)

    @server.tool()
    def work_context(brief: bool = False) -> dict:
        """Offline session context; brief=True returns the what-next summary. No remote calls."""
        from ai_dlc.work.workflow import build_context

        return build_context(root, brief=brief)

    @server.tool()
    def work_new(
        work_id: str,
        from_issue: str | None = None,
        title: str | None = None,
        scope: str | None = None,
        requires_spec: bool | None = None,
        spec_reason: str | None = None,
        acceptance: list[str] | None = None,
    ) -> dict:
        """Create an unreviewed local work record from explicit fields or a tracker issue."""
        record = work().new(
            work_id,
            tracker_reference=from_issue,
            title=title,
            scope=scope,
            requires_spec=requires_spec,
            spec_reason=spec_reason,
            acceptance=acceptance,
        )
        return {"status": "created", "work": record}

    @server.tool()
    def work_pr(work_id: str) -> dict:
        """Open the pull request for the bound branch once, link it and commit the record."""
        return work().pr(work_id)

    @server.tool()
    def work_archive(work_id: str) -> dict:
        """Archive this work's active OpenSpec change and commit its affected files."""
        return work().archive(work_id)

    @server.tool()
    def work_review(work_id: str, reviewer: str | None = None) -> dict:
        """Mark an unstarted draft reviewed after validation; records the reviewer and time."""
        from ai_dlc.documentation.learnings import resolve_author

        name = reviewer if reviewer is not None else resolve_author(interactive=False)
        return work().review(work_id, name)

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
        """Read the local work record, bindings and specification state; no tracker query."""
        return work().status(work_id)

    @server.tool()
    def work_show(key: str) -> dict:
        """Work records and sessions a session key, session ID, ticket key or work ID names.

        Local and read-only: it resolves a trace's ``Work-Session`` key back to its ticket.
        """
        from ai_dlc.work.session_key import find_sessions

        return {"status": "ok", "query": key, "work": find_sessions(root, key)}

    @server.tool()
    def work_link(work_id: str, kind: str, reference: str) -> dict:
        """Link an artifact to reviewed work."""
        return work().link(work_id, kind, reference)

    @server.tool()
    def work_finish(work_id: str, handoff: str | None = None, learning: str | None = None) -> dict:
        """Verify completion gates, then complete work and optionally record handoff."""
        from ai_dlc.documentation.learnings import resolve_author

        author = resolve_author(interactive=False) if learning is not None else None
        return work().finish(work_id, handoff, learning, author)

    @server.tool()
    def doctor(target: str = "local") -> dict:
        """Inspect target readiness without installing or changing tools."""
        from ai_dlc.setup.provision import doctor as inspect

        return inspect(root, target, machine)


def _register_docs_tools(server: FastMCP, root: Path) -> None:
    from ai_dlc.documentation.document_inputs import Disposition, Review, ReviewPacket

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
    def project_docs_disposition(base: str, decisions: list[Disposition], reviewer: str) -> dict:
        """Prepare evidence from explicit reviewed dispositions without writing files."""
        from ai_dlc.documentation.document_impact import prepare_disposition

        return prepare_disposition(
            root, base=base, decisions=[dict(d) for d in decisions], reviewer=reviewer
        )

    @server.tool()
    def project_docs_record(
        base: str, decisions: list[Disposition], reviewer: str, evidence_id: str
    ) -> dict:
        """Merge reviewed dispositions into one work item's content-bound evidence file."""
        from ai_dlc.documentation.document_impact import record_disposition

        return record_disposition(
            root,
            base=base,
            decisions=[dict(d) for d in decisions],
            reviewer=reviewer,
            evidence_id=evidence_id,
        )

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
    def project_docs_review_check(packet: ReviewPacket, review: Review) -> dict:
        """Validate a harness review's citations and scope against current local sources.

        ``packet`` is ``project_docs_review``'s result, passed back unchanged. A review that
        does not match the typed schema is refused as a tool error before any check runs.
        """
        from ai_dlc.documentation.document_review import validate_review

        return validate_review(root, packet=dict(packet), review=dict(review))


def _register_workspace_tools(server: FastMCP, root: Path, config: dict) -> None:
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


def _register_knowledge_tools(server: FastMCP, root: Path, config: dict) -> None:
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

    @server.tool()
    def knowledge_check(records: str = ".", base: str | None = None) -> dict:
        """Check a records directory (relative to the project) against the record contract.

        Read-only. ``base`` is a git ref: decisions accepted there must not be edited.
        """
        from ai_dlc.documentation.knowledge_check import check_records

        return check_records(root / records, base=base)

    @server.tool()
    def knowledge_render(changed_since: str, dry_run: bool = True) -> dict:
        """Render records changed since a revision to the wiki role; the wiki's only writer.

        Dry run by default: it lists every planned upsert and writes nothing.
        """
        from ai_dlc.documentation.knowledge_render import KnowledgeRender

        return KnowledgeRender(root, config).render(changed_since, dry_run=dry_run)


def _register_knowledge_record_tools(server: FastMCP, root: Path) -> None:
    @server.tool()
    def knowledge_number_plan(records: str = ".") -> dict:
        """Preview the numbers merge-time CI would give slug-id records; writes nothing."""
        from ai_dlc.documentation.knowledge_bundle import number_records

        return number_records(root / records, write=False)

    @server.tool()
    def knowledge_index(records: str = ".", write: bool = False) -> dict:
        """Report, or with ``write`` regenerate, the OKF index.md files of a records directory."""
        from ai_dlc.documentation.knowledge_bundle import index_records

        return index_records(root / records, write=write)


def _register_knowledge_why_tool(server: FastMCP, root: Path) -> None:
    @server.tool()
    def knowledge_why(id: str, records: str = ".", project: str | None = None) -> dict:
        """Reconstruct a decision from local records: status, dates, owner, author and
        verifications, supersession both ways, linked conventions and lessons, and
        quoted evidence with payload state.
        """
        from ai_dlc.documentation.knowledge_why import why

        return why(root / records, id, project=project)


def _register_knowledge_stats_tool(server: FastMCP, root: Path, config: dict, registry) -> None:
    @server.tool()
    def knowledge_stats(
        since: str,
        records: str = ".",
        project: str | None = None,
        log: str | None = None,
        agent_repositories: list[str] | None = None,
    ) -> dict:
        """Measure the 1.0 outcomes: capture, review, agent loop and health; read-only.

        ``since`` is an ISO date or time; ``records`` and ``log`` are relative to the
        project. Reads git, the scm and tracker roles and, with ``log``, the capture
        batch's run log (.jsonl, .json or a folder). Without the project's ai-dlc.toml,
        a role or the log, those numbers read not measured; a wrong-shaped log is an
        error. Customer numbers count only in a view of their own ``project``.
        """
        from datetime import datetime

        from ai_dlc.documentation import knowledge_stats as measure

        # As the command: no ai-dlc.toml means no roles, not the packaged defaults'.
        roles = config if (root / "ai-dlc.toml").is_file() else None
        wired = measure.from_roles(
            roles, root, agent_repositories=agent_repositories or (), registry=registry
        )
        moment = datetime.fromisoformat(since)
        run_log = root / log if log else None
        return measure.stats(root / records, moment, project=project, log=run_log, **wired)


def _register_knowledge_records_tools(server: FastMCP, root: Path, config: dict, registry) -> None:
    from ai_dlc.documentation.knowledge_service import ProposedRecord

    def store():
        from ai_dlc.documentation.knowledge_service import KnowledgeRecords

        return KnowledgeRecords(root, config, registry=registry)

    @server.tool()
    def knowledge_search(
        type: str | None = None,
        scope: str | None = None,
        labels: list[str] | None = None,
        status: str | None = None,
        text: str | None = None,
        project: str | None = None,
    ) -> dict:
        """Find records through the knowledge role, ranked; ``text`` also reads bodies.

        Source records come back only when ``type`` is ``source``.

        Customer records come back only when ``project`` names their own project.
        """
        return store().search(type, scope, labels, status, text, project)

    @server.tool()
    def knowledge_get(id: str, project: str | None = None) -> dict:
        """One record by id or alias, with its body; a customer record only for its project."""
        return store().get(id, project)

    @server.tool()
    def knowledge_propose(
        records: list[ProposedRecord], branch: str, title: str, body: str = ""
    ) -> dict:
        """Check records, push them on a new branch of the knowledge store and open a draft PR."""
        return store().propose([dict(item) for item in records], branch, title, body)

    @server.tool()
    def knowledge_template(type: str | None = None) -> dict:
        """The packaged template for one record type; without ``type``, the types."""
        from ai_dlc.documentation.knowledge_service import template, templates

        return templates() if type is None else template(type)


def _register_tracker_tools(server: FastMCP, root: Path, config: dict, registry) -> None:
    from ai_dlc.work.tracker_items import CustomField, ItemLink

    def tracker():
        from ai_dlc.work.tracker_items import TrackerItems

        return TrackerItems(root, config, registry=registry)

    @server.tool()
    def tracker_get(reference: str) -> dict:
        """Read one tracker item through the tracker role, with its exec: labels."""
        return tracker().get(reference)

    @server.tool()
    def tracker_search(
        text: str | None = None,
        labels: list[str] | None = None,
        state: str | None = None,
        limit: int = 20,
    ) -> dict:
        """Find tracker items by text, labels and state through the tracker role; read-only."""
        return tracker().search(text, labels, state, limit)

    @server.tool()
    def tracker_comment(reference: str, body: str) -> dict:
        """Add one plain-text comment to an item; refuses one that names exec:agent."""
        return tracker().comment(reference, body)

    @server.tool()
    def tracker_create(
        title: str,
        body: str = "",
        labels: list[str] | None = None,
        correlation: str | None = None,
        issue_type: str | None = None,
        fields: list[CustomField] | None = None,
        parent: str | None = None,
        links: list[ItemLink] | None = None,
    ) -> dict:
        """File a tracker item once through the tracker role; refuses exec:agent in any case.

        A repeat with the same correlation (default: title and body) returns the first item.
        Where the tracker offers it: ``issue_type`` (native type ID), ``fields`` (each a
        custom field ID and text, a number, YYYY-MM-DD or an option's name), ``parent`` and
        ``links`` (``{"type": "Blocks", "target": "KAN-1"}``: the new item blocks KAN-1).
        """
        values = {item["field"]: item["value"] for item in fields or []}
        return tracker().create(
            title,
            body,
            labels,
            correlation,
            issue_type,
            values,
            parent,
            [dict(link) for link in links or []],
        )

    @server.tool()
    def tracker_create_decision(
        question: str,
        blocks: str,
        options: list[str],
        recommendation: str,
        default: str,
        scope: str,
        due: str,
        body: str = "",
        labels: list[str] | None = None,
        parent: str | None = None,
    ) -> dict:
        """File a decision for a person that blocks one open work item; refuses exec:agent.

        ``question`` ends in ?; two to five ``options``; ``default`` applies if nobody
        answers by ``due`` (YYYY-MM-DD); ``scope`` is one of the tracker's scope values.
        A repeat for the same question and work item returns the first decision.
        """
        return tracker().create_decision(
            question,
            blocks,
            options,
            recommendation,
            default,
            scope,
            due,
            body,
            labels,
            parent=parent,
        )

    @server.tool()
    def tracker_update(
        reference: str,
        title: str | None = None,
        body: str | None = None,
        labels: list[str] | None = None,
    ) -> dict:
        """Set the title, body or whole label set of an open item; never its status.

        Refuses exec:agent in any case, and keeps one a person already set.
        """
        return tracker().update(reference, title, body, labels)


def _register_transcripts_tool(server: FastMCP, root: Path, config: dict) -> None:
    @server.tool()
    def knowledge_pull_transcripts(
        since: str, into: str | None = None, dry_run: bool = True
    ) -> dict:
        """Land new meeting transcripts in the knowledge inbox through the transcripts role.

        One Source record and raw payload per transcript, idempotent by transcript id.
        Dry run by default: it lists what it would write. ``into`` is a local checkout.
        """
        from ai_dlc.documentation.knowledge_transcripts import TranscriptPull

        target = Path(into) if into else None
        return TranscriptPull(root, config, into=target).pull(since, dry_run=dry_run)


def make_server(root: Path, machine: Path | None = None, *, registry: Any = None) -> FastMCP:
    """``registry`` replaces the providers of the project, for tests."""
    config = config_for(root, machine)
    server = FastMCP("ai-dlc")
    _register_work_tools(server, root, machine, registry)
    _register_docs_tools(server, root)
    _register_workspace_tools(server, root, config)
    _register_knowledge_tools(server, root, config)
    _register_knowledge_record_tools(server, root)
    _register_knowledge_why_tool(server, root)
    _register_knowledge_stats_tool(server, root, config, registry)
    _register_knowledge_records_tools(server, root, config, registry)
    _register_tracker_tools(server, root, config, registry)
    _register_transcripts_tool(server, root, config)
    return server


def serve(root: Path, machine: Path | None = None):
    make_server(root, machine).run(transport="stdio")
