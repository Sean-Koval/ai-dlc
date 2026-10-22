#!/usr/bin/env python3
"""Generate the front page's assets (README.md and docs/index.md) by running the real CLI.

Writes, next to this script:

- ``enroll.cast`` / ``enroll.svg``: ``ai-dlc machine enroll`` (preview, apply, status) against a
  throwaway profile repository, as an asciicast v2 recording and an animated terminal (CSS
  keyframes; opens on the finished session for OPEN seconds, as flightdeck's recording does, then
  replays once in under 20 seconds and holds its last frame, which is also what shows when
  animations do not run; no player needed on GitHub or the docs site);
- ``work.cast`` / ``work.svg``: ``work start -> pr -> finish (refused: the PR is not merged) ->
  merge -> finish (closes the issue)`` in a fresh ``ai-dlc project init`` repository whose work
  record was reviewed and published off camera. GitHub and its CI are replaced by
  ``demo_provider.py``, a local stand-in that speaks the executable provider contract, so the
  finish gates evaluate a real local merge and the receipt ``project check`` wrote;
- ``plugin-skills.svg``: the workflow plugin's skills as Claude Code lists them
  (``claude --plugin-dir plugins/ai-dlc-workflow plugin details ai-dlc-workflow``);
- ``project-check.svg``: ``ai-dlc project check --required`` in the demo repository;
- ``suite.svg`` (Airframe tokens, theme-aware when inlined) and ``suite-dark.svg`` /
  ``suite-light.svg`` (the same drawing with each flavor's colors resolved, for ``<picture>``),
  800 by 520 so its text stays readable in the docs column.

The terminals follow Airframe's Terminal component and the diagram's fallbacks are Airframe's Night
values, both read from the vendored ``docs/stylesheets/airframe-tokens.json``, since an SVG shown as
an image cannot load the site's stylesheet. Output is shown as the CLI prints it, 80 columns wide,
in a window of ROWS lines that scrolls like a terminal.

Everything is byte-reproducible for a given checkout: the demo runs in a fixed directory with
fixed Git identities and dates, and machine paths are shown as ``~``. CI re-runs this and fails on
a diff (.github/workflows/assets.yml).

    uv run --locked --no-sync python docs/assets/front/build.py [--check]
    uv run --locked --no-sync --with playwright==1.56.0 python docs/assets/front/build.py --clip

``--clip`` records only ``clip.mp4`` and ``clip-poster.png``: the quickstart's five steps in a fresh
project, ending on ``project check --required`` passing, at 2x and 680 px, as tall as its content (Playwright's Chromium and
ffmpeg). An MP4 is not byte-reproducible, so ``--check`` does not compare it.

Needs git, jq (the project-check still drops its timings), mise (the bootstrap provides it) and, for the plugin screen, the Claude Code CLI
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
COLS = 80
ROWS = 22  # the terminal window's height in lines; longer sessions scroll
MAX_SECONDS = 20.0  # a recording replays once, within this, then holds its last frame
PHONE_COLS = 40  # a phone still: 44 columns with the window's margin, 13 px text in a 360 px column
OPEN = 4.0  # seconds the finished session shows first, so a reader sees the outcome before the replay
GIT_ENV = {
    "GIT_AUTHOR_NAME": "Dev A",
    "GIT_AUTHOR_EMAIL": "dev-a@example.com",
    "GIT_COMMITTER_NAME": "Dev A",
    "GIT_COMMITTER_EMAIL": "dev-a@example.com",
    "GIT_AUTHOR_DATE": "2026-10-20T09:00:00+00:00",
    "GIT_COMMITTER_DATE": "2026-10-20T09:00:00+00:00",
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_MERGE_AUTOEDIT": "no",
}

ENROLL = [
    "ai-dlc machine enroll ~/profile --profile-id example-development \\\n  --machine-id laptop",
    "ai-dlc machine enroll ~/profile --profile-id example-development \\\n  --machine-id laptop --apply",
    "ai-dlc machine status",
]
WORK = [  # the record was reviewed and published off camera (issue 42); see prepare()
    "ai-dlc work start fix-receipts",
    "echo 'RETRIES = 1' > src/receipts.py && git commit -qam 'fix: retry receipt downloads'",
    "ai-dlc work pr fix-receipts",
    "ai-dlc work finish fix-receipts  # refused: the PR is not merged",
    "git switch -q main && git merge -q --no-ff work/fix-receipts  # the PR merges",
    "ai-dlc work finish fix-receipts",
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
    # The answers file records where the engine's templates were read from. That is this
    # checkout's absolute path, which would make every commit sha in the recording depend on
    # where the engine was cloned; the demo names the canonical repository instead.
    answers = app / ".copier-answers.yml"
    answers.write_text(re.sub(r"^_src_path: .*$", "_src_path: https://github.com/Sean-Koval/ai-dlc.git",
                              answers.read_text(), count=1, flags=re.MULTILINE))
    sh("ai-dlc agents render --apply > /dev/null && git init -q -b main && git add -A "
       "&& git commit -qm 'Initialize with ai-dlc project init'", app, env)
    # One piece of work, reviewed by a person and published as issue 42, so the recording can
    # start at `work start`.
    sh('ai-dlc work new fix-receipts --title "Retry receipt downloads" '
       '--scope "Retry one failed receipt download" --no-requires-spec '
       '--spec-reason "Bug fix with a regression test" '
       '--acceptance "A transient download failure retries once" > /dev/null', app, env)
    sh("sed -i 's/^reviewed = false/reviewed = true/' .ai-dlc/work/fix-receipts.toml "
       "&& ai-dlc work publish fix-receipts > /dev/null", app, env)


def session(commands: list[str], cwd: Path, env: dict[str, str]) -> list[tuple[str, str]]:
    """Run each command and keep what it printed; a refusal (non-zero exit) is part of the story."""
    return [(cmd, tidy(sh(cmd, cwd, env, check=False))) for cmd in commands]


def screens(env: dict[str, str], skip_claude: bool) -> dict[str, tuple[str, str]]:
    app = Path(env["HOME"]) / "app"
    check = ("ai-dlc project check --required \\\n"
             "  | jq '{required, dirty, outcomes: [.outcomes[] | {id, status, exit_code}]}'  # no timings")
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
def wrap(text: str, cols: int = COLS) -> list[str]:
    """Lines at most `cols` wide, broken at a space (never inside a word or a hash) and indented."""
    lines = []
    for line in text.splitlines() or [""]:
        while len(line) > cols:
            indent = len(line) - len(line.lstrip())
            cut = line.rfind(" ", indent, cols + 1)
            cut = cut if cut > indent else cols
            lines.append(line[:cut].rstrip())
            line = " " * (indent + 4) + line[cut:].lstrip()
        lines.append(line)
    return lines


TYPE, TYPE_MAX, PAUSE, LINE, HOLD = 0.03, 1.0, 0.4, 0.04, 2.0  # seconds; long commands type faster


def speed(cmd: str) -> float:
    """Seconds per typed character, so no command takes longer than TYPE_MAX to type."""
    return min(TYPE, TYPE_MAX / max(1, len(cmd)))


def timeline(
    steps: list[tuple[str, str]], gap: float
) -> tuple[list[tuple[float, str, str, float]], float]:
    """Screen lines as (time shown, kind, text, seconds per character): `cmd` lines type out from
    that time; `out` lines appear. The total is the play time, within MAX_SECONDS."""
    t, lines = 0.3, []
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
    total = t + HOLD
    if total > MAX_SECONDS:
        sys.exit(f"build: a recording of {len(lines)} lines plays for {total:.1f}s, over {MAX_SECONDS:.0f}s")
    return lines, total


def cast(steps: list[tuple[str, str]], title: str, gap: float) -> str:
    """asciicast v2 (https://docs.asciinema.org/manual/asciicast/v2/) with the SVG's timings."""
    head = {"version": 2, "width": COLS + 4, "height": ROWS, "title": title,
            "env": {"SHELL": "/bin/bash", "TERM": "xterm-256color"}}
    events, t = [], 0.3
    for cmd, output in steps:
        events.append([round(t, 3), "o", "$ "])
        per = speed(cmd)
        for ch in cmd:
            t += per
            events.append([round(t, 3), "o", "\r\n> " if ch == "\n" else ch])
        t += PAUSE
        events.append([round(t, 3), "o", "\r\n"])
        for line in wrap(output) if output else []:
            events.append([round(t, 3), "o", line + "\r\n"])
            t += LINE
        t += gap
    events.append([round(t, 3), "o", "$ "])
    return "\n".join(json.dumps(x, ensure_ascii=False) for x in [head, *events]) + "\n"


CW, LH, PAD, BAR = 7.8, 17.0, 18, 34  # char width (0.6em at 13px), line height, padding, title bar
MONO = "'DM Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
LIT = re.compile(r':\s*"(failed|denied|blocked)"')  # the lines a terminal may color: a failed status, never green for good
TERM_ICON = ('<g fill="none" stroke-width="1.5" stroke-linecap="square" stroke-linejoin="miter" '
             'transform="translate({x},{y}) scale(.7)"><rect x="2.5" y="3.5" width="15" height="13"/>'
             '<path d="M6 8l2.5 2L6 12M10.5 12.5H14"/></g>')  # Airframe's `terminal` icon, 20px grid drawn at 14px


def pct(at: float, total: float) -> str:
    return f"{100 * at / total:.3f}%"


def terminal(lines: list[tuple[float, str, str, float]], total: float | None, title: str, cols: int = COLS) -> str:
    """A terminal window on Airframe's Terminal contract: always dark, DM Mono on `terminal-bg`, a bar
    with the product and scope in mono capitals, output in `terminal-fg`, the prompt and cursor in
    `brand`, and color on one kind of line only (`terminal-err` for the failed role). The bar reads
    `title` as `product|scope|scope`. With `total`, the window is ROWS lines high and opens on the
    finished session for OPEN seconds; then lines appear at their times, commands type out and the
    window scrolls like a terminal; it replays once and holds its last frame, which is also the frame
    shown when animations do not run (the markup's resting state is the end of the session). Without
    `total`, a still of every line. `cols` sets the width (a phone still is PHONE_COLS)."""
    t = night()
    rows = min(len(lines), ROWS) if total else len(lines)
    start = ""
    if total:  # every moment moves OPEN seconds later; until then the finished session shows
        lines = [(at + OPEN, kind, text, per) for at, kind, text, per in lines]
        total += OPEN
        start = pct(OPEN, total)
    w, h = round((cols + 4) * CW + 2 * PAD), round(BAR + PAD + rows * LH + PAD / 2)
    css = [f".t{{font:13px {MONO};fill:{t['terminal-fg']};white-space:pre}}.p{{fill:{t['brand']}}}"
           f".c{{fill:{t['code-keyword']}}}.x{{fill:{t['terminal-err']}}}"
           f".b{{font:500 10.5px {MONO};letter-spacing:.08em;fill:{t['terminal-dim']}}}.b1{{fill:{t['terminal-fg']}}}"
           "@media(prefers-reduced-motion:reduce){.v,.v *{animation:none!important}}"]
    r = px(t["radius-card"])  # Terminal takes the card radius
    body = [f'<rect width="{w}" height="{h}" rx="{r}" fill="{t["terminal-bg"]}"/>',
            f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="{r - .5}" fill="none" stroke="{t["terminal-fg"]}" '
            f'stroke-opacity=".08"/><path d="M0 {BAR + .5}H{w}" stroke="{t["terminal-fg"]}" stroke-opacity=".09"/>',
            TERM_ICON.format(x=14, y=BAR / 2 - 7).replace("<g ", f'<g stroke="{t["terminal-dim"]}" ', 1)]
    x = 14 + 14 + 14  # icon, gap
    for i, part in enumerate(title.split("|")):
        body.append(f'<text class="b{" b1" if i == 0 else ""}" x="{x}" y="{BAR / 2 + 3.75}">{esc(part.upper())}</text>')
        x += round(len(part) * (10.5 * 0.6 + 0.84)) + 14
    screen: list[str] = []
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
                x0, d, dx = PAD + 2 * CW, n * per, f"{n * CW:.1f}px"
                css.append(f"@keyframes y{i}{{0%,{start}{{transform:translateX({dx})}}"
                           f"{100 * OPEN / total + 0.001:.3f}%,{pct(at, total)}{{transform:translateX(0)}}"
                           f"{pct(at + d, total)},100%{{transform:translateX({dx})}}}}"
                           f".y{i}{{transform:translateX({dx});animation:y{i} {total:.2f}s steps({n},end) forwards}}")
                el += (f'<rect class="y{i}" x="{x0:.1f}" y="{y - LH * 0.8:.1f}" width="{n * CW + 4:.1f}" '
                       f'height="{LH:.1f}" fill="{t["terminal-bg"]}"/>')
        else:  # normal stays quiet; a failed, denied or blocked status is the only red
            el = f'<text class="t{" x" if LIT.search(text) else ""}" x="{PAD}" y="{y:.1f}">{esc(text)}</text>'
        if total:
            css.append(f"@keyframes s{i}{{0%,{start}{{opacity:1}}{100 * OPEN / total + 0.001:.3f}%,"
                       f"{pct(at, total)}{{opacity:0}}{100 * at / total + 0.001:.3f}%,100%{{opacity:1}}}}"
                       f".s{i}{{animation:s{i} {total:.2f}s step-end forwards}}")
            el = f'<g class="s{i}">{el}</g>'
        screen.append(el)
    if total and len(lines) > ROWS:  # scroll one line each time a line appears below the window
        end = (len(lines) - ROWS) * LH
        frames = "".join(f"{pct(at, total)}{{transform:translateY(-{(i - ROWS + 1) * LH:.1f}px)}}"
                         for i, (at, _, _, _) in enumerate(lines) if i >= ROWS)
        css.append(f"@keyframes v{{0%,{start}{{transform:translateY(-{end:.1f}px)}}"
                   f"{100 * OPEN / total + 0.001:.3f}%{{transform:translateY(0)}}"
                   f"{frames}100%{{transform:translateY(-{end:.1f}px)}}}}"
                   f".v{{transform:translateY(-{end:.1f}px);animation:v {total:.2f}s step-end forwards}}")
    clip = f'<clipPath id="win"><rect x="0" y="{BAR + 1}" width="{w}" height="{h - BAR - 1}"/></clipPath>'
    body.append(f'{clip}<g clip-path="url(#win)"><g class="v">{"".join(screen)}</g></g>')
    label = title.replace("|", ", ")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img" aria-label="{esc(label)}"><style>{"".join(css)}</style>{"".join(body)}</svg>\n')


def phone(steps: list[tuple[str, str]], keep: dict[int, str], title: str) -> str:
    """A still of a recording's key lines for screens under 600 px, PHONE_COLS wide so its text stays
    13 px in a phone's column: the commands of the steps in `keep`, each with only the output lines
    that match its pattern, and `…` where lines are left out."""
    lines: list[tuple[float, str, str, float]] = []
    for i, pattern in keep.items():
        cmd, output = steps[i]
        cmd = cmd.split("  #")[0]  # the recording's comments explain the step; the caption does here
        parts = [x for part in cmd.split(" \\\n") for x in wrap(part.strip(), PHONE_COLS - 2)]
        lines += [(0.0, "cmd" if j == 0 else "cont", x.strip() + (" \\" if j < len(parts) - 1 else ""), 0.0)
                  for j, x in enumerate(parts)]
        shown = [x for x in output.splitlines() if re.search(pattern, x)] if pattern else []
        cut = len(shown) < len(output.splitlines())  # lines left out: drop the commas they leave dangling
        for x in shown:
            lines += [(0.0, "out", y, 0.0) for y in wrap(x.rstrip(",") if cut else x, PHONE_COLS)]
        if shown and cut:
            lines.append((0.0, "out", "  …", 0.0))
    lines.append((0.0, "cmd", "", 0.0))
    return terminal(lines, None, title, PHONE_COLS)


def still(command: str, output: str, title: str) -> str:
    parts = command.split("\n")
    lines = [(0.0, "cmd" if i == 0 else "cont", p, 0.0) for i, p in enumerate(parts)]
    lines += [(0.0, "out", x, 0.0) for x in wrap(output)]
    return terminal(lines, None, title)


# ------------------------------------------------------------------------------------------ the diagram
TOKENS = ("canvas", "surface", "raised", "line", "line-strong", "rule", "fg", "fg-muted", "fg-subtle",
          "product-aidlc", "product-hangar", "product-flightdeck", "product-tower")


def px(value: str) -> int:
    """A length token such as `12px` as a number, for SVG attributes that cannot take var()."""
    return int(value.removesuffix("px"))


def night() -> dict[str, str]:
    """Every Night token value, from the vendored Airframe tokens (`scripts/sync-airframe.sh`)."""
    return json.loads((ROOT / "docs/stylesheets/airframe-tokens.json").read_text())["themes"]["dark"]


def flavors() -> dict[str, dict[str, str]]:
    """Token values for the dark and light flavors, from the vendored Airframe tokens (theme-v2 and later)."""
    themes = json.loads((ROOT / "docs/stylesheets/airframe-tokens.json").read_text())["themes"]
    return {flavor: {t: themes[flavor][t] for t in TOKENS} for flavor in ("dark", "light")}


def diagram(colors: dict[str, str] | None) -> str:
    """Where ai-dlc sits in the suite (agent-factory's diagram conventions: Airframe tokens with dark
    fallbacks; with `colors`, every token resolved to that flavor). Drawn at 800 by 520 so that in
    the docs column (686px) body text is still 13px and labels 11px. Airframe theme-v12: labels are
    sentence-case sans, cards take `radius-card` and the steps `radius-control`, the product hue is a
    2px marker inset from the corners, and ai-dlc's box is set apart by a `line-strong` edge, never the brand yellow."""
    dark = flavors()["dark"]
    card, control = px(night()["radius-card"]), px(night()["radius-control"])

    def v(token: str) -> str:
        return colors[token] if colors else f"var(--af-{token}, {dark[token]})"

    sans, text = "Archivo,'Helvetica Neue',Arial,sans-serif", "'Red Hat Text','Helvetica Neue',Arial,sans-serif"
    style = (f".ad .n{{font:700 20px {sans};font-stretch:125%;fill:{v('fg')}}}"
             f".ad .s{{font:700 15px {sans};font-stretch:125%;fill:{v('fg')}}}"
             f".ad .b{{font:400 15.5px {text};fill:{v('fg-muted')}}}"
             f".ad .e{{font:400 13.5px {text};fill:{v('fg-subtle')}}}"
             f".ad .l{{font:500 14px {text};fill:{v('fg-subtle')}}}"
             f".ad .edge{{fill:none;stroke:{v('fg-subtle')};stroke-width:1.25}}")
    out: list[str] = []

    def box(x: int, y: int, w: int, h: int, eyebrow: str, name: str, lines: tuple[str, ...],
            hue: str | None, kind: str = "raised") -> None:
        stroke = f' stroke="{v("line-strong")}"' if kind == "hub" else f' stroke="{v("rule")}"'
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{card}" fill="{v("raised")}"{stroke}/>')
        if hue:
            out.append(f'<rect x="{x + card}" y="{y}" width="{w - 2 * card}" height="2" fill="{v(hue)}"/>')
        out.append(f'<text class="l" x="{x + 16}" y="{y + 28}">{esc(eyebrow)}</text>'
                   f'<text class="n" x="{x + 16}" y="{y + 56}">{esc(name)}</text>')
        out.extend(f'<text class="b" x="{x + 16}" y="{y + 84 + 22 * i}">{esc(t)}</text>'
                   for i, t in enumerate(lines))

    def step(x: int, y: int, name: str, sub: str) -> None:
        out.append(f'<rect x="{x}" y="{y}" width="216" height="58" rx="{control}" fill="{v("surface")}" '
                   f'stroke="{v("line-strong")}"/><text class="s" x="{x + 14}" y="{y + 24}">{esc(name)}</text>'
                   f'<text class="b" x="{x + 14}" y="{y + 46}">{esc(sub)}</text>')

    def edge(d: str, label: str, lx: int, ly: int, anchor: str = "middle") -> None:
        out.append(f'<path class="edge" d="{d}" marker-end="url(#ad-arrow)"/>')
        out.extend(f'<text class="e" x="{lx}" y="{ly + 17 * i}" text-anchor="{anchor}">{esc(t)}</text>'
                   for i, t in enumerate(label.split("|")))

    w, h = 800, 520
    out.append(f'<rect width="{w}" height="{h}" fill="{v("canvas")}"/>')
    out.append('<text class="l" x="24" y="34">Where ai-dlc sits: the developer side of the agent factory</text>')
    box(24, 56, 248, 390, "Developer machine, local", "ai-dlc", (), "product-aidlc", "hub")
    for i, (name, sub) in enumerate((("machine enroll", "a pinned profile"),
                                     ("work new → start", "record, issue, branch"),
                                     ("work pr → project check", "a PR and a check receipt"),
                                     ("work finish", "merged, CI green, closed"))):
        step(40, 128 + 78 * i, name, sub)
        if i:
            out.append(f'<path class="edge" d="M148 {128 + 78 * i - 20} V{128 + 78 * i - 3}" '
                       'marker-end="url(#ad-arrow)"/>')
    box(336, 56, 196, 170, "Team harness repository", "harness.lock",
        ("pins the workflow", "plugin (skills, guide,", "hooks): off in stable,", "on in candidate"), None)
    box(336, 276, 196, 170, "Source of truth", "GitHub",
        ("issues, pull requests,", "a CI receipt per merge", "commit, decisions in", "docs/decisions/"), None)
    box(596, 56, 180, 170, "Run", "hangar",
        ("runs coding agents", "in sandboxes with", "the pinned harness"), "product-hangar")
    box(596, 276, 180, 170, "Judge", "flightdeck",
        ("compares runs with", "and without the", "plugin; posts the", "verdict on the PR"), "product-flightdeck")
    edge("M272 132 H332", "publish|plugin", 302, 112)
    edge("M532 132 H592", "pinned|plugin", 562, 112)
    edge("M686 226 V272", "trials,|traces", 696, 245, anchor="start")
    edge("M272 372 H332", "issue,|PR,|receipt", 302, 336)
    edge("M596 372 H536", "verdict|on PR", 566, 352)
    out.append('<text class="l" x="24" y="488">Govern: Tower clears risky agent actions with policy decisions, approvals '
               'and signed receipts</text>')
    defs = (f'<defs><marker id="ad-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
            f'markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="{v("fg-subtle")}"/>'
            "</marker></defs>")
    return (f'<svg class="ad" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            'role="img" aria-label="Where ai-dlc sits: it prepares developer machines and gates work on '
            'merged evidence; it publishes the workflow plugin that a team harness pins, hangar runs and '
            f'flightdeck compares; Tower governs risky actions">'
            f"<style>{style}</style>{defs}{''.join(out)}</svg>\n")


# ------------------------------------------------------------------------------------------ the clip
# The demo clip (KAN-75): the quickstart's five steps in a fresh project, ending on
# `project check --required` passing, as an MP4 for the suite's pages. A terminal page at 680 px plays
# the session (real output, filtered with jq as the still is) and Playwright screenshots it at 2x;
# each frame is encoded for as long as it was on screen. The terminal is always dark, so the clip is
# Night only. Not byte-reproducible, so `--check` leaves it alone; `--clip` makes it.
CLIP = [  # (command, caption): `~` is the demo's home; jq prints what each step says in plain words
    ("ai-dlc project init ~/demo-app \\\n  | jq -r '\"\\(.status), \\(.files | length) files\"'",
     "project init writes the team's templates into a new project"),
    ("cd ~/demo-app && git init -q", ""),
    ("ai-dlc project setup --root . \\\n  | jq -r 'select(.ready)\n    | \"ready, \\(.agent_configuration.changed | length) rendered\"'",
     "project setup renders the agents' configuration"),
    ("git add -A && git commit -qm 'chore: initialize with ai-dlc'", "Commit the result"),
    ("ai-dlc project check --required \\\n  | jq -r '.outcomes[] | \"\\(.id)  \\(.status)\"'",
     "project check --required: every required check passes"),
]
CLIP_W = 680  # the height fits the finished session and its caption
CLIP_CSS = """
html,body{margin:0;background:var(--af-canvas);overflow:hidden}
.wrap{padding:20px 20px 0}
.term{background:var(--af-terminal-bg);color:var(--af-terminal-fg);border-radius:var(--af-radius-card);
border:1px solid color-mix(in srgb,var(--af-terminal-fg) 8%,transparent);font:14px/20px var(--af-font-mono);overflow:hidden}
.bar{display:flex;gap:6px;align-items:center;padding:0 14px;height:34px;font:500 12.5px var(--af-font-sans);
border-bottom:1px solid color-mix(in srgb,var(--af-terminal-fg) 9%,transparent);color:var(--af-terminal-dim)}
.bar b{color:var(--af-terminal-fg);font-weight:500}
pre{margin:0;padding:16px 18px;font:inherit;white-space:pre}.p{color:var(--af-brand)}
.c,.v{color:var(--af-code-keyword)}.hide{visibility:hidden}
.cap{display:flex;gap:10px;align-items:baseline;padding:14px 20px 18px;color:var(--af-fg);
font:500 15px/1.35 var(--af-font-sans)}
.cap b{font:500 12px var(--af-font-mono);color:var(--af-brand-text);letter-spacing:.08em}
"""
CLIP_JS = """
const lines = [...document.querySelectorAll('pre .l')], cap = document.querySelector('.cap');
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
let step = 0, first = true;  // the first step is on screen, typed and answered, in the first frame (the poster)
async function play() {
  for (const l of lines) {
    if (l.dataset.cap) { step += 1; cap.querySelector('b').textContent = step; cap.querySelector('span').textContent = l.dataset.cap; }
    l.classList.remove('hide');
    const c = l.querySelector('.c');
    if (first) { if (c) c.textContent = c.dataset.t; if (l.dataset.end) { first = false; window.clipStarted = true; await wait(3000); } continue; }
    if (c && c.dataset.t) {
      const t = c.dataset.t;
      for (let k = 0; k <= t.length; k++) { c.textContent = t.slice(0, k); await wait(26); }
      await wait(l.nextElementSibling && l.nextElementSibling.dataset.k === 'cont' ? 0 : 450);
    } else await wait(l.dataset.k === 'out' ? 60 : 0);
    if (l.dataset.end) await wait(1500);
  }
  await wait(3800);
  window.clipDone = true;
}
function prepare() {  // the window is as tall as the finished session (hidden lines keep their place) and a caption
  const c = lines.find((l) => l.dataset.cap);
  cap.querySelector('b').textContent = '1'; cap.querySelector('span').textContent = c.dataset.cap;
  window.clipHeight = Math.ceil(cap.getBoundingClientRect().bottom);
}
document.fonts.ready.then(prepare);  // the recorder sizes the window to clipHeight, then calls play()
"""


def clip_page(steps: list[tuple[str, str]]) -> str:
    """The clip's page: Airframe (the vendored stylesheet, Night) around a terminal; `steps` as run."""
    rows: list[str] = []
    for (cmd, caption), (_, output) in zip(CLIP, steps, strict=True):
        for i, part in enumerate(cmd.split("\n")):
            kind, prompt = ("cmd", "$ ") if i == 0 else ("cont", "> ")
            mark = f' data-cap="{esc(caption)}"' if i == 0 and caption else ""
            rows.append(f'<span class="l hide" data-k="{kind}"{mark}><span class="p">{prompt}</span>'
                        f'<span class="c" data-t="{esc(part)}"></span>\n</span>')
        out = wrap(output) if output else []
        for j, line in enumerate(out):
            last = ' data-end="1"' if j == len(out) - 1 else ""
            cls = " v" if line.endswith("passed") else ""
            rows.append(f'<span class="l hide{cls}" data-k="out"{last}>{esc(line)}\n</span>')
    rows.append('<span class="l hide" data-k="cmd"><span class="p">$ ▌</span></span>')
    css = (ROOT / "docs/stylesheets/airframe.css").read_text()
    fonts = ("https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500"
             "&family=Red+Hat+Text:wght@400..700&display=swap")
    return (f'<!doctype html><html data-theme="dark"><head><meta charset="utf-8"><link rel="stylesheet" '
            f'href="{fonts}"><style>{css}{CLIP_CSS}</style></head><body><div class="wrap"><div class="term">'
            '<div class="bar"><b>ai-dlc</b><span>·</span><span>A new project, five steps</span></div>'
            f'<pre>{"".join(rows)}</pre></div></div><div class="cap"><b></b><span></span></div>'
            f"<script>{CLIP_JS}</script></body></html>\n")


def record_clip(page: str, out: Path) -> float:
    """`out` (MP4, H.264) and its poster (the first frame) from the clip page; returns its length."""
    import tempfile

    from playwright.sync_api import sync_playwright

    ffmpeg = shutil.which("ffmpeg") or sys.exit("build: the clip needs ffmpeg on PATH")
    with sync_playwright() as pw, tempfile.TemporaryDirectory() as d:
        browser = pw.chromium.launch()
        tab = browser.new_context(device_scale_factor=2, viewport={"width": CLIP_W, "height": 900}).new_page()
        tab.set_content(page, wait_until="networkidle")
        tab.wait_for_function("window.clipHeight > 0", timeout=30000)
        tab.set_viewport_size({"width": CLIP_W, "height": tab.evaluate("window.clipHeight")})
        tab.evaluate("() => { play(); }")  # not awaited: the frames are taken while it plays
        tab.wait_for_function("window.clipStarted === true", timeout=30000)
        shots: list[tuple[Path, float]] = []
        while not tab.evaluate("window.clipDone === true"):
            path = Path(d) / f"{len(shots):05d}.png"
            tab.screenshot(path=str(path))
            shots.append((path, tab.evaluate("performance.now()") / 1000))
        browser.close()
        rows = []
        for (path, t), (_, nxt) in zip(shots, [*shots[1:], (None, shots[-1][1] + 0.1)], strict=True):
            rows += [f"file '{path}'", f"duration {max(nxt - t, 0.01):.3f}"]
        listing = Path(d) / "frames.txt"
        listing.write_text("\n".join([*rows, f"file '{shots[-1][0]}'"]) + "\n")
        subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(listing),
                        "-vf", "fps=15,format=yuv420p", "-c:v", "libx264", "-preset", "slow", "-crf", "28",
                        "-movflags", "+faststart", str(out)], check=True)
        shutil.copyfile(shots[0][0], out.with_name(out.stem + "-poster.png"))
    return shots[-1][1] - shots[0][1]


def clip() -> None:
    """clip.mp4 and clip-poster.png: the five steps run for real in a fresh demo home."""
    if DEMO.exists():
        shutil.rmtree(DEMO)
    env = environment()
    try:
        home = Path(env["HOME"])
        (home / "demo-app").mkdir(parents=True)
        steps = [(cmd, tidy(sh(cmd.replace("~", str(home)), home / "demo-app", env)))
                 for cmd, _ in CLIP]
    finally:
        shutil.rmtree(DEMO, ignore_errors=True)
    if not steps[2][1].startswith("ready, ") or not all(
            line.endswith("  passed") for line in steps[-1][1].splitlines()):
        sys.exit(f"build: project check --required did not pass:\n{steps[-1][1]}")
    seconds = record_clip(clip_page(steps), HERE / "clip.mp4")
    size = (HERE / "clip.mp4").stat().st_size
    if not 15 <= seconds <= 25 or size > 3_000_000:
        sys.exit(f"build: clip.mp4 runs {seconds:.1f} s and is {size} bytes; a clip runs 15 to 25 s, under 3 MB")
    print(f"build: wrote clip.mp4 ({seconds:.1f} s, {size // 1024} KB) and clip-poster.png")


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
        ("enroll", enroll, "ai-dlc machine enroll: preview, apply, status",
         "ai-dlc|machine enroll|preview, apply, status", 1.0),
        ("work", work, "ai-dlc work: start → pr → finish refused → merge → finish (GitHub is a local stand-in)",
         "ai-dlc|work: start → pr → finish|GitHub is a local stand-in", 0.7),
    ):
        lines, total = timeline(steps, gap)
        files[f"{name}.cast"] = cast(steps, title, gap)
        files[f"{name}.svg"] = terminal(lines, total, bar)
    files["enroll-phone.svg"] = phone(enroll, {1: r'"applied": true', 2: r'"(drift|enrolled|ready)"|not bound'},
                                      "ai-dlc|machine enroll")
    files["work-phone.svg"] = phone(work, {3: r'"(gate|status)"|not merged', 4: "",
                                           5: r'"(ci-green|pr-merged|merged|status|state)"'}, "ai-dlc|work finish")
    titles = {"project-check.svg": "ai-dlc|project check --required",
              "plugin-skills.svg": "Claude Code|the ai-dlc workflow plugin"}
    for name, (cmd, text) in shots.items():
        files[name] = still(cmd, text, titles[name])
    check = ("ai-dlc project check --required \\\n  | jq '…'", shots["project-check.svg"][1])  # the filter is on the wide one
    files["project-check-phone.svg"] = phone([check], {0: "."}, titles["project-check.svg"])
    files["suite.svg"] = diagram(None)
    for flavor, colors in flavors().items():
        files[f"suite-{flavor}.svg"] = diagram(colors)
    return files


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="Fail when a committed asset differs.")
    ap.add_argument("--skip-claude", action="store_true", help="Keep the committed plugin screen.")
    ap.add_argument("--clip", action="store_true", help="Only record clip.mp4 (needs Playwright and ffmpeg).")
    args = ap.parse_args(argv)
    if args.clip:
        clip()
        return 0
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
