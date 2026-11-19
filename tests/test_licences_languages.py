import pytest

from hexapla.languages import is_rtl, language_name
from hexapla.licences import licence_info


@pytest.mark.parametrize("value, name, url", [
    ("CC-BY-4.0", "CC BY 4.0", "https://creativecommons.org/licenses/by/4.0/"),
    ("CC-BY-NC-SA-4.0", "CC BY-NC-SA 4.0", "https://creativecommons.org/licenses/by-nc-sa/4.0/"),
    ("cc-by-nc-nd-3.0", "CC BY-NC-ND 3.0", "https://creativecommons.org/licenses/by-nc-nd/3.0/"),
    ("CC-BY-NC-SA", "CC BY-NC-SA 4.0", "https://creativecommons.org/licenses/by-nc-sa/4.0/"),
    ("CC0-1.0", "CC0 1.0", "https://creativecommons.org/publicdomain/zero/1.0/"),
    ("CC0", "CC0 1.0", "https://creativecommons.org/publicdomain/zero/1.0/"),
    ("https://example.org/terms", "https://example.org/terms", "https://example.org/terms"),
    ("All rights reserved", "All rights reserved", None),
])
def test_licence_info(value, name, url):
    assert licence_info(value) == {"id": value, "name": name, "url": url}


def test_no_licence():
    assert licence_info(None) is None
    assert licence_info("") is None


@pytest.mark.parametrize("code, name", [
    ("grc", "Greek"), ("lat", "Latin"), ("la", "Latin"), ("ar", "Arabic"), ("arb", "Arabic"),
    ("cop", "Coptic"), ("cop-x-sa", "Coptic"), ("got", "Gothic"), ("syc", "Syriac"), ("en-GB", "English"),
    ("xyz", "XYZ"),
])
def test_language_name(code, name):
    assert language_name(code) == name


def test_rtl():
    assert is_rtl("ar") and is_rtl("arb") and is_rtl("syc") and is_rtl("he")
    assert not is_rtl("grc") and not is_rtl("cop")
