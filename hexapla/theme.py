"""
The site's stylesheet: Bootstrap and Hexapla's own styles, compiled from SCSS with the theme's variables.

A ``.scss`` theme sets Bootstrap variables (``$primary``, ``$body-bg``, ``$font-family-sans-serif``...) and
Hexapla's (``$hexapla-brand``, ``$hexapla-page-bg``, ``$hexapla-serif``...; see ``static/scss/_hexapla.scss``).
The site's brand colour follows ``$primary`` when the theme sets it. It is compiled between
Bootstrap's functions and the rest of Bootstrap, the order Bootstrap's docs give for overriding variables, and
can ``@import`` partials beside it. A ``.css`` theme is added after the compiled sheet.
"""
from __future__ import annotations

from pathlib import Path

import sass

SCSS_DIR = Path(__file__).resolve().parent / "static" / "scss"
BOOTSTRAP_SCSS = SCSS_DIR / "bootstrap" / "scss"
DEFAULT_BRAND = "#224abe"  # Hexapla's blue, used unless the theme sets $primary or $hexapla-brand


class ThemeError(Exception):
    pass


def compile_css(variables: Path | None) -> str:
    """ The stylesheet for a theme file (``.scss`` or ``.css``), or Hexapla's default look for ``None``. """
    is_scss = variables is not None and variables.suffix.lower() == ".scss"
    theme = variables.read_text(encoding="utf-8") if is_scss else ""
    sheet = f'@import "functions";\n{theme}\n@import "bootstrap";\n@import "hexapla";\n'
    include_paths = [str(BOOTSTRAP_SCSS), str(SCSS_DIR)] + ([str(variables.parent)] if is_scss else [])
    try:
        css = sass.compile(string=sheet, include_paths=include_paths, output_style="compressed")
    except sass.CompileError as err:
        raise ThemeError(f"{variables}: {str(err).strip()}") from err
    if variables is not None and not is_scss:
        css += "\n" + variables.read_text(encoding="utf-8")
    return css
