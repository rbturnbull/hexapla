from pathlib import Path

from hexapla.about import local_links, render_about


def test_local_links():
    text = "![a](img/a.png) [b](docs/b.pdf#page=2) [c](https://x.org) [d](#top) [e](mailto:a@b.c) [f](/abs.png) ![g](img/a.png)"
    assert local_links(text) == ["img/a.png", "docs/b.pdf#page=2"]


def test_render_about_rewrites_asset_links(tmp_path):
    about = tmp_path / "theme" / "about.md"
    assets = tmp_path / "theme" / "assets"
    (assets / "img").mkdir(parents=True)
    (assets / "img" / "logo.png").write_bytes(b"png")
    (assets / "notes.pdf").write_bytes(b"pdf")
    about.write_text("![Logo](assets/img/logo.png \"The logo\") and [notes](assets/notes.pdf#page=2) and [data](assets/notes.pdf?v=2) and [x](https://x.org)")
    html = render_about(about, assets, root="../")
    assert '<img src="../assets/img/logo.png" alt="Logo" title="The logo" />' in html
    assert 'href="../assets/notes.pdf#page=2"' in html and 'href="../assets/notes.pdf?v=2"' in html and 'href="https://x.org"' in html


def test_render_about_without_assets(tmp_path):
    about = tmp_path / "about.md"
    about.write_text("Plain *text*.")
    assert render_about(about, None, root="../") == "<p>Plain <em>text</em>.</p>\n"


def test_images_can_be_sized_and_classed(tmp_path):
    about = tmp_path / "about.md"
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "erc.jpg").write_bytes(b"jpg")
    about.write_text("![ERC](assets/erc.jpg){width=180 .float-end}")
    assert render_about(about, assets, root="../") == \
        '<p><img src="../assets/erc.jpg" alt="ERC" width="180" class="float-end" /></p>\n'
