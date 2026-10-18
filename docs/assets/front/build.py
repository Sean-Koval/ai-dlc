#!/usr/bin/env python3
"""Generate the front page's assets (README.md and docs/index.md) by running the real CLI.

Writes, next to this script:

- ``enroll.cast`` / ``enroll.svg``: ``ai-dlc machine enroll`` (preview, apply, status) against a
  throwaway profile repository, as an asciicast v2 recording and an animated terminal (CSS
  keyframes, loops; no player needed on GitHub or the docs site);
- ``work.cast`` / ``work.svg``: ``work new -> publish -> start -> pr -> project check -> finish`` in
  a fresh ``ai-dlc project init`` repository. GitHub is replaced by ``demo_provider.py``, a local
  stand-in that speaks the executable provider contract, so the finish gates evaluate a real
  local merge and the receipt ``project check`` wrote;
- ``plugin-skills.svg``: the workflow plugin's skills as Claude Code lists them
  (``claude --plugin-dir plugins/ai-dlc-workflow plugin details ai-dlc-workflow``);
- ``project-check.svg``: ``ai-dlc project check --required`` in the demo repository;
- ``suite.svg`` (Airframe tokens, theme-aware when inlined) and ``suite-dark.svg`` /
  ``suite-light.svg`` (the same drawing with each flavor's colors resolved, for ``<picture>``).

The terminals follow Airframe's Terminal component and the diagram's fallbacks are Airframe's Night
values, both read from the vendored ``docs/stylesheets/airframe-tokens.json``, since an SVG shown as
an image cannot load the site's stylesheet.

Everything is byte-reproducible for a given checkout: the demo runs in a fixed directory with
fixed Git identities and dates, and machine paths are shown as ``~``. CI re-runs this and fails on
a diff (.github/workflows/assets.yml).

    uv run --locked --no-sync python docs/assets/front/build.py [--check]

Needs git, jq, mise (the bootstrap provides it) and, for the plugin screen, the Claude Code CLI
at CLAUDE_CODE_VERSION; ``--skip-claude`` keeps the committed plugin screen.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DEMO = Path("/tmp/ai-dlc-front-demo")
CLAUDE_CODE_VERSION = "2.1.302"
COLS = 92
GIT_ENV = {
    "GIT_AUTHOR_NAME": "Dev A",
    "GIT_AUTHOR_EMAIL": "dev-a@example.com",
    "GIT_COMMITTER_NAME": "Dev A",
    "GIT_COMMITTER_EMAIL": "dev-a@example.com",
    "GIT_AUTHOR_DATE": "2026-10-20T09:00:00+00:00",
    "GIT_COMMITTER_DATE": "2026-10-20T09:00:00+00:00",
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_NOSYSTEM": "1",
}

ENROLL = [
    "ai-dlc machine enroll ~/profile --profile-id example-development --machine-id laptop \\\n"
    "  | jq -c '{applied, modules, credentials: [.credentials[].id]}'",
    "ai-dlc machine enroll ~/profile --profile-id example-development --machine-id laptop --apply \\\n"
    "  | jq -c '{applied, machine: .machine.path}'",
    "ai-dlc machine status \\\n  | jq -c '{enrolled, profile: .profile.id, commit: .profile.resolved_commit[:12], drift}'",
]
WORK = [
    'ai-dlc work new fix-receipts --title "Retry receipt downloads" \\\n'
    '  --scope "Retry one failed receipt download" --no-requires-spec \\\n'
    '  --spec-reason "Bug fix with a regression test" \\\n'
    '  --acceptance "A transient download failure retries once" | jq -c \'{id, reviewed}\'',
    "sed -i 's/^reviewed = false/reviewed = true/' .ai-dlc/work/fix-receipts.toml  # reviewed",
    "ai-dlc work publish fix-receipts | jq -c '{status, issue: .tracker.url}'",
    "ai-dlc work start fix-receipts | jq -c '{status, branch, issue: .tracker.state}'",
    "echo 'RETRIES = 1' > src/receipts.py && git commit -qam 'fix: retry receipt downloads'",
    "ai-dlc work pr fix-receipts | jq -c '{status, pr: .pr.url}'",
    "git checkout -q main && git merge -q --no-ff work/fix-receipts -m 'Merge #43'  # PR merged",
    "ai-dlc project check --required --receipt .ai-dlc/local/receipt.json \\\n"
    "  | jq -c '[.outcomes[] | \"\\(.id): \\(.status)\"]'",
    "ai-dlc work finish fix-receipts \\\n  | jq -c '{status, issue: .tracker.state, gates: (.evidence | keys | join(\", \"))}'",
]


def esc(s: str) -> str:
    return html.escape(s, quote=True)


# ------------------------------------------------------------------------------------------ the demo
def environment() -> dict[str, str]:
    """PATH with this checkout's ai-dlc first and mise available, an isolated HOME, fixed Git."""
    home = DEMO / "home"
    tools = DEMO / "bin"
    tools.mkdir(parents=True, exist_ok=True)
    mise = shutil.which("mise") or str(Path.home() / ".local/share/ai-dlc/bootstrap/bin/mise")
    if not Path(mise).is_file():
        sys.exit("build: mise is required (run scripts/bootstrap.sh --source)")
    (tools / "mise").symlink_to(mise)
    path = [str(Path(sys.executable).parent), str(tools), *os.environ.get("PATH", "").split(os.pathsep)]
    keep = {k: os.environ[k] for k in ("LANG", "TERM", "SSL_CERT_FILE", "UV_CACHE_DIR") if k in os.environ}
    return {
        **keep,
        **GIT_ENV,
        "PATH": os.pathsep.join(path),
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "XDG_STATE_HOME": str(home / ".local/state"),
        "XDG_CACHE_HOME": str(home / ".cache"),
        "MISE_DATA_DIR": str(Path.home() / ".local/share/mise"),
        "NO_COLOR": "1",
        "COLUMNS": str(COLS),
    }


def sh(command: str, cwd: Path, env: dict[str, str], check: bool = True) -> str:
    res = subprocess.run(["bash", "-c", command], cwd=cwd, env=env, capture_output=True, text=True)
    if check and res.returncode:
        sys.exit(f"build: `{command}` failed ({res.returncode}):\n{res.stdout}{res.stderr}")
    return res.stdout


def tidy(text: str) -> str:
    return text.replace(str(DEMO / "home"), "~").replace(str(DEMO), "/tmp/demo").rstrip("\n")


def prepare(env: dict[str, str]) -> None:
    """A profile repository and a freshly initialized project wired to the local GitHub stand-in."""
    home = Path(env["HOME"])
    profile = home / "profile"
    profile.mkdir(parents=True)
    shutil.copy(ROOT / "profiles/example/ai-dlc-profile.toml", profile)
    sh("git init -q -b main && git add -A && git commit -qm 'example profile'", profile, env)
    sh("ai-dlc project init app > /dev/null", home, env)
    app = home / "app"
    provider = app / ".ai-dlc/local/demo_provider.py"
    provider.parent.mkdir(parents=True)
    shutil.copy(HERE / "demo_provider.py", provider)
    provider.chmod(0o755)
    digest = sh(f"sha256sum {provider}", app, env).split()[0]
    config = (app / "ai-dlc.toml").read_text()
    config = config.replace('tracker = "github-issues"', 'tracker = "demo-github"')
    config = config.replace('scm = "github"', 'scm = "demo-github"')
    config = re.sub(
        r'\[providers\.github-issues\]\n\nkind = "github-issues"\n',
        '[providers.demo-github]  # local stand-in for GitHub (docs/assets/front/demo_provider.py)\n'
        f'kind = "executable"\ncommand = "{provider}"\nsha256 = "{digest}"\n'
        'operations = ["capabilities"]\n',
        config,
    )
    (app / "ai-dlc.toml").write_text(config)
    (app / "src").mkdir()
    (app / "src/receipts.py").write_text("RETRIES = 0\n")
    sh("ai-dlc agents render --apply > /dev/null && git init -q -b main && git add -A "
       "&& git commit -qm 'Initialize with ai-dlc project init'", app, env)


def session(commands: list[str], cwd: Path, env: dict[str, str]) -> list[tuple[str, str]]:
    return [(cmd, tidy(sh(cmd, cwd, env))) for cmd in commands]


def screens(env: dict[str, str], skip_claude: bool) -> dict[str, tuple[str, str]]:
    app = Path(env["HOME"]) / "app"
    check = ("ai-dlc project check --required \\\n"
             "  | jq '{required, dirty, outcomes: [.outcomes[] | {id, status, exit_code}]}'")
    out = {"project-check.svg": (check, tidy(sh(check, app, env)))}
    if not skip_claude:
        claude = shutil.which("claude", path=env["PATH"])
        if claude is None:
            sys.exit(f"build: the Claude Code CLI {CLAUDE_CODE_VERSION} is required (or pass --skip-claude)")
        version = sh(f"{claude} --version", ROOT, env).split()[0]
        if version != CLAUDE_CODE_VERSION:
            sys.exit(f"build: Claude Code {CLAUDE_CODE_VERSION} is required, found {version}")
        cmd = "claude --plugin-dir plugins/ai-dlc-workflow plugin details ai-dlc-workflow"
        text = sh(cmd.replace("claude", claude, 1), ROOT, env)
        text = text.split("\nProjected token cost")[0]  # the inventory; costs are estimates
        out["plugin-skills.svg"] = (cmd, tidy(text))
    return out


# ------------------------------------------------------------------------------------------ recordings
def wrap(text: str) -> list[str]:
    lines = []
    for line in text.splitlines() or [""]:
        while len(line) > COLS:
            cut = line.rfind(" ", 0, COLS)
            cut = cut if cut > COLS // 2 else COLS
            lines.append(line[:cut])
            line = "    " + line[cut:].lstrip()
        lines.append(line)
    return lines


TYPE, TYPE_MAX, PAUSE, LINE = 0.03, 1.8, 0.6, 0.08  # seconds; long commands type faster


def speed(cmd: str) -> float:
    """Seconds per typed character, so no command takes longer than TYPE_MAX to type."""
    return min(TYPE, TYPE_MAX / max(1, len(cmd)))


def timeline(
    steps: list[tuple[str, str]], gap: float
) -> tuple[list[tuple[float, str, str, float]], float]:
    """Screen lines as (time shown, kind, text): `cmd` lines type out from that time; `out` lines appear."""
    t, lines = 0.5, []
    for cmd, output in steps:
        per = speed(cmd)
        for i, part in enumerate(cmd.split("\n")):
            lines.append((t, "cmd" if i == 0 else "cont", part, per))
            t += len(part) * per
        t += PAUSE
        for line in wrap(output) if output else []:
            lines.append((t, "out", line, 0.0))
            t += LINE
        t += gap
    lines.append((t, "cmd", "", 0.0))
    return lines, t + 3.0


def cast(steps: list[tuple[str, str]], title: str, gap: float) -> str:
    """asciicast v2 (https://docs.asciinema.org/manual/asciicast/v2/) with fixed timings."""
    head = {"version": 2, "width": COLS + 4, "height": 40, "title": title,
            "env": {"SHELL": "/bin/bash", "TERM": "xterm-256color"}}
    events, t = [], 0.5
    for cmd, output in steps:
        events.append([round(t, 3), "o", "$ "])
        per = speed(cmd)
        for ch in cmd:
            t += per
            events.append([round(t, 3), "o", "\r\n> " if ch == "\n" else ch])
        t += PAUSE
        events.append([round(t, 3), "o", "\r\n" + (output.replace("\n", "\r\n") + "\r\n" if output else "")])
        t += gap
    events.append([round(t, 3), "o", "$ "])
    return "\n".join(json.dumps(x, ensure_ascii=False) for x in [head, *events]) + "\n"


CW, LH, PAD, BAR = 7.8, 17.0, 18, 34  # char width (0.6em at 13px), line height, padding, title bar
MONO = "'DM Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
LIT = re.compile(r'"(failed|denied)"')  # the lines a terminal may color: the failed role, never green for good
TERM_ICON = ('<g fill="none" stroke-width="1.5" stroke-linecap="square" stroke-linejoin="miter" '
             'transform="translate({x},{y}) scale(.7)"><rect x="2.5" y="3.5" width="15" height="13"/>'
             '<path d="M6 8l2.5 2L6 12M10.5 12.5H14"/></g>')  # Airframe's `terminal` icon, 20px grid drawn at 14px


def terminal(lines: list[tuple[float, str, str, float]], total: float | None, title: str) -> str:
    """A terminal window on Airframe's Terminal contract: always dark, DM Mono on `terminal-bg`, a bar
    with the product and scope in mono capitals, output in `terminal-fg`, the prompt and cursor in
    `brand`, and color on one kind of line only (`terminal-err` for the failed role). The bar reads
    `title` as `product|scope|scope`. With `total`, lines appear at their times and commands type out,
    looping every `total` seconds; without it, a still of every line."""
    t = night()
    w, h = round((COLS + 4) * CW + 2 * PAD), round(BAR + PAD + len(lines) * LH + PAD / 2)
    css = [f".t{{font:13px {MONO};fill:{t['terminal-fg']};white-space:pre}}.p{{fill:{t['brand']}}}"
           f".c{{fill:{t['code-keyword']}}}.x{{fill:{t['terminal-err']}}}"
           f".b{{font:500 10.5px {MONO};letter-spacing:.08em;fill:{t['terminal-dim']}}}.b1{{fill:{t['terminal-fg']}}}"]
    body = [f'<rect width="{w}" height="{h}" rx="4" fill="{t["terminal-bg"]}"/>',
            f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="4" fill="none" stroke="{t["terminal-fg"]}" '
            f'stroke-opacity=".08"/><path d="M0 {BAR + .5}H{w}" stroke="{t["terminal-fg"]}" stroke-opacity=".09"/>',
            TERM_ICON.format(x=14, y=BAR / 2 - 7).replace("<g ", f'<g stroke="{t["terminal-dim"]}" ', 1)]
    x = 14 + 14 + 14  # icon, gap
    for i, part in enumerate(title.split("|")):
        body.append(f'<text class="b{" b1" if i == 0 else ""}" x="{x}" y="{BAR / 2 + 3.75}">{esc(part.upper())}</text>')
        x += round(len(part) * (10.5 * 0.6 + 0.84)) + 14
    for i, (at, kind, text, per) in enumerate(lines):
        y = BAR + PAD + (i + 0.75) * LH
        if kind in ("cmd", "cont"):
            prompt = "$ " if kind == "cmd" else "> "
            inner = (f'<tspan class="p">{prompt}</tspan><tspan class="c">{esc(text)}</tspan>' if text
                     else f'<tspan class="p">{prompt}▌</tspan>')
            n = len(text)
            attrs = f' textLength="{(n + 2) * CW:.1f}" lengthAdjust="spacingAndGlyphs"' if text else ""
            el = f'<text class="t" x="{PAD}" y="{y:.1f}"{attrs}>{inner}</text>'
            if total and text:  # a cover over the command that steps right one character at a time
                x0, d = PAD + 2 * CW, n * per
                css.append(f"@keyframes y{i}{{0%,{100 * at / total:.3f}%{{transform:translateX(0)}}"
                           f"{100 * (at + d) / total:.3f}%,100%{{transform:translateX({n * CW:.1f}px)}}}}"
                           f".y{i}{{animation:y{i} {total:.2f}s steps({n},end) infinite}}")
                el += (f'<rect class="y{i}" x="{x0:.1f}" y="{y - LH * 0.8:.1f}" width="{n * CW + 4:.1f}" '
                       f'height="{LH:.1f}" fill="{t["terminal-bg"]}"/>')
        else:  # normal stays quiet; a failed or denied status is the only red
            el = f'<text class="t{" x" if LIT.search(text) else ""}" x="{PAD}" y="{y:.1f}">{esc(text)}</text>'
        if total:
            css.append(f"@keyframes s{i}{{0%,{100 * at / total:.3f}%{{opacity:0}}"
                       f"{100 * at / total + 0.001:.3f}%,100%{{opacity:1}}}}"
                       f".s{i}{{animation:s{i} {total:.2f}s step-end infinite}}")
            el = f'<g class="s{i}">{el}</g>'
        body.append(el)
    label = title.replace("|", ", ")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img" aria-label="{esc(label)}"><style>{"".join(css)}</style>{"".join(body)}</svg>\n')


def still(command: str, output: str, title: str) -> str:
    parts = command.split("\n")
    lines = [(0.0, "cmd" if i == 0 else "cont", p, 0.0) for i, p in enumerate(parts)]
    lines += [(0.0, "out", x, 0.0) for x in wrap(output)]
    return terminal(lines, None, title)


# ------------------------------------------------------------------------------------------ the diagram
TOKENS = ("canvas", "surface", "raised", "line", "line-strong", "rule", "fg", "fg-muted", "fg-subtle",
          "brand-line", "product-aidlc", "product-hangar", "product-flightdeck", "product-tower")


def night() -> dict[str, str]:
    """Every Night token value, from the vendored Airframe tokens (`scripts/sync-airframe.sh`)."""
    return json.loads((ROOT / "docs/stylesheets/airframe-tokens.json").read_text())["themes"]["dark"]


def flavors() -> dict[str, dict[str, str]]:
    """Token values for the dark and light flavors, from the vendored Airframe tokens (theme-v2 and later)."""
    themes = json.loads((ROOT / "docs/stylesheets/airframe-tokens.json").read_text())["themes"]
    return {flavor: {t: themes[flavor][t] for t in TOKENS} for flavor in ("dark", "light")}


def diagram(colors: dict[str, str] | None) -> str:
    """Where ai-dlc sits in the suite (agent-factory's diagram conventions: Airframe tokens with dark
    fallbacks; with `colors`, every token resolved to that flavor)."""
    dark = flavors()["dark"]

    def v(token: str) -> str:
        return colors[token] if colors else f"var(--af-{token}, {dark[token]})"

    style = (f".ad .n{{font:700 17px Archivo,'Helvetica Neue',Arial,sans-serif;font-stretch:125%;fill:{v('fg')}}}"
             f".ad .s{{font:700 13px Archivo,'Helvetica Neue',Arial,sans-serif;font-stretch:125%;fill:{v('fg')}}}"
             f".ad .b{{font:400 12.5px 'Red Hat Text','Helvetica Neue',Arial,sans-serif;fill:{v('fg-muted')}}}"
             f".ad .e{{font:400 12.5px 'Red Hat Text','Helvetica Neue',Arial,sans-serif;fill:{v('fg-subtle')}}}"
             f".ad .l{{font:500 10.5px 'DM Mono',ui-monospace,Menlo,monospace;letter-spacing:.08em;"
             f"fill:{v('fg-subtle')}}}.ad .edge{{fill:none;stroke:{v('fg-subtle')};stroke-width:1.25}}"
             f".ad .plan{{fill:none;stroke:{v('fg-subtle')};stroke-width:1.25;stroke-dasharray:5 4}}")
    out: list[str] = []

    def box(x: int, y: int, w: int, h: int, eyebrow: str, name: str, lines: tuple[str, ...],
            hue: str | None, kind: str = "raised") -> None:
        stroke = {"hub": f' stroke="{v("brand-line")}" stroke-width="1.5"',
                  "plan": f' stroke="{v("line-strong")}" stroke-dasharray="4 4" fill-opacity="0"'}.get(
            kind, f' stroke="{v("rule")}"')
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" fill="{v("raised")}"{stroke}/>')
        if hue:
            out.append(f'<rect x="{x}" y="{y}" width="{w}" height="2" fill="{v(hue)}"/>')
        out.append(f'<text class="l" x="{x + 18}" y="{y + 26}">{esc(eyebrow)}</text>'
                   f'<text class="n" x="{x + 18}" y="{y + 50}">{esc(name)}</text>')
        out.extend(f'<text class="b" x="{x + 18}" y="{y + 74 + 19 * i}">{esc(t)}</text>'
                   for i, t in enumerate(lines))

    def step(x: int, y: int, name: str, sub: str) -> None:
        out.append(f'<rect x="{x}" y="{y}" width="320" height="52" rx="3" fill="{v("surface")}" '
                   f'stroke="{v("line-strong")}"/><text class="s" x="{x + 14}" y="{y + 21}">{esc(name)}</text>'
                   f'<text class="b" x="{x + 14}" y="{y + 40}">{esc(sub)}</text>')

    def edge(d: str, label: str, lx: int, ly: int, cls: str = "edge", anchor: str = "middle") -> None:
        out.append(f'<path class="{cls}" d="{d}" marker-end="url(#ad-arrow)"/>')
        out.extend(f'<text class="e" x="{lx}" y="{ly + 16 * i}" text-anchor="{anchor}">{esc(t)}</text>'
                   for i, t in enumerate(label.split("|")))

    w, h = 1200, 620
    out.append(f'<rect width="{w}" height="{h}" fill="{v("canvas")}"/>')
    out.append('<text class="l" x="40" y="44">WHERE AI-DLC SITS · THE DEVELOPER SIDE OF THE AGENT FACTORY</text>')
    box(30, 80, 380, 400, "DEVELOPER MACHINE · LOCAL", "ai-dlc", (), "product-aidlc", "hub")
    for i, (name, sub) in enumerate((("machine enroll", "a pinned profile: tools, clients, credentials"),
                                     ("work new → start", "reviewed record, tracker issue, branch"),
                                     ("work pr → project check", "one PR; checks write a receipt"),
                                     ("work finish", "merged PR + CI receipt, then close"))):
        step(60, 140 + 78 * i, name, sub)
        if i:
            out.append(f'<path class="edge" d="M220 {140 + 78 * i - 26} V{140 + 78 * i - 2}" '
                       'marker-end="url(#ad-arrow)"/>')
    box(500, 80, 300, 170, "TEAM HARNESS REPO", "harness.lock", ("pins the ai-dlc workflow plugin", "(skills, guide, safe hooks)",
                                                                  "off in stable, on in candidate"), None)
    box(890, 80, 280, 170, "RUN", "hangar", ("runs coding agents in sandboxes", "renders the harness at claim",
                                              "time; owns verify and landing"), "product-hangar")
    box(890, 310, 280, 170, "JUDGE", "flightdeck", ("A/B: with and without the", "plugin, same tasks; a verdict",
                                                     "on the pull request"), "product-flightdeck")
    box(500, 310, 300, 170, "SOURCE OF TRUTH", "GitHub", ("issues, pull requests,", "CI receipts per merge commit",
                                                         "decisions in docs/decisions/"), None)
    edge("M410 180 H496", "publish|plugin", 453, 160)
    edge("M800 165 H886", "pinned|plugin", 843, 145)
    edge("M1030 250 V306", "trials,|traces", 1040, 276, anchor="start")
    edge("M410 400 H496", "issue, PR,|receipt", 453, 380)
    edge("M800 395 H886", "report", 843, 385)
    box(30, 520, 1140, 70, "GOVERN · PLANNED", "Tower: policy decisions, approvals, receipts", (),
        "product-tower", "plan")
    defs = (f'<defs><marker id="ad-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
            f'markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="{v("fg-subtle")}"/>'
            "</marker></defs>")
    return (f'<svg class="ad" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            'role="img" aria-label="Where ai-dlc sits: it prepares developer machines and gates work on '
            'merged evidence; it publishes the workflow plugin that a team harness pins, hangar runs and '
            f'flightdeck compares">'
            f"<style>{style}</style>{defs}{''.join(out)}</svg>\n")


# ------------------------------------------------------------------------------------------ main
def build(skip_claude: bool) -> dict[str, str]:
    if DEMO.exists():
        shutil.rmtree(DEMO)
    env = environment()
    try:
        prepare(env)
        home = Path(env["HOME"])
        enroll = session(ENROLL, home, env)
        work = session(WORK, home / "app", env)
        shots = screens(env, skip_claude)
    finally:
        shutil.rmtree(DEMO, ignore_errors=True)
    files: dict[str, str] = {}
    for name, steps, title, bar, gap in (  # the cast's title, and the terminal bar as product|scope
        ("enroll", enroll, "ai-dlc machine enroll", "ai-dlc|machine enroll|preview, apply, status", 4.4),
        ("work", work, "ai-dlc work: new → start → pr → finish (GitHub stood in locally)",
         "ai-dlc|work: new → start → pr → finish|GitHub stood in locally", 1.7),
    ):
        lines, total = timeline(steps, gap)
        files[f"{name}.cast"] = cast(steps, title, gap)
        files[f"{name}.svg"] = terminal(lines, total, bar)
    titles = {"project-check.svg": "ai-dlc|project check --required",
              "plugin-skills.svg": "Claude Code|the ai-dlc workflow plugin"}
    for name, (cmd, text) in shots.items():
        files[name] = still(cmd, text, titles[name])
    files["suite.svg"] = diagram(None)
    for flavor, colors in flavors().items():
        files[f"suite-{flavor}.svg"] = diagram(colors)
    return files


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="Fail when a committed asset differs.")
    ap.add_argument("--skip-claude", action="store_true", help="Keep the committed plugin screen.")
    args = ap.parse_args(argv)
    files = build(args.skip_claude)
    stale = [n for n, text in files.items() if not (HERE / n).is_file() or (HERE / n).read_text() != text]
    if args.check:
        for name in stale:
            print(f"build: {name} is stale", file=sys.stderr)
        return 1 if stale else 0
    for name in stale:
        (HERE / name).write_text(files[name])
        print("build: wrote", name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
