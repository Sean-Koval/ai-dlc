# Obsidian knowledge guidance

AI-DLC's existing knowledge operations read and write Markdown in an existing
local vault. Configure `paths.vault` in the machine layer; do not commit a personal
vault path or note contents to the shared project. A named knowledge provider may
identify the logical vault, but `providers.<alias>.vault_path` does not replace the
runtime `paths.vault` setting.

Offline readiness checks directory availability only. It does not read notes,
create a vault, verify write permissions or establish live qualification. Use
explicit knowledge operations for authorized notes and retain their receipts.
The Obsidian desktop viewer is optional; headless note storage does not require it.
