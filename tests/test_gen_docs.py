"""Checks for generated reference documentation."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("gen_docs", ROOT / "tools/gen_docs.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)


def test_generated_documents_match():
    for path, content in gen.generate().items():
        assert (ROOT / path).read_text() == content, path


def test_commands_and_refusal_expressions():
    outputs = gen.generate()
    for name in gen.COMMANDS:
        assert f'<a id="{name}"></a>' in outputs["docs/api.md"]
        assert f'<a id="{name}"></a>' in outputs["docs/reference/errors.md"]
    assert "dynamic expression" in outputs["docs/reference/errors.md"]
    for page in (ROOT / "docs").rglob("*.md"):
        assert page.relative_to(ROOT).as_posix() in outputs["llms.txt"]


def test_command_prose_is_projected_once_verbatim():
    sections = gen.command_sections()
    api = gen.generate()["docs/api.md"]
    for name, body in sections.items():
        if name not in gen.COMMANDS:
            continue
        section = api.split(f'<a id="{name}"></a>', 1)[1].split('<a id="', 1)[0]
        assert section.count(body) == 1, name
        assert "[API reference](../api.md#" not in section


def test_command_section_parser_preserves_multiline_body(tmp_path, monkeypatch):
    commands = tmp_path / "docs/commands"
    commands.mkdir(parents=True)
    (commands / "sample.md").write_text(
        "# Commands\n\n## `sample`\n\nFirst sentence. "
        "[API reference](../api.md#sample).\n\n- Detail one\n- Detail two\n"
    )
    monkeypatch.setattr(gen, "ROOT", tmp_path)
    monkeypatch.setattr(gen, "COMMANDS", {"sample": {}})
    assert gen.command_sections()["sample"] == ("First sentence.\n\n- Detail one\n- Detail two")


def test_projected_relative_links_resolve_and_examples_are_not_duplicated():
    import re
    from urllib.parse import unquote, urlsplit

    api = gen.generate()["docs/api.md"]
    for target in re.findall(r"\[[^\]]+\]\(([^ )]+)\)", api):
        link = urlsplit(target)
        if link.scheme or link.netloc or not link.path:
            continue
        assert (ROOT / "docs" / unquote(link.path)).is_file(), target
    sections = gen.command_sections()
    for name, body in sections.items():
        if name in gen.COMMANDS and "```python" in body:
            section = api.split(f'<a id="{name}"></a>', 1)[1].split('<a id="', 1)[0]
            assert section.count("```python") == body.count("```python") + 1
