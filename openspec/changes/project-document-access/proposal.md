# Provide scoped project-document discovery and reading to harnesses

## Why
Existing navigation and portal setup do not satisfy the approved existing-project cleanup and native Obsidian workflow.

## What Changes
- CLI and MCP SHALL share project-document search and read operations scoped to the selected repository and declared document sources, returning canonical paths and source identity with bounded reads.
- Generated guidance SHALL distinguish project-document access from private knowledge and route edits through ordinary repository tools and verification, without following vault links as general authority.

## Capabilities
### New Capabilities
- project-document-access: Provide scoped project-document discovery and reading to harnesses

## Impact
Shared Python documentation services, thin CLI/MCP adapters, portable skills and existing canonical documentation guidance. Related prior work: GitHub #32 and #34; their scope and qualification remain independent. No Jira, vault synchronization or remote publication.
