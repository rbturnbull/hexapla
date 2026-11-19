"""
The about page: the theme's Markdown file, rendered to HTML.

Images and links in it are written relative to the Markdown file, as they are when it is previewed on GitHub.
Images can be given a size or Bootstrap classes: ``![ERC](assets/erc-logo.jpg){width=180 .float-end}``.
Those that point into the theme's ``assets`` folder (``![ERC](assets/erc-logo.jpg)``) are rewritten to the copy
of the folder in the site; any other local link would be broken on the site, so validation reports it.
"""
from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

from markdown_it import MarkdownIt
from mdit_py_plugins.attrs import attrs_plugin

ATTRIBUTES = {"image": "src", "link_open": "href"}


def _markdown() -> MarkdownIt:
    return MarkdownIt().use(attrs_plugin)


def _link_tokens(tokens):
    for token in tokens:
        for child in token.children or []:
            if child.type in ATTRIBUTES:
                yield child, ATTRIBUTES[child.type]


def _is_local(url: str) -> bool:
    parts = urlsplit(url)
    return bool(parts.path) and not parts.scheme and not parts.netloc and not url.startswith("/")


def local_links(text: str) -> list[str]:
    """ The images and links in a Markdown text that point to local files, in order, without repeats. """
    links = [str(token.attrs[attr]) for token, attr in _link_tokens(_markdown().parse(text))]
    return list(dict.fromkeys(link for link in links if _is_local(link)))


def asset_path(link: str, about: Path, assets: Path | None) -> str | None:
    """ Where a link from the about file lands in the assets folder (``img/logo.png``), or None if it is not there. """
    if assets is None:
        return None
    target = (about.parent / urlsplit(link).path).resolve()
    assets = assets.resolve()
    if not target.is_file() or not target.is_relative_to(assets):
        return None
    return target.relative_to(assets).as_posix()


def render_about(about: Path, assets: Path | None, root: str) -> str:
    """ The about page's HTML, with links into the assets folder pointing at its copy in the site. """
    md = _markdown()
    tokens = md.parse(about.read_text(encoding="utf-8"))
    for token, attr in _link_tokens(tokens):
        link = str(token.attrs[attr])
        if _is_local(link) and (path := asset_path(link, about, assets)):
            parts = urlsplit(link)
            suffix = (f"?{parts.query}" if parts.query else "") + (f"#{parts.fragment}" if parts.fragment else "")
            token.attrs[attr] = f"{root}assets/{path}{suffix}"
    return md.renderer.render(tokens, md.options, {})
