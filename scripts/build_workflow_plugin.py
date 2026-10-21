"""Build the optional ai-dlc workflow plugin for Claude Code and Codex; --check refuses drift.

The plugin directory ``plugins/ai-dlc-workflow/`` is generated and committed. It
packages the provider-neutral workflow guidance as a skill, the selected team
skills from ``agents/skills/`` (verified against ``agents/skills.lock.json``) and
the stdlib-only hook shim from ``src/ai_dlc/harness/hook_shim.py``. Output is
byte-deterministic: no timestamps, absolute paths or build-machine data.

``native/codex/`` inside it is the Codex form: the same skill bytes, a Codex
``hooks.json`` (also usable as a ``~/.codex/hooks.json`` fragment), the shim, an
``AGENTS.fragment.md`` for harnesses that read only AGENTS.md, and a
``.codex-plugin/plugin.json`` manifest. A harness publishes the Claude plugin
without ``native/`` and the Codex form separately (scripts/publish_workflow_plugin.py).

``plugin.lock.json`` records one digest per component, a content digest over them,
the digest of every published file, and the Codex form's own digests; the revision
increases whenever either content digest changes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from ai_dlc import __version__
from ai_dlc.harness import agents

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = "ai-dlc-workflow"
PLUGIN_DIRECTORY = Path("plugins") / PLUGIN
GUIDE = "ai-dlc-workflow"
# day-start and day-end journal over a personal vault; they stay in the personal profile.
TEAM_SKILLS = (
    "design-brief",
    "design-evaluate",
    "discovery",
    "document-organize",
    "document-review",
    "handoff",
    "needs-spec",
    "prd-draft",
    "review-inbox",
    "spec-from-prd",
)
EXCLUDED_SKILLS = ("day-end", "day-start")
AUTHORED = frozenset({"README.md"})
NATIVE = "native/codex"
CODEX_HOOK_ROOT = "${PLUGIN_ROOT:-${CODEX_HOME:-$HOME/.codex}/" + PLUGIN + "}"
HOOK_EVENTS = (("SessionStart", "session-start"), ("PreToolUse", "pre-tool"), ("Stop", "stop"))
# A fully featured adopted configuration exposes every conditional guidance line;
# the filter below then keeps only what holds without a concrete project.
GUIDANCE_CONFIG: dict = {
    "roles": {
        "specs": "openspec",
        "tracker": "github-issues",
        "scm": "github",
        "knowledge": "obsidian",
    },
    "checks": {"required": ["documentation"], "commands": {}},
}
PROJECT_TERMS = (
    "openspec",
    "github",
    "obsidian",
    "jira",
    "plane",
    "linear",
    "provider",
    "documentation gate",
    "verification",
)
ADOPTED = "If `ai-dlc.toml` exists at the repo root and `ai-dlc` is on PATH: "


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def guidance_lines() -> tuple[list[str], list[str]]:
    """Split shared AGENTS.md guidance into (portable, adopted-repository) lines."""
    lines = agents._shared_guidance_lines(GUIDANCE_CONFIG, ["claude-code"], "", "")
    portable: list[str] = []
    adopted: list[str] = []
    for line in lines:
        if line.startswith("## "):
            break  # Verification and later sections name a concrete project's checks.
        if not line or line.startswith("# "):
            continue
        if any(term in line.lower() for term in PROJECT_TERMS):
            continue
        (adopted if "ai-dlc" in line else portable).append(line)
    return portable, adopted


def guide_skill() -> str:
    portable, adopted = guidance_lines()
    body = [
        "---",
        f"name: {GUIDE}",
        (
            "description: Use at the start of development work in any repository to follow "
            "the ai-dlc workflow: shape scope, specify when needed, deliver through a "
            "reviewed pull request and finish against merged evidence."
        ),
        "---",
        "",
        "# ai-dlc workflow",
        "",
        "This optional plugin carries the ai-dlc workflow guidance, team skills and safe hooks.",
        "It works in any repository; lifecycle commands apply only to adopted repositories.",
        "",
        "## Always",
        "",
        "- Use the team skills in this plugin for judgment: discovery, prd-draft, needs-spec,",
        "  spec-from-prd, review-inbox, handoff, document-review, document-organize and the",
        "  optional design-brief and design-evaluate.",
        "- When the repository renders its own copies of these skills (unprefixed, under",
        "  `.claude/skills`), prefer the repository copies and its AGENTS.md guidance.",
        *(f"- {line}" for line in portable),
        "",
        "## In adopted repositories",
        "",
        "Adopted repositories carry fuller guidance in their AGENTS.md managed section.",
        "",
        *(f"- {ADOPTED}{line[0].lower()}{line[1:]}" for line in adopted),
        f"- {ADOPTED}when recording a learning with `ai-dlc work finish --learning`, set",
        "  `AI_DLC_AUTHOR=agent:<client>@<content_digest>`, using the `content_digest` in",
        "  this plugin's `plugin.lock.json`, so the note records who wrote it.",
        "",
        "## Hooks",
        "",
        "The plugin hooks deny destructive shell commands such as `rm -rf`. In adopted",
        "repositories with `ai-dlc` installed they delegate to `ai-dlc hook`; inside hangar",
        "sandboxes they never delegate and never block `git push` or `gh pr create`. Set",
        "`AI_DLC_HOOKS=off` to disable them or `AI_DLC_HOOKS=quiet` to drop the session line.",
        "",
    ]
    return "\n".join(body)


def hooks_document() -> str:
    hooks: dict[str, list[dict]] = {}
    for event, action in HOOK_EVENTS:
        entry: dict = {
            "hooks": [
                {
                    "type": "command",
                    "command": "python3",
                    "args": ["${CLAUDE_PLUGIN_ROOT}/hooks/aidlc_hook.py", action],
                    "timeout": 10,
                }
            ]
        }
        if event == "PreToolUse":
            entry["matcher"] = "Bash|exec_command"
        hooks[event] = [entry]
    return json.dumps({"hooks": hooks}, indent=2, sort_keys=True) + "\n"


def codex_hooks_document() -> str:
    """The `.codex/hooks.json` shape `agents._plan_hooks` writes, pointing at the shim.

    Codex sets PLUGIN_ROOT for plugin hooks; as a native fragment the shim is expected
    at ``$CODEX_HOME/ai-dlc-workflow/hooks/aidlc_hook.py`` (``native/codex/ai-dlc-workflow/``
    in a harness maps there).
    """
    hooks: dict[str, list[dict]] = {}
    for event, action in HOOK_EVENTS:
        entry: dict = {
            "hooks": [
                {
                    "type": "command",
                    "command": f'python3 "{CODEX_HOOK_ROOT}/hooks/aidlc_hook.py" {action}',
                    "timeout": 10,
                }
            ]
        }
        if event == "PreToolUse":
            entry["matcher"] = "Bash|exec_command"
        hooks[event] = [entry]
    return json.dumps({"hooks": hooks}, indent=2, sort_keys=True) + "\n"


def agents_fragment() -> str:
    """The guide skill body without its frontmatter, for harnesses that only read AGENTS.md."""
    guide = guide_skill()
    body = guide.split("\n---\n", 1)[1].lstrip("\n")
    return (
        "<!-- Generated by ai-dlc scripts/build_workflow_plugin.py; append to AGENTS.md. -->\n\n"
        + body
    )


def codex_files(files: dict[str, bytes], root: Path) -> dict[str, bytes]:
    """The Codex form (without its manifest), relative to ``native/codex/``."""
    native = {
        path: data
        for path, data in files.items()
        if path.startswith("skills/") and path.endswith("/SKILL.md")
    }
    native["hooks.json"] = codex_hooks_document().encode()
    native["hooks/aidlc_hook.py"] = (root / "src/ai_dlc/harness/hook_shim.py").read_bytes()
    native["AGENTS.fragment.md"] = agents_fragment().encode()
    return dict(sorted(native.items()))


def file_digests(files: dict[str, bytes]) -> dict[str, str]:
    return {path: sha256(data) for path, data in sorted(files.items())}


def components(files: dict[str, bytes]) -> dict[str, str]:
    result = {f"skill:{name}": sha256(files[f"skills/{name}/SKILL.md"]) for name in TEAM_SKILLS}
    result[f"guide:{GUIDE}"] = sha256(files[f"skills/{GUIDE}/SKILL.md"])
    result["hooks:ai-dlc"] = sha256(
        canonical(
            {path: sha256(files[path]) for path in ("hooks/hooks.json", "hooks/aidlc_hook.py")}
        )
    )
    return dict(sorted(result.items()))


def previous_lock(plugin_root: Path) -> dict:
    try:
        lock = json.loads((plugin_root / "plugin.lock.json").read_text())
    except (OSError, ValueError):
        return {}
    return lock if isinstance(lock, dict) else {}


def plan(root: Path) -> dict[str, bytes]:
    """Every generated plugin file, relative to the plugin directory."""
    sources = agents._skill_sources({"agents": {"skills": list(TEAM_SKILLS)}})
    files: dict[str, bytes] = {
        f"skills/{name}/SKILL.md": sources[name].encode() for name in TEAM_SKILLS
    }
    files[f"skills/{GUIDE}/SKILL.md"] = guide_skill().encode()
    files["hooks/hooks.json"] = hooks_document().encode()
    files["hooks/aidlc_hook.py"] = (root / "src/ai_dlc/harness/hook_shim.py").read_bytes()
    parts = components(files)
    digest = sha256(canonical(parts))
    native = codex_files(files, root)
    native_digest = sha256(canonical(file_digests(native)))
    previous = previous_lock(root / PLUGIN_DIRECTORY)
    revision = previous.get("revision", 0)
    if not isinstance(revision, int) or revision < 0:
        raise ValueError("plugin.lock.json revision must be a nonnegative integer")
    previous_native = previous.get("native", {}).get("codex", {}).get("content_digest")
    if previous.get("content_digest") != digest or previous_native != native_digest:
        revision += 1
    version = f"{__version__}-r{revision}"
    description = (
        "ai-dlc workflow guidance, team skills and CLI-optional safety hooks; "
        "opt in per session or settings scope."
    )
    native[".codex-plugin/plugin.json"] = (
        json.dumps(
            {
                "name": PLUGIN,
                "version": version,
                "description": description,
                "author": {"name": "AI-DLC contributors"},
                "repository": "https://github.com/Sean-Koval/ai-dlc",
                "license": "MIT",
                "keywords": ["workflow", "skills", "hooks", "ai-dlc"],
                "skills": "./skills/",
                "hooks": "./hooks.json",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode()
    manifest = {
        "name": PLUGIN,
        "displayName": "ai-dlc workflow",
        "version": version,
        "description": description,
        "author": {"name": "AI-DLC contributors"},
        "repository": "https://github.com/Sean-Koval/ai-dlc",
        "license": "MIT",
        "keywords": ["workflow", "skills", "hooks", "ai-dlc"],
        "defaultEnabled": False,
        "metadata": {
            "content_digest": digest,
            "source": f"Sean-Koval/ai-dlc/{PLUGIN_DIRECTORY.as_posix()}",
        },
    }
    files[".claude-plugin/plugin.json"] = (
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    ).encode()
    readme = root / PLUGIN_DIRECTORY / "README.md"
    published = {**files, **({"README.md": readme.read_bytes()} if readme.is_file() else {})}
    lock = {
        "schema": 1,
        "plugin": PLUGIN,
        "revision": revision,
        "components": parts,
        "content_digest": digest,
        # Every file a harness receives (plugin.lock.json itself aside), so a publisher
        # can prove a target directory is an unmodified earlier publication.
        "files": file_digests(published),
        "native": {
            "codex": {
                "content_digest": native_digest,
                "files": file_digests(native),
            }
        },
    }
    files["plugin.lock.json"] = (json.dumps(lock, indent=2, sort_keys=True) + "\n").encode()
    files.update({f"{NATIVE}/{path}": data for path, data in native.items()})
    return dict(sorted(files.items()))


def existing(plugin_root: Path) -> dict[str, bytes]:
    if not plugin_root.is_dir():
        return {}
    return {
        path.relative_to(plugin_root).as_posix(): path.read_bytes()
        for path in sorted(plugin_root.rglob("*"))
        if path.is_file()
        and path.relative_to(plugin_root).as_posix() not in AUTHORED
        and "__pycache__" not in path.parts
    }


def drift(root: Path) -> list[str]:
    planned = plan(root)
    current = existing(root / PLUGIN_DIRECTORY)
    return sorted(
        path for path in planned.keys() | current.keys() if planned.get(path) != current.get(path)
    )


def write(root: Path) -> dict[str, bytes]:
    plugin_root = root / PLUGIN_DIRECTORY
    planned = plan(root)
    for relative in existing(plugin_root).keys() - planned.keys():
        (plugin_root / relative).unlink()
    for relative, data in planned.items():
        path = plugin_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.is_file() or path.read_bytes() != data:
            path.write_bytes(data)
    for directory in sorted(plugin_root.rglob("*"), reverse=True):
        if directory.is_dir() and not any(directory.iterdir()):
            directory.rmdir()
    return planned


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Refuse a stale plugin directory.")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    try:
        if args.check:
            stale = drift(args.root)
            if stale:
                print(
                    "Workflow plugin is stale; run "
                    "`uv run --locked --no-sync python scripts/build_workflow_plugin.py`: "
                    + ", ".join(stale),
                    file=sys.stderr,
                )
                return 1
            print("Workflow plugin is current")
            return 0
        planned = write(args.root)
    except ValueError as exc:
        print(f"Workflow plugin build refused: {exc}", file=sys.stderr)
        return 1
    lock = json.loads(planned["plugin.lock.json"])
    print(f"Built {PLUGIN_DIRECTORY.as_posix()} r{lock['revision']} {lock['content_digest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
