# Expose canonical project documents as editable Obsidian folders

## Why
Existing navigation and portal setup do not satisfy the approved existing-project cleanup and native Obsidian workflow.

## What Changes
- Vault linking SHALL retain portal default behavior and provide explicit mount mode exposing canonical docs and existing openspec directories as siblings beneath Projects/project. Bindings SHALL remain machine-local and use a stable checkout.
- Mount setup SHALL be idempotent, preserve authored notes and portals, support explicit adoption of matching links, reject conflicts, loops, overlapping targets and unexpected nested traversal, and report retained partial output.
- Private knowledge operations SHALL retain their existing filesystem boundary; native mounts SHALL not authorize generic symlink traversal, synchronization or publication.

## Capabilities
### New Capabilities
- obsidian-native-project-mounts: Expose canonical project documents as editable Obsidian folders

## Impact
Shared Python documentation services, thin CLI/MCP adapters, portable skills and existing canonical documentation guidance. Related prior work: GitHub #32 and #34; their scope and qualification remain independent. No Jira, vault synchronization or remote publication.
