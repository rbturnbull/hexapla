from pathlib import Path

import pytest

from hexapla.config import Alignment, Config, ConfigError, Manuscript, Theme, load_config

from .conftest import CONFIG_NAME, PROJECT, read_config, write_config


def test_load_project_config():
    config = load_config(PROJECT / CONFIG_NAME)
    assert isinstance(config, Config)
    assert config.path == (PROJECT / CONFIG_NAME).resolve()
    assert config.root == PROJECT.resolve()

    assert isinstance(config.theme, Theme)
    assert config.theme.name == "Test Navigator"
    assert config.theme.logo == PROJECT.resolve() / "theme" / "logo.svg"
    assert config.theme.variables.suffix == ".scss"
    assert config.theme.licence == "CC-BY-NC-SA-4.0"

    assert [m.id for m in config.manuscripts] == ["claro-greek", "claro-latin"]
    greek, latin = config.manuscripts
    assert isinstance(greek, Manuscript)
    assert greek.tei == PROJECT.resolve() / "claro" / "claro-greek.xml"
    assert greek.parsing_licence is None and latin.parsing_licence == "CC-BY-4.0"

    (alignment,) = config.alignments
    assert isinstance(alignment, Alignment)
    assert alignment.id == "claro" and alignment.name is None and alignment.licence is None
    assert alignment.manuscripts == ["claro-greek", "claro-latin"]
    assert config.manuscript("claro-latin") is latin


def test_minimal_config_uses_defaults(project_dir):
    data = read_config(project_dir)
    del data["theme"]
    config = load_config(write_config(project_dir, data))
    assert config.theme == Theme()
    assert config.theme.name == "Hexapla"
    assert config.theme.logo is None and config.theme.variables is None and config.theme.about is None


def test_absolute_paths_are_kept(project_dir):
    data = read_config(project_dir)
    absolute = (project_dir / "claro" / "claro-greek.xml").resolve()
    data["manuscripts"]["claro-greek"]["tei"] = str(absolute)
    assert load_config(write_config(project_dir, data)).manuscripts[0].tei == absolute


def test_config_in_a_subfolder_resolves_paths_against_itself(project_dir):
    nested = project_dir / "configs"
    nested.mkdir()
    data = read_config(project_dir)
    data["theme"] = {"logo": "../theme/logo.svg"}
    data["manuscripts"] = {key: {k: f"../{v}" for k, v in value.items() if k in ("tei", "parsing")}
                           for key, value in data["manuscripts"].items()}
    data["alignments"]["claro"]["links"] = "../claro/claro-links.jsonl"
    path = write_config(nested, data)
    config = load_config(path)
    assert config.theme.logo == (project_dir / "theme" / "logo.svg").resolve()


@pytest.mark.parametrize("change, message", [
    (lambda d: d["manuscripts"]["claro-greek"].update(tei="missing.xml"), "missing.xml"),
    (lambda d: d["theme"].update(about="nowhere.md"), "nowhere.md"),
    (lambda d: d["theme"].update(variables="theme/about.md"), ".scss or .css"),
    (lambda d: d["alignments"]["claro"].update(manuscripts=["claro-greek", "claro-coptic"]), "claro-coptic"),
    (lambda d: d["alignments"]["claro"].update(manuscripts=["claro-greek"]), "at least 2"),
    (lambda d: d["alignments"]["claro"].update(manuscripts=["claro-greek", "claro-greek"]), "more than once"),
    (lambda d: d["alignments"]["claro"].update(manuscripts=["claro-greek", "claro-latin", "claro-greek"]), "more than once"),
    (lambda d: d["manuscripts"].update({"Bad Id!": d["manuscripts"]["claro-greek"]}), "Bad Id!"),
    (lambda d: d["alignments"]["claro"].update(mss=["claro-greek", "claro-latin"]), "mss"),
    (lambda d: d.update(manuscripts=[{"tei": "a.xml"}]), "mapping"),
    (lambda d: d["manuscripts"].update({"claro-greek": "claro/claro-greek.xml"}), "claro-greek"),
])
def test_config_errors(project_dir, change, message):
    data = read_config(project_dir)
    change(data)
    with pytest.raises(ConfigError, match=None) as caught:
        load_config(write_config(project_dir, data))
    assert message in str(caught.value)


def test_three_way_alignments_are_not_supported_yet(project_dir):
    data = read_config(project_dir)
    data["manuscripts"]["claro-copy"] = dict(data["manuscripts"]["claro-greek"])
    data["alignments"]["claro"]["manuscripts"].append("claro-copy")
    with pytest.raises(ConfigError, match="exactly two manuscripts"):
        load_config(write_config(project_dir, data))


def test_errors_list_every_problem(project_dir):
    data = read_config(project_dir)
    data["manuscripts"]["claro-greek"]["tei"] = "one.xml"
    data["manuscripts"]["claro-latin"]["parsing"] = "two.conllu"
    with pytest.raises(ConfigError) as caught:
        load_config(write_config(project_dir, data))
    assert len(caught.value.errors) == 2
    assert "one.xml" in str(caught.value) and "two.conllu" in str(caught.value)
    assert str(project_dir / CONFIG_NAME) in str(caught.value)


def test_unreadable_config(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "nope.yaml")
    bad = tmp_path / "bad.yaml"
    bad.write_text("theme: [unclosed", encoding="utf-8")
    with pytest.raises(ConfigError, match="YAML"):
        load_config(bad)
    scalar = tmp_path / "scalar.yaml"
    scalar.write_text("just a string", encoding="utf-8")
    with pytest.raises(ConfigError, match="mapping"):
        load_config(scalar)


def test_config_can_be_built_in_python(tmp_path):
    """ Without a config file, relative paths stay relative and are not checked. """
    config = Config(
        manuscripts=[Manuscript(id="a", tei=Path("a.xml"), parsing=Path("a.conllu")),
                     Manuscript(id="b", tei=Path("b.xml"), parsing=Path("b.conllu"))],
        alignments=[Alignment(id="ab", manuscripts=["a", "b"], links=Path("ab.jsonl"))],
    )
    assert config.path is None and config.root is None
    assert Theme(about=Path("about.md"), assets=Path("assets")).about == Path("about.md")
    assert config.manuscripts[0].tei == Path("a.xml")
    with pytest.raises(KeyError):
        config.manuscript("missing")


def test_assets_folder(project_dir):
    config = load_config(project_dir / CONFIG_NAME)
    assert config.theme.assets == (project_dir / "theme" / "assets").resolve()


@pytest.mark.parametrize("change, message", [
    (lambda d: d["theme"].update(assets="theme/missing"), "folder not found"),
    (lambda d: d["theme"].update(assets="theme/about.md"), "folder not found"),
])
def test_assets_errors(project_dir, change, message):
    data = read_config(project_dir)
    change(data)
    with pytest.raises(ConfigError) as caught:
        load_config(write_config(project_dir, data))
    assert message in str(caught.value)


def test_about_page_can_only_link_to_assets(project_dir):
    about = project_dir / "theme" / "about.md"
    about.write_text(about.read_text() + "\n![Missing](assets/nope.png) [Elsewhere](../claro/claro-greek.xml)\n")
    with pytest.raises(ConfigError) as caught:
        load_config(project_dir / CONFIG_NAME)
    assert "theme.about: assets/nope.png is not in the assets folder" in str(caught.value)
    assert "../claro/claro-greek.xml is not in the assets folder" in str(caught.value)


def test_about_page_links_need_an_assets_folder(project_dir):
    data = read_config(project_dir)
    del data["theme"]["assets"]
    with pytest.raises(ConfigError, match="assets/badge.svg is not in the assets folder"):
        load_config(write_config(project_dir, data))
