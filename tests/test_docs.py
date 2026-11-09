"""Coverage checks for the hand-written command guides."""

import re
from collections import Counter
from pathlib import Path

from crusader.commands import COMMANDS

ROOT = Path(__file__).resolve().parents[1]
COMMANDS_DIR = ROOT / "docs" / "commands"


def test_command_guides_cover_each_command_once():
    groups = {spec["group"] for spec in COMMANDS.values()}
    assert {path.stem for path in COMMANDS_DIR.glob("*.md")} == groups

    for group in groups:
        text = (COMMANDS_DIR / f"{group}.md").read_text()
        headings = re.findall(r"^## `([^`]+)`$", text, re.MULTILINE)
        expected = {name for name, spec in COMMANDS.items() if spec["group"] == group}
        assert Counter(headings) == Counter({name: 1 for name in expected})
        for name in expected:
            assert text.count(f"../api.md#{name})") == 1
