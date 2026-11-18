from bilingualnavigator.transcription import read_transcription

TEI = """<?xml version="1.0" encoding="utf-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
<teiHeader><fileDesc>
<titleStmt><title>A Transcription of John in GA 999</title><title type="document" key="20999" n="999">GA 999</title>
<respStmt><resp>Transcribed by</resp><name>A. Scribe</name></respStmt></titleStmt>
<editionStmt><edition n="1.0">Version 1.0</edition></editionStmt>
<publicationStmt><publisher><name type="org">ITSEE</name></publisher>
<availability><p>Licensed under a Creative Commons Attribution 4.0 International License (CC BY 4.0). See <ptr target="https://creativecommons.org/licenses/by/4.0/"/>.</p></availability></publicationStmt>
<sourceDesc><msDesc><msIdentifier><settlement>Paris</settlement><altIdentifier type="TM"><idno>123</idno></altIdentifier></msIdentifier></msDesc></sourceDesc>
</fileDesc></teiHeader>
<text><body><div type="book" n="John"><div type="chapter" n="John.4">
<pb n="1r" type="folio"/>
<ab n="John.4.1"><w>a</w><app><rdg type="orig"><w>b</w></rdg><rdg type="corr"><w>c</w></rdg></app></ab>
<ab n="John.4.2"><w>d</w><pb n="1v" type="folio"/><w>e<unclear>f</unclear></w><gap reason="lacuna" unit="line"/></ab>
<ab n="John.4.3"><w>g</w><pb n="2r" type="folio"/></ab>
<ab n="John.4.1"><w>h</w></ab>
</div></div></body></text></TEI>
"""


def test_read_transcription(tmp_path):
    path = tmp_path / "t.xml"
    path.write_text(TEI, encoding="utf-8")

    t = read_transcription(path)
    assert t.header["title"] == "A Transcription of John in GA 999"
    assert t.header["licence_name"] == "CC BY 4.0"
    assert t.header["responsibility"] == [{"resp": "Transcribed by", "names": ["A. Scribe"]}]
    assert {i["type"]: i["url"] for i in t.header["identifiers"]}["TM"] == "https://www.trismegistos.org/text/123"
    assert t.summary["folios"] == ["1r", "1v", "2r"]
    assert t.summary["corrections"] == 1 and t.summary["lacunae"] == 1 and t.summary["unclear"] == 1
    assert t.verses["John.4.1"].corrections == 1
    assert t.verses["John.4.2"].folios == ["1r", "1v"]
    assert t.verses["John.4.3"].folios == ["1v"]  # the break to 2r after its last word does not count
    # The numbers restart at the second John.4.1: left out unless relabelled.
    assert len(t.verses) == 3 and t.problems

    relabelled = read_transcription(path, renumber_restarts=["John.6"])
    assert relabelled.verses["John.6.1"].folios == ["2r"]
    assert relabelled.verses["John.4.1"].corrections == 1


def test_dcodex_and_ntvmr_variants(tmp_path):
    """ D-Codex: no namespace, no <w>, folios as <note>1r</note>, bare <gap/>.
    NTVMR: licence as HTML in CDATA, two msIdentifiers, numbered pages. """
    dcodex = tmp_path / "ar.xml"
    dcodex.write_text("""<TEI><teiHeader><fileDesc><titleStmt><title>Transcription of X</title></titleStmt></fileDesc></teiHeader>
<text><body>
<ab n="B01K13V46"><gap/><note type="editorial">1r</note>__وه كثير الثمن
<note type="editorial">ذ</note>هب فباع</ab>
<ab n="B01K13V47">يضا <note type="editorial">1v</note>يشبه</ab>
</body></text></TEI>""", encoding="utf-8")
    t = read_transcription(dcodex)
    assert t.summary["folios"] == ["1r", "1v"] and t.summary["unit"] == "folio"
    assert t.summary["words"] == 7 and t.summary["lacunae"] == 1
    assert t.verses["B01K13V46"].folios == ["1r"] and t.verses["B01K13V46"].notes == ["ذ"]
    assert t.verses["B01K13V47"].folios == ["1r", "1v"]

    ntvmr = tmp_path / "grc.xml"
    ntvmr.write_text("""<TEI xmlns="http://www.tei-c.org/ns/1.0"><teiHeader><fileDesc>
<titleStmt><title type="document" n="0136">0136</title></titleStmt>
<publicationStmt><availability><p><![CDATA[Licensed under a <a href="https://creativecommons.org/licenses/by/4.0/">CC licence</a>]]></p></availability></publicationStmt>
<sourceDesc><msDesc><msIdentifier><settlement>Sinai</settlement><idno>Harris 9</idno></msIdentifier></msDesc></sourceDesc>
<sourceDesc><msDesc><msIdentifier><settlement>St. Petersburg</settlement><idno>Gr. 281</idno></msIdentifier></msDesc></sourceDesc>
</fileDesc></teiHeader>
<text><body><pb n="7" type="page"/><ab n="B01K13V46"><w>τιμον</w></ab></body></text></TEI>""", encoding="utf-8")
    t = read_transcription(ntvmr)
    assert t.header["title"] == "GA 0136"
    assert t.header["licence_name"] == "CC BY 4.0" and t.header["licence_url"].startswith("https://creativecommons.org")
    assert "<" not in t.header["licence"]
    assert [m["idno"] for m in t.header["shelfmarks"]] == ["Harris 9", "Gr. 281"]
    assert t.summary["unit"] == "page" and t.verses["B01K13V46"].folios == ["7"]


def test_out_of_order_fragments_are_not_a_restart(tmp_path):
    """ ac1 has John.13.13 before 13.10-12: new numbers, so they keep their labels (unlike a restart, which repeats). """
    path = tmp_path / "ac1.xml"
    abs_ = "".join(f'<ab n="John.13.{n}"><w>x</w></ab>' for n in (1, 2, 13, 10, 11, 12))
    path.write_text(f'<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body><div type="chapter" n="John.13">{abs_}</div></body></text></TEI>')
    t = read_transcription(path)
    assert list(t.verses) == ["John.13.1", "John.13.2", "John.13.13", "John.13.10", "John.13.11", "John.13.12"]
    assert t.problems == []
