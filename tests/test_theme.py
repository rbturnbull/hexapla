import pytest

from hexapla.theme import DEFAULT_BRAND, ThemeError, compile_css


def test_default_theme_keeps_the_hexapla_look():
    css = compile_css(None)
    assert f"--brand: {DEFAULT_BRAND}" in css and "--brand-light: #4e73df" in css
    assert "--bs-primary: #0d6efd" in css  # Bootstrap's own buttons keep Bootstrap's blue
    assert ".btn-primary" in css  # Bootstrap is compiled in
    assert ".sidebar" in css and ".matrix" in css  # and Hexapla's own styles


def test_scss_variables_set_bootstrap_and_hexapla_colours(tmp_path):
    theme = tmp_path / "theme.scss"
    theme.write_text("$primary: #7b2d26;\n")
    css = compile_css(theme)
    assert "--brand: #7b2d26" in css and "--brand-light: #955751" in css
    assert "--bs-primary: #7b2d26" in css


def test_scss_theme_can_import_partials_beside_it(tmp_path):
    (tmp_path / "_colours.scss").write_text("$wine: #7b2d26;\n")
    theme = tmp_path / "theme.scss"
    theme.write_text('@import "colours";\n$primary: $wine;\n')
    assert "--brand: #7b2d26" in compile_css(theme)


def test_css_theme_is_added_after_the_default(tmp_path):
    theme = tmp_path / "theme.css"
    theme.write_text(":root { --brand: #123456; }\n")
    css = compile_css(theme)
    assert css.rstrip().endswith(":root { --brand: #123456; }")
    assert f"--brand: {DEFAULT_BRAND}" in css


def test_scss_errors_name_the_file(tmp_path):
    theme = tmp_path / "broken.scss"
    theme.write_text("$primary: ;\n")
    with pytest.raises(ThemeError, match="broken.scss"):
        compile_css(theme)


def test_hexapla_variables_can_be_set_on_their_own(tmp_path):
    theme = tmp_path / "theme.scss"
    theme.write_text("$hexapla-brand: #2e7d32;\n$hexapla-page-bg: #fafafa;\n")
    css = compile_css(theme)
    assert "--brand: #2e7d32" in css and "--page-bg: #fafafa" in css
    assert "--bs-primary: #0d6efd" in css


BLUES = ["#1c3fae", "#2a78d6", "#cde2fb", "#0d366b", "#eef2fd", "#f7f9ff", "#f1f5fd", "#e4e9f3"]


def test_default_theme_keeps_its_blues():
    css = compile_css(None)
    for name, value in [("accent", "#1c3fae"), ("series-1", "#2a78d6"), ("series-1-soft", "#cde2fb"),
                        ("tint", "#eef2fd"), ("tint-faint", "#f7f9ff"), ("tint-hover", "#f1f5fd"),
                        ("tint-track", "#e4e9f3"), ("ramp-0", "#cde2fb"), ("ramp-6", "#0d366b")]:
        assert f"--{name}: {value}" in css


def test_a_themed_primary_replaces_every_blue(tmp_path):
    theme = tmp_path / "theme.scss"
    theme.write_text("$primary: #226318;\n")
    hexapla_css = compile_css(theme).split(":root{--brand:")[1]  # Hexapla's part, after Bootstrap
    assert "--series-1: #226318" in hexapla_css and "--accent: #1d5414" in hexapla_css
    for blue in BLUES:
        assert blue not in hexapla_css


def test_scripts_take_their_colours_from_the_theme():
    from hexapla.build import STATIC_DIR
    for script in ("common.js", "navigator.js", "pages.js"):
        text = (STATIC_DIR / "js" / script).read_text(encoding="utf-8")
        assert not any(blue in text for blue in BLUES), script
