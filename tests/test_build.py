import json
import re

import pytest

from hexapla.build import OutputDirError, build_site, gregory_aland_to_intf_id
from hexapla.config import load_config
from hexapla.corpus import load_project

from .conftest import CONFIG_NAME, PROJECT, read_config, write_config


def build(project_dir, output):
    project = load_project(load_config(project_dir / CONFIG_NAME))
    build_site(project, output)
    return output


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    return build(PROJECT, tmp_path_factory.mktemp("site") / "site")


def read(site, path):
    return (site / path).read_text(encoding="utf-8")


def test_assets(site):
    assert "--brand: #7b2d26" in read(site, "css/hexapla.css")  # the theme's $primary
    assert read(site, "img/logo.svg").startswith("<svg")
    for script in ("common.js", "navigator.js", "pages.js", "d3.v7.min.js"):
        assert (site / "js" / script).exists()
    assert (site / ".hexapla").exists()


def test_home_page(site):
    home = read(site, "index.html")
    assert "<title>Home · Test Navigator</title>" in home
    assert 'href="./alignments/claro/"' in home
    assert "Codex Claromontanus" in home and "Greek-Latin" in home
    assert 'href="./about/"' in home
    assert 'src="./img/logo.svg"' in home
    assert 'href="./css/hexapla.css"' in home
    assert not re.search(r'(href|src)="/', home)  # relative links work under /<repo>/ on GitHub Pages


def test_about_page(site):
    about = read(site, "about/index.html")
    assert "<strong>one</strong>" in about and "About the test project" in about
    assert 'href="../css/hexapla.css"' in about


def test_manuscript_pages(site):
    greek = read(site, "manuscripts/claro-greek/index.html")
    assert "Codex Claromontanus" in greek and "Greek" in greek
    assert "Paris, Bibliothèque nationale de France, Grec 107" in greek
    assert "https://www.trismegistos.org/text/65887" in greek
    assert "6th century" in greek
    assert "Greek-Latin bilingual of the Pauline epistles." in greek
    assert 'href="claro-greek.xml"' in greek and (site / "manuscripts/claro-greek/claro-greek.xml").exists()
    assert "CC BY 4.0" in greek  # the TEI's own licence
    assert 'href="../../alignments/claro/"' in greek

    latin = read(site, "manuscripts/claro-latin/index.html")
    assert "CC BY-NC-SA 4.0" in latin  # no licence in the TEI: the site's applies
    assert "Parsing" in latin and "CC BY 4.0" in latin  # parsing_licence


def test_alignment_overview(site):
    page = read(site, "alignments/claro/index.html")
    assert "Codex Claromontanus" in page and "GA 06" in page and "VL 75" in page and "6th century" in page
    assert 'href="../../manuscripts/claro-greek/"' in page and 'href="../../manuscripts/claro-latin/"' in page
    footer = re.sub(r"<[^>]+>", "", page.split('class="site-footer"')[1])
    assert "A. Scribe (CC BY 4.0)" in footer and "B. Scribe (CC BY-NC-SA 4.0)" in footer
    assert "Alignment: CC BY-NC-SA 4.0" in footer
    assert "Latin parsing: CC BY 4.0" in footer and "Greek parsing: CC BY-NC-SA 4.0" in footer
    for name in ("corpus.js", "verses.js", "lexicon/index.html", "insights/index.html", "review/index.html"):
        assert (site / "alignments/claro" / name).exists()


def test_verse_pages(site):
    verse_dir = site / "alignments/claro/B06K01V07"
    page = read(verse_dir, "index.html")
    assert "Romans 1:7" in page and "Codex Claromontanus" in page
    assert "fol. 1r" in page and "1 correction" in page
    assert 'href="../../../manuscripts/claro-greek/"' in page
    js = read(verse_dir, "claro-B06K01V07.js")
    word_map_json = re.search(r"const wordMap = (.*);", js).group(1)
    assert all(isinstance(v, list) for v in json.loads(word_map_json).values())


def test_lemma_pages(site):
    assert list((site / "alignments/claro/latin").glob("*/index.html"))
    page = read(site, "alignments/claro/greek/χάρις/index.html")
    assert "χάρις" in page and "gratia" in page
    assert (site / "alignments/claro/greek/lemmas.js").exists()


def test_rebuild_removes_stale_files(project_dir, tmp_path):
    output = build(project_dir, tmp_path / "site")
    (output / "alignments" / "stale").mkdir()
    build(project_dir, output)
    assert not (output / "alignments" / "stale").exists()


def test_refuses_to_overwrite_a_folder_it_did_not_build(project_dir, tmp_path):
    output = tmp_path / "precious"
    output.mkdir()
    (output / "thesis.docx").write_text("do not delete")
    with pytest.raises(OutputDirError, match="precious"):
        build(project_dir, output)
    assert (output / "thesis.docx").exists()
    empty = tmp_path / "empty"
    empty.mkdir()
    build(project_dir, empty)
    assert (empty / "index.html").exists()


def test_refuses_a_file_as_output(project_dir, tmp_path):
    output = tmp_path / "file"
    output.write_text("x")
    with pytest.raises(OutputDirError):
        build(project_dir, output)


def test_defaults_without_a_theme(project_dir, tmp_path):
    data = read_config(project_dir)
    data["theme"] = {}
    write_config(project_dir, data)
    output = build(project_dir, tmp_path / "site")
    home = read(output, "index.html")
    assert "· Hexapla</title>" in home
    assert 'src="./img/hexapla-logo.svg"' in home and (output / "img/hexapla-logo.svg").exists()
    assert 'href="./about/"' not in home and not (output / "about").exists()
    assert "--brand: #224abe" in read(output, "css/hexapla.css")
    footer = re.sub(r"<[^>]+>", "", read(output, "alignments/claro/index.html").split('class="site-footer"')[1])
    assert "B. Scribe (no licence stated)" in footer and "Alignment" not in footer


def test_png_logo_keeps_its_extension(project_dir, tmp_path):
    (project_dir / "theme" / "logo.png").write_bytes(b"\x89PNG")
    data = read_config(project_dir)
    data["theme"]["logo"] = "theme/logo.png"
    write_config(project_dir, data)
    output = build(project_dir, tmp_path / "site")
    assert (output / "img/logo.png").exists() and 'src="./img/logo.png"' in read(output, "index.html")


def test_manuscript_without_an_alignment_still_gets_a_page(project_dir, tmp_path):
    data = read_config(project_dir)
    data["manuscripts"]["claro-copy"] = dict(data["manuscripts"]["claro-greek"])
    write_config(project_dir, data)
    output = build(project_dir, tmp_path / "site")
    page = read(output, "manuscripts/claro-copy/index.html")
    assert "Not in any alignment yet." in page


def test_page_names_cannot_clash(project_dir, tmp_path):
    for name in ("greek", "latin"):
        path = project_dir / "claro" / f"claro-{name}.conllu"
        path.write_text(path.read_text() + "\n# sent_id = Lexicon\n1\tx\tx\tX\t_\t_\t0\troot\t_\t_\n")
    with pytest.raises(ValueError, match="clash with page names: lexicon"):
        build(project_dir, tmp_path / "site")


def test_gregory_aland_numbers_sort_the_sidebar():
    assert gregory_aland_to_intf_id("P6") == 10006
    assert gregory_aland_to_intf_id("05") == 20005
    assert gregory_aland_to_intf_id("GA0278") == 20278
    assert gregory_aland_to_intf_id("460") == 30460
    assert gregory_aland_to_intf_id("L2211") == 42211
    assert gregory_aland_to_intf_id("") is None
    assert gregory_aland_to_intf_id("Harris 9") is None


def test_sidebar_sorts_by_gregory_aland_then_siglum():
    from hexapla.build import sidebar_sort_key
    items = [{"siglum": "Harris 9"}, {"siglum": "05", "gregoryaland": "05"}, {"siglum": "P6", "gregoryaland": "P6"}]
    assert [item["siglum"] for item in sorted(items, key=sidebar_sort_key)] == ["P6", "05", "Harris 9"]


def test_reference_ranges():
    from hexapla.build import _ref_range
    assert _ref_range("John.1.24", "John.8.31") == "John 1:24 – 8:31"
    assert _ref_range("John.1.24", "Acts.1.2") == "John 1:24 – Acts 1:2"
    assert _ref_range("John.1.24", "John.1.24") == "John 1:24"
    assert _ref_range(None, None) == ""
    assert _ref_range("Colophon", "inscriptio") == "Colophon – inscriptio"


def test_attribution_credits():
    from hexapla.build import attribution
    base = {"language": "Gothic", "licence": None}
    lines = attribution([
        {**base, "header": {"responsibility": [{"resp": "Edition metadata assembled by", "names": ["VMRCRE"]}],
                            "publishers": [], "authority": "Project Wulfila"}},
        {**base, "header": {"responsibility": [], "publishers": ["ITSEE"], "authority": "Wulfila"}},
        {**base, "header": {"responsibility": [], "publishers": [], "authority": ""}},
    ])
    assert [line["credit"] for line in lines] == ["Project Wulfila", "ITSEE, Wulfila", "transcriber not named in the file"]
    assert lines[0]["licence"] == "no licence stated"


def test_assets_are_copied_and_the_about_page_links_to_them(site):
    assert (site / "assets/badge.svg").exists() and (site / "assets/docs/guide.txt").exists()
    about = read(site, "about/index.html")
    assert 'src="../assets/badge.svg"' in about and 'alt="A badge"' in about
    assert 'href="../assets/docs/guide.txt"' in about
    assert 'href="https://example.org/"' in about and 'href="#funding"' in about


def test_about_links_from_a_nested_about_file(project_dir, tmp_path):
    """ Links are relative to the about file, wherever it is. """
    (project_dir / "pages").mkdir()
    (project_dir / "pages" / "about.md").write_text("![Badge](../theme/assets/badge.svg)\n")
    data = read_config(project_dir)
    data["theme"]["about"] = "pages/about.md"
    write_config(project_dir, data)
    output = build(project_dir, tmp_path / "site")
    assert 'src="../assets/badge.svg"' in read(output, "about/index.html")
