from bilingualnavigator.bible import components_from_verse_ref



def test_components_from_verse_ref():
    assert components_from_verse_ref("B1K2V3") == (40, 2, 3)
    assert components_from_verse_ref("John 7.9") == (43, 7, 9)
    assert components_from_verse_ref("John 7:9") == (43, 7, 9)
    assert components_from_verse_ref("John7:9") == (43, 7, 9)
    assert components_from_verse_ref("John.7.9") == (43, 7, 9)
