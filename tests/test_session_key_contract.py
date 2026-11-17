"""The session join key page is the contract; it must match session_key.py (KAN-495).

``docs/design/session-join-key.md`` is what flightdeck, hangar and trace review read
to tie a trace to its ticket. A change to the key's format, trailer name or
environment variable names fails here unless the page changes in the same PR.
"""

from __future__ import annotations

import re
from pathlib import Path

from ai_dlc.work import session_key

PAGE = Path(__file__).resolve().parents[1] / "docs/design/session-join-key.md"
FENCE = re.compile(r"```text\n(.*?)\n```", re.DOTALL)


def _page() -> str:
    return PAGE.read_text(encoding="utf-8")


def _section(title: str) -> str:
    """The text under one ``## title`` heading, up to the next ``##`` heading."""
    match = re.search(
        rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)", _page(), re.MULTILINE | re.DOTALL
    )
    assert match, f"{PAGE.name}: the '## {title}' section is missing"
    return match.group(1)


def _block_after(text: str, lead: str) -> str:
    """The first ``text`` fenced block after the paragraph that contains ``lead``."""
    start = text.find(lead)
    assert start >= 0, f"{PAGE.name}: no paragraph containing {lead!r}"
    match = FENCE.search(text, start)
    assert match, f"{PAGE.name}: no ```text block after {lead!r}"
    return match.group(1).strip()


def test_whole_key_expression_matches_the_parser():
    shown = _block_after(_section("Format"), "A whole key matches")
    expected = "^" + session_key._KEY.pattern + "$"
    assert shown == expected, (
        "Update the 'A whole key matches' block under '## Format' in "
        f"{PAGE.name}: it shows {shown!r}, session_key.py parses {expected!r}"
    )


def test_session_environment_row_names_the_four_variables():
    rows = [
        line
        for line in _section("Where it is written").splitlines()
        if line.startswith("| Session environment |")
    ]
    assert len(rows) == 1, (
        f"Update the '## Where it is written' table in {PAGE.name}: "
        "it needs exactly one 'Session environment' row"
    )
    shown = set(re.findall(r"`(AI_DLC_[A-Z_]+)`", rows[0]))
    expected = {
        session_key.ENV_KEY,
        session_key.ENV_TRACKER,
        session_key.ENV_WORK,
        session_key.ENV_SESSION,
    }
    assert shown == expected, (
        "Update the 'Session environment' row of the '## Where it is written' table "
        f"in {PAGE.name}: it names {sorted(shown)}, session_key.py exports "
        f"{sorted(expected)}"
    )


def test_trailer_is_shown_with_its_exact_name():
    trailer = f"`{session_key.TRAILER}: <key>`"
    assert trailer in _section("Format"), (
        f"Update the trailer line under '## Format' in {PAGE.name}: session_key.py writes {trailer}"
    )


def test_format_block_shows_the_version_and_three_parts():
    block = FENCE.search(_section("Format"))
    assert block, f"{PAGE.name}: the '## Format' section has no ```text block"
    shown = block.group(1).strip()
    expected = f"{session_key.VERSION}:<tracker>:<work>:<session>"
    assert shown == expected, (
        f"Update the first block under '## Format' in {PAGE.name}: it shows "
        f"{shown!r}, session_key.py writes {expected!r}"
    )


def test_part_pattern_matches_the_parser():
    match = re.search(r"Each non-empty part matches `([^`]+)`", _section("Format"))
    assert match, f"{PAGE.name}: no 'Each non-empty part matches' line under '## Format'"
    shown = match.group(1)
    assert shown == session_key._SAFE.pattern, (
        f"Update the 'Each non-empty part matches' line under '## Format' in {PAGE.name}: "
        f"it shows {shown!r}, session_key.py checks {session_key._SAFE.pattern!r}"
    )
    upper = re.search(r",(\d+)\}$", session_key._PART)
    assert upper and shown.endswith(f",{upper.group(1)}}}"), (
        f"session_key.py: _SAFE and _PART disagree on a part's length ({shown!r}, {session_key._PART!r})"
    )
