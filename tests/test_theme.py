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
