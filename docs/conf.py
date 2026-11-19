"""Sphinx configuration for Hexapla."""

from __future__ import annotations

import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parent
sys.path.insert(0, str(DOCS.parent))

project = "Hexapla"
author = "Robert Turnbull"
copyright = "2026, Robert Turnbull"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
]
exclude_patterns = ["_build"]
html_theme = "furo"
html_title = "Hexapla"
html_static_path = ["_static"]
html_logo = "_static/hexapla-logo.svg"
html_favicon = "_static/hexapla-logo.svg"
html_theme_options = {
    "sidebar_hide_name": True,
    "light_css_variables": {"color-brand-primary": "#9c3d2a", "color-brand-content": "#9c3d2a"},
    "dark_css_variables": {"color-brand-primary": "#e8c890", "color-brand-content": "#e8c890"},
}
autodoc_member_order = "bysource"
autodoc_typehints = "description"
copybutton_prompt_text = "$ "

CLI_COMMANDS = [[], ["build"], ["validate"]]


def write_cli_reference(app) -> None:
    """ Renders ``--help`` for every command into ``_generated/cli.rst``. """
    from typer.testing import CliRunner

    from hexapla.main import app as cli

    runner = CliRunner()
    parts = ["CLI reference\n=============\n", "Generated from the command-line help when the docs are built.\n"]
    for command in CLI_COMMANDS:
        result = runner.invoke(cli, [*command, "--help"], prog_name="hexapla",
                               env={"COLUMNS": "88", "NO_COLOR": "1", "TERM": "dumb"})
        title = " ".join(["hexapla", *command])
        body = "\n".join(f"    {line}" for line in result.output.strip().splitlines())
        parts.append(f"``{title}``\n{'-' * (len(title) + 4)}\n\n.. code-block:: text\n\n{body}\n")
    target = DOCS / "_generated" / "cli.rst"
    target.parent.mkdir(exist_ok=True)
    text = "\n".join(parts)
    if not target.exists() or target.read_text(encoding="utf-8") != text:
        target.write_text(text, encoding="utf-8")


def setup(app):
    app.connect("builder-inited", write_cli_reference)
