"""daily-note reads Work Copilot's attention only when it is bound (KAN-396)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "agents/skills/daily-note/SKILL.md"


def _start_of_day() -> str:
    text = SKILL.read_text(encoding="utf-8")
    return text.split("## Start of day", 1)[1].split("## End of day", 1)[0]


def test_start_of_day_reads_get_attention_only_when_bound_in_the_work_vault():
    section = _start_of_day()
    assert "`get_attention`" in section
    assert "origin is `work`" in section
    assert "available in this session" in section
    assert "Without the tool, or in the\n   `home` vault, leave the section out" in section


def test_attention_stays_read_only_and_shows_gaps():
    section = _start_of_day()
    assert "Never call Work Copilot's write tools from here." in section
    for gap in ("`healthy`", "`page.next_cursor`", "`refresh_needed`"):
        assert gap in section


def test_shipped_plugin_carries_the_same_skill():
    for copy in (
        "plugins/ai-dlc-workflow/skills/daily-note/SKILL.md",
        "plugins/ai-dlc-workflow/native/codex/skills/daily-note/SKILL.md",
    ):
        assert "`get_attention`" in (ROOT / copy).read_text(encoding="utf-8"), copy
