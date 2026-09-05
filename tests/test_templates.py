import asyncio
import json
import os
import re
import subprocess
import tarfile
import tomllib
import zipfile
from pathlib import Path
from urllib.parse import unquote

import pytest

from ai_dlc.config import resolve_files
from ai_dlc.credentials import credential_status
from ai_dlc.files import assets
from ai_dlc.templates import adopt, sync

_PROHIBITED_PUBLIC_TOKENS = {
    "personal",
    "account",
    "organization",
    "org",
    "owner",
    "email",
    "workspace",
    "team",
    "vault",
    "repository",
    "remote",
    "path",
    "password",
    "secret",
    "api",
    "key",
    "token",
    "access",
}
_REFERENCE_KEYS = {"token_env", "variable"}
_ENVIRONMENT_NAME = re.compile(r"^[A-Z_][A-Z0-9_]*$")
_POSIX_PATH = re.compile(r"(?<![\w.~-])/(?![/\s])[^\s`\"'<>()\[\]{}]+")
_WINDOWS_DRIVE_PATH = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/][^\s`\"'<>()\[\]{}]+")
_UNC_PATH = re.compile(r"(?<!\\)\\\\[^\\/\s]+[\\/][^\s`\"'<>()\[\]{}]+")
_HOME_PATH = re.compile(r"(?<![\w])~(?:[A-Za-z0-9._-]+)?[\\/][^\s`\"'<>()\[\]{}]+")
_REMOTE_URL = re.compile(r"(?i)\b(?:https?|ssh|git|file)://")
_SCP_REMOTE = re.compile(
    r"(?i)(?<![\w@.-])(?:[\w.+-]+@)?[A-Za-z0-9][\w.-]*:"
    r"(?:~?[\\/])?[^\s:]+[\\/][^\s]+"
)
_EMAIL_ADDRESS = re.compile(r"[\w.+-]+@[\w.-]+")
_STRIPE_LIKE_PREFIX = "sk" + "_live_"
_CREDENTIAL_SIGNATURE = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_[A-Za-z0-9]{20,}|AKIA[A-Z0-9]{12,}|"
    + re.escape(_STRIPE_LIKE_PREFIX)
    + r"[A-Za-z0-9]{8,})(?![A-Za-z0-9])"
)
_PLACEHOLDER_SECRET = re.compile(
    r"(?i)(?<![A-Za-z0-9])(?:placeholder|representative)[-_ ]secret(?![A-Za-z0-9])"
)
_SECRET_VALUE_TOKENS = {"password", "secret", "token", "key"}
_SURROUNDING_PUNCTUATION = " \t\r\n`*()[]{}<>\"',;!?"
_TOML_KEY_PART = r'(?:[A-Za-z_][A-Za-z0-9_-]*|"[^"\r\n]+"|\'[^\'\r\n]+\')'
_COMMENTED_ASSIGNMENT = re.compile(
    rf"^\s*(?P<lhs>{_TOML_KEY_PART}(?:\s*\.\s*{_TOML_KEY_PART})*)\s*="
)
_TOML_KEY_COMPONENT = re.compile(_TOML_KEY_PART)

_HANDBOOK_TRANSLATION = str.maketrans(
    {
        "‘": "'",
        "’": "'",
        "ʼ": "'",
        "‐": "-",
        "‑": "-",
        "‒": "-",
        "–": "-",
        "—": "-",
        "―": "-",
        "−": "-",
    }
)
_HANDBOOK_TARGET = re.compile(
    r"(?:\.env(?:\.(?:\*|[a-z0-9_-]+))?(?:\s+files?)?|credential\s+values?)"
)
_HANDBOOK_ACTION_BODY = (
    r"(?:git\s+(?:add|commit(?:ting)?)|commit(?:ting)?|stag(?:e|ing)|"
    r"track(?:ing)?|check[- ]in|version[- ]control)"
)
_HANDBOOK_ACTION = re.compile(rf"\b{_HANDBOOK_ACTION_BODY}\b")
_HANDBOOK_SENTENCE_BREAK = re.compile(r"[!?]+|\.(?=\s|$)")
_HANDBOOK_CLAUSE_BREAK = re.compile(
    r"(?:[;]+|,?\s+\b(?:but|however|yet|whereas|although|though|instead)\b\s*,?\s*)"
)
_DIRECT_ACTION_NEGATION = re.compile(
    r"\b(?:never(?:\s*,?\s*ever)?|do\s+not(?:\s+ever)?|don't(?:\s+ever)?|"
    r"must\s+not(?:\s+ever)?|avoid(?:\s+ever)?)\s*,?\s*$"
)
_NEGATION_REVERSAL = re.compile(r"\b(?:unless|except)\b")
_PERMISSION_REVERSAL = re.compile(
    rf"\b(?:you\s+)?(?:may|can)\b[^!?;]*?\b(?:do\s+so|{_HANDBOOK_ACTION_BODY})\b"
)


def _key_tokens(key):
    separated = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", key)
    separated = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", separated)
    return set(re.split(r"[-_.\s]+", separated.lower())) - {""}


def _assert_public_identifier(identifier, location=""):
    if identifier in _REFERENCE_KEYS:
        return
    assert not (_key_tokens(identifier) & _PROHIBITED_PUBLIC_TOKENS), location


def _assert_public_value(value, location=""):
    content = unquote(value).strip(_SURROUNDING_PUNCTUATION)
    assert not _CREDENTIAL_SIGNATURE.search(content), location
    assert not _PLACEHOLDER_SECRET.search(content), location
    if _ENVIRONMENT_NAME.fullmatch(content):
        return
    assert not _POSIX_PATH.search(content), location
    assert not _WINDOWS_DRIVE_PATH.search(content), location
    assert not _UNC_PATH.search(content), location
    assert not _HOME_PATH.search(content), location
    assert not _REMOTE_URL.search(content), location
    assert not _SCP_REMOTE.search(content), location
    assert not _EMAIL_ADDRESS.search(content), location
    if re.fullmatch(r"[A-Za-z0-9_-]+", content):
        assert not (_key_tokens(content) & _SECRET_VALUE_TOKENS), location


def _assert_public_example(value, location=""):
    if isinstance(value, dict):
        for key, child in value.items():
            _assert_public_identifier(key, location)
            if key in _REFERENCE_KEYS:
                assert isinstance(child, str) and _ENVIRONMENT_NAME.fullmatch(child), location
            _assert_public_example(child, f"{location}.{key}".strip("."))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_public_example(child, f"{location}[{index}]")
    elif isinstance(value, str):
        _assert_public_value(value, location)


def _toml_comment_payloads(raw):
    delimiter = None
    escaped = False
    index = 0
    while index < len(raw):
        if delimiter:
            if len(delimiter) == 3:
                if raw.startswith(delimiter, index):
                    delimiter = None
                    index += 3
                    continue
            elif delimiter == '"':
                if escaped:
                    escaped = False
                elif raw[index] == "\\":
                    escaped = True
                elif raw[index] == delimiter:
                    delimiter = None
            elif raw[index] == delimiter:
                delimiter = None
        elif raw.startswith(('"""', "'''"), index):
            delimiter = raw[index : index + 3]
            index += 3
            continue
        elif raw[index] in {'"', "'"}:
            delimiter = raw[index]
        elif raw[index] == "#":
            end = raw.find("\n", index)
            if end == -1:
                end = len(raw)
            yield raw[index + 1 : end]
            index = end
            continue
        index += 1


def _assert_public_raw_content(raw):
    _assert_public_example(tomllib.loads(raw))
    for payload in _toml_comment_payloads(raw):
        _assert_public_value(payload, "comment")
        assignment = _COMMENTED_ASSIGNMENT.match(payload)
        if not assignment:
            continue
        for component in _TOML_KEY_COMPONENT.finditer(assignment.group("lhs")):
            identifier = component.group(0).strip("\"'")
            _assert_public_identifier(identifier, identifier)


def _assert_handbook_safety(pages):
    for page in pages.values():
        normalized = page.translate(_HANDBOOK_TRANSLATION).lower()
        normalized = re.sub(r"[`*_~]+", "", normalized)
        normalized = " ".join(normalized.split())
        for sentence in _HANDBOOK_SENTENCE_BREAK.split(normalized):
            protected_rule_seen = False
            cursor = 0
            for clause in _HANDBOOK_CLAUSE_BREAK.split(sentence):
                clause_start = sentence.find(clause, cursor)
                cursor = clause_start + len(clause)
                if protected_rule_seen and _PERMISSION_REVERSAL.search(clause):
                    raise AssertionError("protected handbook rule is reversed")
                if not _HANDBOOK_TARGET.search(clause):
                    continue
                for action in _HANDBOOK_ACTION.finditer(clause):
                    assert _DIRECT_ACTION_NEGATION.search(clause[: action.start()])
                    protected_rule_seen = True
                    action_end = clause_start + action.end()
                    assert not _NEGATION_REVERSAL.search(sentence[action_end:])


def git(root, *args):
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    ).stdout


@pytest.fixture
def template(tmp_path):
    source = tmp_path / "template"
    source.mkdir()
    (source / "copier.yml").write_text("_subdirectory: project\n")
    project = source / "project"
    project.mkdir()
    (project / "{{ _copier_conf.answers_file }}.jinja").write_text(
        "{{ _copier_answers | to_nice_yaml }}"
    )
    (project / "managed.txt").write_text("first\nsecond\nthird\n")
    git(source, "init")
    git(source, "add", ".")
    git(source, "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "v1")
    git(source, "tag", "v1.0.0")
    return source


def release(source, text):
    (source / "project/managed.txt").write_text(text)
    git(source, "add", ".")
    git(source, "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "v2")
    git(source, "tag", "v2.0.0")


def test_adopt_preview_and_conflict_preserve(tmp_path, template):
    root = tmp_path / "app"
    root.mkdir()
    (root / "app.py").write_text("user code")
    assert adopt(root, template_source=str(template), vcs_ref="v1.0.0")["status"] == "planned"
    assert not (root / "managed.txt").exists()
    (root / "managed.txt").write_text("mine")
    result = adopt(root, apply=True, template_source=str(template))
    assert result["status"] == "conflict"
    assert (root / "managed.txt").read_text() == "mine"
    assert not (root / ".copier-answers.yml").exists()


def test_real_update_preserves_user_edits(tmp_path, template):
    root = tmp_path / "app"
    adopt(root, apply=True, template_source=str(template), vcs_ref="v1.0.0")
    (root / "app.py").write_text("my application")
    (root / "managed.txt").write_text("first\nsecond\nthird\nlocal addition\n")
    release(template, "upstream\nsecond\nthird\n")
    result = sync(root, apply=True)
    assert result["status"] == "applied"
    assert (root / "managed.txt").read_text() == "upstream\nsecond\nthird\nlocal addition\n"
    assert (root / "app.py").read_text() == "my application"
    assert not (root / ".git").exists()


def test_update_conflict_does_not_touch_destination(tmp_path, template):
    root = tmp_path / "app"
    adopt(root, apply=True, template_source=str(template), vcs_ref="v1.0.0")
    (root / "managed.txt").write_text("local\nsecond\nthird\n")
    before = {p.name: p.read_bytes() for p in root.iterdir()}
    release(template, "upstream\nsecond\nthird\n")
    assert sync(root, apply=True)["status"] == "conflict"
    assert before == {p.name: p.read_bytes() for p in root.iterdir()}


@pytest.mark.parametrize("preset", ["generic", "python", "node", "rust"])
def test_presets(tmp_path, preset):
    import tomllib

    root = tmp_path / preset
    assert adopt(root, preset, apply=True)["status"] == "applied"
    cfg = tomllib.loads((root / "ai-dlc.toml").read_text())
    assert cfg["schema"] == 4
    assert cfg["roles"]["deploy"] == "none"
    assert "repository" not in cfg.get("scm", {})
    assert (root / ".github/workflows/verify.yml").exists()
    assert not list((root / ".ai-dlc/work").glob("*.toml"))


@pytest.mark.parametrize("capabilities", [None, ["specs", "scm"], []])
def test_project_template_includes_workflow_handbook(tmp_path, capabilities):
    root = tmp_path / "project"

    assert adopt(root, apply=True, capabilities=capabilities)["status"] == "applied"

    expected = {
        "docs/development-workflow.md",
        "docs/workflows/brownfield.md",
        "docs/workflows/design-to-implementation.md",
        "docs/workflows/greenfield.md",
        "docs/workflows/tool-map.md",
    }
    generated = {path.relative_to(root).as_posix() for path in root.rglob("*.md")}
    assert expected <= generated
    handbook = (root / "docs/development-workflow.md").read_text()
    assert (
        "[Development workflow](docs/development-workflow.md)" in (root / "AI-DLC.md").read_text()
    )
    selected = (
        {
            "specs",
            "tracker",
            "knowledge",
            "scm",
            "deploy",
            "agent-client",
        }
        if capabilities is None
        else set(capabilities)
    )
    for role in ["specs", "tracker", "knowledge", "scm", "deploy", "agent-client"]:
        state = "configured" if role in selected else "not configured"
        assert f"- `{role}`: {state}" in handbook
    design_headings = {
        line
        for line in (root / "docs/templates/design.md").read_text().splitlines()
        if line.startswith("## ")
    }
    assert {
        "## Identity and links",
        "## Outcome and scope",
        "## User journey and states",
        "## System boundaries and interfaces",
        "## Decisions and rationale",
        "## Behavioral contract",
        "## Verification strategy",
        "## Delivery and recovery",
    } <= design_headings


def test_portable_profile_examples_and_rendered_handbook_are_safe(tmp_path):
    """Catch a missing packaged enrollment example or an unsafe generated handbook."""
    profile_path = assets("profiles") / "example/ai-dlc-profile.toml"
    machine_path = assets("profiles") / "machines/example.toml"

    assert profile_path.is_file()
    profile = tomllib.loads(profile_path.read_text())
    resolved_profile = resolve_files(personal=profile_path).values
    assert resolved_profile["profile_id"] == "example-development"
    assert resolved_profile["modules"]["include"] == ["core", "python"]
    assert resolved_profile["agents"]["servers"] == []
    assert profile["roles"] == {
        "specs": "openspec",
        "tracker": "linear",
        "knowledge": "obsidian",
        "scm": "github",
        "deploy": "none",
        "agent-client": ["claude-code", "codex"],
    }
    assert profile["credentials"] == {
        "linear-sandbox": {
            "description": "Credential for a sandbox tracker integration",
            "required_by": ["provider.linear"],
        }
    }

    machine = tomllib.loads(machine_path.read_text())
    resolved = resolve_files(personal=profile_path, machine=machine_path).values
    assert machine["credentials"]["linear-sandbox"] == {
        "source": "environment",
        "variable": "LINEAR_SANDBOX_TOKEN",
    }
    assert credential_status(resolved, environ={}) == [
        {
            "id": "linear-sandbox",
            "description": "Credential for a sandbox tracker integration",
            "required_by": ["provider.linear"],
            "source": "environment",
            "variable": "LINEAR_SANDBOX_TOKEN",
            "configured": True,
            "present": False,
        }
    ]
    _assert_public_example(profile)
    _assert_public_example(machine)
    for raw in [profile_path.read_text(), machine_path.read_text()]:
        _assert_public_raw_content(raw)

    root = tmp_path / "generated-project"
    assert adopt(root, apply=True)["status"] == "applied"
    pages = {path.relative_to(root): path.read_text() for path in root.rglob("*.md")}
    handbook = "\n".join(pages.values()).lower()
    for topic in [
        "portable profile",
        "machine enrollment",
        "credential",
        "local cli",
        "hosted",
        "design",
        "implementation",
    ]:
        assert topic in handbook
    assert "ai-dlc machine enroll source --profile-id" in handbook
    assert "ai-dlc machine sync --apply" in handbook
    from ai_dlc.mcp_server import make_server

    mcp_tools = {tool.name for tool in asyncio.run(make_server(root).list_tools())}
    tool_map = pages[Path("docs/workflows/tool-map.md")].lower()
    documented_mcp_tools = set(re.findall(r"`((?:work|knowledge)_[a-z_]+|doctor)`", tool_map))
    assert documented_mcp_tools == mcp_tools
    assert not {name for name in mcp_tools if name.startswith("machine_")}
    assert not re.findall(r"`machine_[a-z_]+`", tool_map)
    _assert_handbook_safety(pages)
    git(root, "init")
    for relative in [".env", ".env.local", ".ai-dlc/local/review.json"]:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ignored")
        assert (
            subprocess.run(
                ["git", "-C", str(root), "check-ignore", "-q", relative], check=False
            ).returncode
            == 0
        )


def test_component_catalog_and_guidance_ship_in_the_distribution(tmp_path):
    """Catch a package build that omits the catalog or its provider guidance."""
    project = Path(__file__).resolve().parents[1]
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(tmp_path)],
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "UV_OFFLINE": "1"},
    )

    wheel = next(tmp_path.glob("ai_dlc-*.whl"))
    with zipfile.ZipFile(wheel) as archive:
        catalog = archive.read("ai_dlc/assets/modules/components.json")
        members = set(archive.namelist())

    components = json.loads(catalog)["components"]
    guidance = {
        f"ai_dlc/assets/agents/{path}" for component in components for path in component["guidance"]
    }
    assert guidance <= members


@pytest.mark.parametrize(
    "identifier",
    [
        "workspace_id",
        "workspace-id",
        "workspaceId",
        "owner_email",
        "owner-email",
        "ownerEmail",
        "api_token",
        "api-token",
        "apiToken",
        "APIToken",
        "account",
        "organization",
        "org",
        "team",
        "vault",
        "repository",
        "remote",
        "local_path",
        "local-path",
        "localPath",
        "password",
        "client_secret",
        "access_key",
    ],
)
def test_public_example_helper_rejects_sensitive_identifiers(identifier):
    with pytest.raises(AssertionError):
        _assert_public_example({"outer": {"nested": {identifier: "neutral"}}})


def test_public_example_helper_rejects_sensitive_nested_parsed_toml_keys():
    parsed = tomllib.loads('[outer.nested]\n"APIToken" = "neutral"\n')

    with pytest.raises(AssertionError):
        _assert_public_example(parsed)


def test_public_example_helper_allows_schema_and_environment_bindings():
    _assert_public_example(
        {
            "schema": 4,
            "profile_id": "example-development",
            "roles": {"specs": "openspec"},
            "paths": {},
            "providers": {"linear": {"token_env": "LINEAR_SANDBOX_TOKEN"}},
            "credentials": {
                "linear-sandbox": {
                    "description": "Ordinary path and key prose",
                    "required_by": ["provider.linear"],
                    "source": "environment",
                    "variable": "LINEAR_SANDBOX_TOKEN",
                }
            },
        }
    )


_SENSITIVE_PARSED_VALUES = [
    "person@example.test",
    "/Users/example/profile",
    "~/profiles/example",
    r"C:\Users\example\profile",
    r"\\server\share\profile",
    "http://example.test/group/profile.git",
    "https://example.test/group/profile.git",
    "ssh://git@example.test/group/profile.git",
    "git://example.test/group/profile.git",
    "git@example.test:group/profile.git",
    "ghp_000000000000000000000000000000000000",
    "AKIA0000000000000000",
    _STRIPE_LIKE_PREFIX + "000000000000000000000000",
    "representative-secret",
    "Review (/Users/example/profile), then continue.",
    r"Review [C:\Users\example\profile], then continue.",
    r"Review (\\server\share\profile), then continue.",
    "Review ~example/profiles/example, then continue.",
    "http%3A%2F%2Fexample.test/group/profile.git",
    "https%3a%2f%2fexample.test/group/profile.git",
    "ssh%3A%2F%2Fexample.test/group/profile.git",
    "git%3A%2F%2Fexample.test/group/profile.git",
    "example.test:group/profile.git",
    "The reviewer mutation contains (placeholder-secret).",
    "First line is neutral.\nA later line names /Users/example/profile.",
]


@pytest.mark.parametrize("value", _SENSITIVE_PARSED_VALUES)
def test_public_example_helper_rejects_sensitive_value_shapes(value):
    with pytest.raises(AssertionError):
        _assert_public_example({"description": value})


@pytest.mark.parametrize(
    "value",
    [
        "Ordinary prose can discuss a path or key without containing either value.",
        "provider.linear",
        "example-development",
        "LINEAR_SANDBOX_TOKEN",
    ],
)
def test_public_example_helper_allows_benign_content_values(value):
    _assert_public_example({"description": value})


def test_public_example_helper_scans_decoded_multiline_toml_values():
    parsed = tomllib.loads(
        'description = """First line is neutral.\nA later line names /Users/example/profile.\n"""'
    )

    with pytest.raises(AssertionError):
        _assert_public_example(parsed)


@pytest.mark.parametrize(
    "raw",
    [
        '# workspace_id = "neutral"',
        '# owner-email = "neutral"',
        '# ownerEmail = "neutral"',
        '# apiToken = "neutral"',
        '# "ownerEmail" = "neutral"',
        '# owner.email = "neutral"',
        '# credentials."APIToken" = "neutral"',
    ],
)
def test_public_raw_helper_rejects_commented_sensitive_identifiers(raw):
    with pytest.raises(AssertionError):
        _assert_public_raw_content(raw)


@pytest.mark.parametrize(
    "raw",
    [
        'description = "person@example.test"',
        'description = "/Users/example/profile"',
        'description = "~/profiles/example"',
        r'description = "C:\\Users\\example\\profile"',
        r'description = "\\\\server\\share\\profile"',
        'description = "http://example.test/group/profile.git"',
        'description = "https://example.test/group/profile.git"',
        'description = "ssh://git@example.test/group/profile.git"',
        'description = "git://example.test/group/profile.git"',
        'description = "git@example.test:group/profile.git"',
        'description = "ghp_000000000000000000000000000000000000"',
        'description = "AKIA0000000000000000"',
        f'description = "{_STRIPE_LIKE_PREFIX}000000000000000000000000"',
        'description = "representative-secret"',
        'description = "Review (/Users/example/profile), then continue."',
        'description = "Review ~example/profiles/example, then continue."',
        'description = "https%3A%2F%2Fexample.test/group/profile.git"',
        'description = "example.test:group/profile.git"',
        'description = "The reviewer mutation contains (placeholder-secret)."',
        'description = """First line is neutral.\nA later line names /Users/example/profile.\n"""',
    ],
)
def test_public_raw_helper_rejects_sensitive_value_shapes(raw):
    tomllib.loads(raw)
    with pytest.raises(AssertionError):
        _assert_public_raw_content(raw)


@pytest.mark.parametrize(
    "raw",
    [
        "# Explain which path or key label a reader should choose.",
        'description = "The path and key words are ordinary prose."',
        '# Path and key are prose, not fields.\ndescription = "Neutral guidance"',
        'variable = "LINEAR_SANDBOX_TOKEN"',
        'token_env = "LINEAR_SANDBOX_TOKEN"',
        'description = "provider.linear"',
        'profile_id = "example-development"',
    ],
)
def test_public_raw_helper_allows_benign_prose_and_environment_names(raw):
    tomllib.loads(raw)
    _assert_public_raw_content(raw)


@pytest.mark.parametrize(
    "payload",
    _SENSITIVE_PARSED_VALUES,
)
def test_public_raw_helper_rejects_sensitive_comment_payloads(payload):
    comments = "\n".join(f"# {line}" for line in payload.splitlines())

    with pytest.raises(AssertionError):
        _assert_public_raw_content(f'{comments}\ndescription = "Neutral guidance"\n')


@pytest.mark.parametrize(
    "comment",
    [
        "# Explain which path or key label a reader should choose.",
        "# provider.linear is a provider identifier.",
        "# example-development is a profile identifier.",
        "# LINEAR_SANDBOX_TOKEN is an environment-variable name.",
    ],
)
def test_public_raw_helper_allows_benign_comment_payloads(comment):
    _assert_public_raw_content(f'{comment}\ndescription = "Neutral guidance"\n')


_HANDBOOK_ACTIONS = [
    "git add",
    "git commit",
    "commit",
    "stage",
    "track",
    "check in",
    "check-in",
    "version control",
    "version-control",
]


@pytest.mark.parametrize("action", _HANDBOOK_ACTIONS)
@pytest.mark.parametrize(
    "target", [".env", ".env.local", ".env.* files", "credential value", "credential values"]
)
def test_handbook_helper_rejects_unguarded_protected_actions(action, target):
    with pytest.raises(AssertionError):
        _assert_handbook_safety({"guide": f"Before release, {action}\n{target}."})


@pytest.mark.parametrize(
    "guide",
    [
        "Do not panic but commit .env.",
        "Don't hesitate to commit credential values.",
        "Never commit docs but track .env.",
        "Run git add\n.env before release.",
        "Use check-in\ncredential values.",
        "Do not expose secrets, but track .env.",
        "Do not commit .env unless a developer needs it.",
        "Never commit .env except during setup.",
        "Never commit .env, but you may do so during setup.",
        "Never commit .env, but you can do so during setup.",
        "Never commit .env, but you may safely do so after review.",
        "Never commit .env, but you may commit it during setup.",
        "Run git **add** .env before release.",
        "Run `git add` `.env` before release.",
        "Start committing .env during setup.",
        "Begin staging credential values during setup.",
        "Keep tracking .env during setup.",
        "Use check‑in for .env files.",
        "Use version–control for .env files.",
    ],
)
def test_handbook_helper_rejects_negation_and_contrast_bypasses(guide):
    with pytest.raises(AssertionError):
        _assert_handbook_safety({"guide": guide})


@pytest.mark.parametrize("action", _HANDBOOK_ACTIONS)
@pytest.mark.parametrize(
    "negation",
    [
        "Never",
        "Do not",
        "Don't",
        "Must not",
        "Avoid",
        "Never ever",
        "Do not ever",
        "Don't ever",
        "Must not ever",
        "Avoid ever",
    ],
)
def test_handbook_helper_allows_direct_action_negation(action, negation):
    _assert_handbook_safety({"guide": f"{negation} {action}\ncredential values or .env files."})


@pytest.mark.parametrize(
    "guide",
    [
        "Don’t commit .env.",
        "Do not **commit** .env.",
        "Do not `commit` `.env`.",
        "Never, ever commit .env.",
        "Never commit .env, but store credentials in a keychain.",
    ],
)
def test_handbook_helper_allows_normalized_direct_negation(guide):
    _assert_handbook_safety({"guide": guide})


def test_portable_examples_are_the_only_profiles_in_built_distributions(tmp_path):
    """Catch private assets in either release artifact while validating public profiles."""
    project = Path(__file__).resolve().parents[1]
    subprocess.run(
        [
            "uv",
            "build",
            "--out-dir",
            str(tmp_path),
        ],
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "UV_OFFLINE": "1"},
    )
    wheel = next(tmp_path.glob("ai_dlc-*.whl"))
    source_distribution = next(tmp_path.glob("ai_dlc-*.tar.gz"))
    wheel_profiles = {
        "ai_dlc/assets/profiles/base.toml",
        "ai_dlc/assets/profiles/example/ai-dlc-profile.toml",
        "ai_dlc/assets/profiles/machines/example.toml",
    }
    with zipfile.ZipFile(wheel) as archive:
        members = archive.namelist()
        actual_wheel_profiles = {
            name for name in archive.namelist() if name.startswith("ai_dlc/assets/profiles/")
        }
        assert actual_wheel_profiles == wheel_profiles
        profile_bytes = archive.read("ai_dlc/assets/profiles/example/ai-dlc-profile.toml")
        machine_bytes = archive.read("ai_dlc/assets/profiles/machines/example.toml")

    with tarfile.open(source_distribution) as archive:
        raw_source_members = [member.name for member in archive.getmembers()]
        source_root = raw_source_members[0].split("/", 1)[0]
        members.extend(name.removeprefix(f"{source_root}/") for name in raw_source_members)
        actual_source_profiles = {
            name.removeprefix(f"{source_root}/")
            for name in raw_source_members
            if name.removeprefix(f"{source_root}/").startswith("profiles/")
            and name.endswith(".toml")
        }
        assert actual_source_profiles == {
            "profiles/base.toml",
            "profiles/example/ai-dlc-profile.toml",
            "profiles/machines/example.toml",
        }

    def is_forbidden_member(name: str) -> bool:
        parts = Path(name).parts
        return bool(
            ".git" in parts
            or Path(name).name in {"enrollment.toml", "sean.toml"}
            or Path(name).name.startswith(".env")
            or any(parts[index : index + 2] == (".ai-dlc", "local") for index in range(len(parts)))
        )

    assert not [name for name in members if is_forbidden_member(name)]

    local_user = b"sean" + b"koval"
    forbidden_content = [b"/Users/" + local_user, local_user, str(project).encode()]

    def contains_forbidden_content(content: bytes) -> bool:
        return any(marker in content for marker in forbidden_content)

    with zipfile.ZipFile(wheel) as archive:
        assert not [
            name
            for name in archive.namelist()
            if not name.endswith("/") and contains_forbidden_content(archive.read(name))
        ]
    with tarfile.open(source_distribution) as archive:
        assert not [
            member.name
            for member in archive.getmembers()
            if member.isfile()
            and (content := archive.extractfile(member)) is not None
            and contains_forbidden_content(content.read())
        ]

    profile_raw = profile_bytes.decode()
    machine_raw = machine_bytes.decode()
    _assert_public_example(tomllib.loads(profile_raw))
    _assert_public_example(tomllib.loads(machine_raw))
    _assert_public_raw_content(profile_raw)
    _assert_public_raw_content(machine_raw)
    profile_path = tmp_path / "wheel-profile.toml"
    machine_path = tmp_path / "wheel-machine.toml"
    profile_path.write_bytes(profile_bytes)
    machine_path.write_bytes(machine_bytes)
    resolved = resolve_files(personal=profile_path, machine=machine_path).values
    assert resolved["profile_id"] == "example-development"
    assert credential_status(resolved, environ={})[0]["variable"] == "LINEAR_SANDBOX_TOKEN"


def test_initialized_python_check_does_not_dirty_repository(tmp_path):
    from ai_dlc.project import check_project, setup_project

    root = tmp_path / "python"
    assert adopt(root, "python", apply=True, initialize=True)["status"] == "applied"
    setup_project(root, state_path=tmp_path / "setup.db", use_mise=False)
    git(root, "init")
    git(root, "add", ".")
    git(
        root,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "fixture",
    )

    receipt = check_project(root, use_mise=False)

    assert [item["status"] for item in receipt["outcomes"]] == ["passed", "passed"]
    assert receipt["dirty"] is False
    assert git(root, "status", "--porcelain") == ""


def test_application_symlink_preserved(tmp_path, template):
    root = tmp_path / "app"
    root.mkdir()
    (root / "external").symlink_to(tmp_path / "other")
    assert adopt(root, apply=True, template_source=str(template))["status"] == "applied"
    assert (root / "external").is_symlink()


def test_managed_symlink_is_conflict(tmp_path, template):
    root = tmp_path / "app"
    root.mkdir()
    target = tmp_path / "other"
    target.write_text("outside")
    (root / "managed.txt").symlink_to(target)
    assert adopt(root, apply=True, template_source=str(template))["status"] == "conflict"
    assert target.read_text() == "outside"


def test_runtime_and_ignored_files_are_not_read_or_copied(tmp_path, template, monkeypatch):
    from pathlib import Path

    from ai_dlc import templates

    root = tmp_path / "app"
    adopt(root, apply=True, template_source=str(template), vcs_ref="v1.0.0")
    git(root, "init")
    (root / ".gitignore").write_text("generated-cache/\n")
    excluded = [
        ".venv",
        "node_modules",
        "target",
        ".ai-dlc/local",
        ".pytest_cache",
        "generated-cache",
    ]
    for name in excluded:
        path = root / name / "nested" / "payload.bin"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"cache")
    read = Path.read_bytes

    def guarded_read(path):
        if path.name == "payload.bin":
            pytest.fail("Read excluded runtime file")
        return read(path)

    monkeypatch.setattr(Path, "read_bytes", guarded_read)
    update = templates.copier.run_update

    def guarded_update(stage, **kwargs):
        for name in excluded:
            assert not (stage / name).exists()
        return update(stage, **kwargs)

    monkeypatch.setattr(templates.copier, "run_update", guarded_update)
    release(template, "upstream\nsecond\nthird\n")
    assert sync(root, apply=True)["status"] == "applied"
    for name in excluded:
        assert (root / name / "nested/payload.bin").exists()


def test_checkout_changed_during_stage_requires_retry(tmp_path, template, monkeypatch):
    from ai_dlc import templates

    root = tmp_path / "app"
    root.mkdir()
    application = root / "app.py"
    application.write_text("before")
    copy = templates.copier.run_copy

    def concurrent_edit(*args, **kwargs):
        result = copy(*args, **kwargs)
        application.write_text("concurrent edit")
        return result

    monkeypatch.setattr(templates.copier, "run_copy", concurrent_edit)
    with pytest.raises(ValueError, match="retry"):
        adopt(root, apply=True, template_source=str(template))
    assert application.read_text() == "concurrent edit"
    assert not (root / "managed.txt").exists()


def test_select_role_capabilities(tmp_path):
    import tomllib

    root = tmp_path / "minimal"
    adopt(root, apply=True, capabilities=["specs", "scm"])
    config = tomllib.loads((root / "ai-dlc.toml").read_text())
    assert config["roles"] == {"specs": "openspec", "scm": "github"}
    assert not config.get("providers", {}).get("linear")


def test_unselected_scm_omits_github_workflow(tmp_path):
    root = tmp_path / "minimal"
    adopt(root, apply=True, capabilities=["specs"])
    assert not (root / ".github").exists()


def test_new_upstream_ignore_rule_does_not_delete_application(tmp_path, template):
    root = tmp_path / "app"
    adopt(root, apply=True, template_source=str(template), vcs_ref="v1.0.0")
    (root / "app.py").write_text("valuable application")
    (template / "project/.gitignore").write_text("app.py\n")
    release(template, "upstream\nsecond\nthird\n")
    assert sync(root, apply=True)["status"] == "applied"
    assert (root / "app.py").read_text() == "valuable application"


@pytest.mark.parametrize(
    "preset,manifest,source",
    [
        ("python", "pyproject.toml", "src/main.py"),
        ("node", "package.json", "src/index.js"),
        ("rust", "Cargo.toml", "src/main.rs"),
    ],
)
def test_initialize_starters_and_adoption_preservation(tmp_path, preset, manifest, source):
    import tomllib

    initialized = tmp_path / ("New " + preset)
    adopt(initialized, preset, apply=True, initialize=True)
    config = tomllib.loads((initialized / "ai-dlc.toml").read_text())
    assert (initialized / manifest).exists()
    assert (initialized / source).exists()
    assert config["checks"]["required"] == ["generated", "language-check"]
    assert config["checks"]["commands"]["generated"] == "ai-dlc agents render --check"
    existing = tmp_path / ("existing-" + preset)
    existing.mkdir()
    (existing / manifest).write_text("user-authored manifest")
    assert adopt(existing, preset, apply=True)["status"] == "applied"
    assert (existing / manifest).read_text() == "user-authored manifest"
    assert not (existing / source).exists()
    assert tomllib.loads((existing / "ai-dlc.toml").read_text())["checks"]["required"] == [
        "generated"
    ]


def test_generic_requires_generated_check(tmp_path):
    import tomllib

    adopt(tmp_path, apply=True, initialize=True)
    config = tomllib.loads((tmp_path / "ai-dlc.toml").read_text())
    assert config["checks"]["required"] == ["generated"]
    assert config["setup"]["steps"] == []


@pytest.mark.parametrize(
    "preset,tool,source,lock",
    [
        ("python", "uv", "src/main.py", "uv.lock"),
        ("node", "npm", "src/index.js", "package-lock.json"),
        ("rust", "cargo", "src/main.rs", "Cargo.lock"),
    ],
)
def test_initialized_setup_and_language_check_offline(tmp_path, preset, tool, source, lock):
    import os
    import shutil
    import sys
    import tomllib
    from pathlib import Path

    from ai_dlc.agents import render_agents

    if not shutil.which(tool):
        pytest.skip(f"{tool} unavailable")
    root = tmp_path / preset
    adopt(root, preset, apply=True, initialize=True)
    render_agents(root, apply=True)
    config = tomllib.loads((root / "ai-dlc.toml").read_text())
    env = {
        **os.environ,
        "PATH": str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"],
        "UV_OFFLINE": "1",
        "UV_PYTHON": sys.executable,
        "UV_CACHE_DIR": str(tmp_path / "uv-cache"),
        "npm_config_offline": "true",
        "npm_config_cache": str(tmp_path / "npm-cache"),
        "CARGO_NET_OFFLINE": "true",
    }

    def run(command):
        return subprocess.run(
            command,
            shell=True,
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

    command = config["setup"]["steps"][0]["command"]
    result = run(command)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (root / lock).exists()
    before_lock = (root / lock).read_bytes()
    result = run(command)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (root / lock).read_bytes() == before_lock
    for check in config["checks"]["required"]:
        result = run(config["checks"]["commands"][check])
        assert result.returncode == 0, result.stdout + result.stderr
    (root / source).write_text("this is deliberately invalid syntax !!!\n")
    assert run(config["checks"]["commands"]["language-check"]).returncode != 0
