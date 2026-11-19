import pytest

from hexapla.bible import components_from_verse_ref, get_book_id, read_verse_ref


def test_components_from_verse_ref():
    assert components_from_verse_ref("B1K2V3") == (40, 2, 3)
    assert components_from_verse_ref("John 7.9") == (43, 7, 9)
    assert components_from_verse_ref("John 7:9") == (43, 7, 9)
    assert components_from_verse_ref("John7:9") == (43, 7, 9)
    assert components_from_verse_ref("John.7.9") == (43, 7, 9)
    assert components_from_verse_ref("7:9") == (None, 7, 9)
    assert components_from_verse_ref("12") == (None, None, 12)
    assert components_from_verse_ref("Jude 5") == (65, 1, 5)


@pytest.mark.parametrize("ref", ["John 5", "nonsense", "John:5"])
def test_unreadable_refs(ref):
    with pytest.raises(Exception, match="Cannot interpret verse"):
        components_from_verse_ref(ref)


def test_book_names():
    assert get_book_id("Romans") == 45
    assert get_book_id("rom") == 45
    assert get_book_id("1cor") == 46
    assert get_book_id("Matt") == 40
    assert get_book_id("Phlm") == 57  # an alternative abbreviation
    assert get_book_id("Gen") == 1
    assert get_book_id("xyz") is None


def test_read_verse_ref():
    assert read_verse_ref("Rom.1.7") == ("B06K01V07", "Romans 1:7")
