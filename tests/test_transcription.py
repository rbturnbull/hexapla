import pytest
from pathlib import Path

from hexapla.transcription import read_transcription

PROJECT = Path(__file__).parent / "data" / "project"

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
    assert len(t.verses) == 3 and t.errors == []
    assert t.header["language"] is None  # no <text xml:lang>


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
    assert t.errors == []


def test_repeated_verse_numbers_are_an_error(tmp_path):
    """ sa117 labels John 6:21-58 as John.4.21-58: the file is wrong and must be fixed, not relabelled. """
    path = tmp_path / "sa117.xml"
    abs_ = "".join(f'<ab n="John.4.{n}"><w>x</w></ab>' for n in (20, 21, 22, 21, 22))
    path.write_text(f'<TEI xmlns="http://www.tei-c.org/ns/1.0"><text xml:lang="cop"><body>{abs_}</body></text></TEI>')
    t = read_transcription(path)
    assert t.errors == ['2 verses appear in more than one <ab> (mark a split verse with part="I" ... part="F"): '
                        'John.4.21, John.4.22']


def test_verse_split_with_part_attributes_is_fine(tmp_path):
    """ A verse split across pages is two <ab>s marked part="I" and part="F". """
    path = tmp_path / "split.xml"
    path.write_text('<TEI xmlns="http://www.tei-c.org/ns/1.0"><text xml:lang="grc"><body>'
                    '<ab n="B04K20V1" part="I"><w>a</w></ab><pb n="2r"/><ab n="B04K20V1" part="F"><w>b</w></ab>'
                    '</body></text></TEI>')
    t = read_transcription(path)
    assert t.errors == [] and t.verses["B04K20V1"].folios == ["2r"]


def test_manuscript_metadata_from_the_header():
    t = read_transcription(PROJECT / "claro" / "claro-greek.xml")
    h = t.header
    assert h["language"] == "grc"
    assert h["ms_name"] == "Codex Claromontanus"
    assert h["date"] == {"text": "6th century", "when": None, "not_before": "0500", "not_after": "0599"}
    assert h["description"] == "Greek-Latin bilingual of the Pauline epistles."
    assert {i["type"]: i["value"] for i in h["identifiers"]} == {"GA": "06", "VL": "75", "TM": "65887"}
    assert h["licence_name"] == "CC BY 4.0"
    assert h["licence_url"] == "https://creativecommons.org/licenses/by/4.0/"
    assert t.identifier("TM") == "65887" and t.identifier("LDAB") is None

    latin = read_transcription(PROJECT / "claro" / "claro-latin.xml")
    assert latin.header["date"]["text"] == "6th century" and latin.header["description"] == ""
    assert latin.header["licence"] == "" and latin.header["licence_name"] is None


def test_header_without_msdesc(tmp_path):
    path = tmp_path / "bare.xml"
    path.write_text('<TEI xmlns="http://www.tei-c.org/ns/1.0"><teiHeader><fileDesc><titleStmt><title>Bare</title>'
                    '</titleStmt></fileDesc></teiHeader><text xml:lang="lat"><body/></text></TEI>')
    h = read_transcription(path).header
    assert h["title"] == "Bare" and h["ms_name"] == "" and h["date"] is None and h["identifiers"] == []


def test_header_details(tmp_path):
    """ Printed sources, licences named in words, empty identifiers, NTVMR ids, notes, revisions, nomina sacra. """
    path = tmp_path / "details.xml"
    path.write_text("""<TEI xmlns="http://www.tei-c.org/ns/1.0"><teiHeader><fileDesc>
<titleStmt><title>Gothic Romans</title></titleStmt>
<publicationStmt><authority>Project Wulfila</authority>
<availability><p>Licensed under Creative Commons by-nc-sa.</p></availability></publicationStmt>
<sourceDesc><biblStruct><monogr><author>Streitberg</author><title>Die gotische Bibel</title><imprint>1919.</imprint></monogr></biblStruct>
<bibl/>
<msDesc><msIdentifier><idno/><altIdentifier type="TM"><idno/></altIdentifier><altIdentifier type="Liste"><idno>20005</idno></altIdentifier>
<altIdentifier><idno>x1</idno></altIdentifier></msIdentifier></msDesc></sourceDesc>
</fileDesc>
<encodingDesc><projectDesc><p>The project.</p></projectDesc><editorialDecl><p>Decisions.</p></editorialDecl></encodingDesc>
<revisionDesc><change when="2026-11-19" n="2">Added the language.</change></revisionDesc>
</teiHeader>
<text xml:lang="got"><body><!-- a comment --><ab n="Rom.1.1"><w><abbr type="nomSac">xs</abbr></w></ab></body></text></TEI>""")
    t = read_transcription(path)
    h = t.header
    assert h["source"] == ["Streitberg. Die gotische Bibel. 1919"]
    assert h["licence_name"] == "CC BY-NC-SA" and h["authority"] == "Project Wulfila"
    assert h["identifiers"] == [
        {"type": "Liste", "label": "Liste", "value": "20005", "url": "https://ntvmr.uni-muenster.de/manuscript-workspace?docID=20005"},
        {"type": "", "label": "", "value": "x1", "url": None},
    ]
    assert h["shelfmarks"] == [] and h["project"] == ["The project."] and h["editorial"] == ["Decisions."]
    assert h["revisions"] == [{"when": "2026-11-19", "n": "2", "text": "Added the language."}]
    assert t.summary["nomina_sacra"] == 1


def test_non_commercial_licence_in_words(tmp_path):
    path = tmp_path / "nc.xml"
    path.write_text('<TEI><teiHeader><fileDesc><publicationStmt><availability><p>Free for non-commercial use.</p>'
                    '</availability></publicationStmt></fileDesc></teiHeader><text xml:lang="ar"/></TEI>')
    assert read_transcription(path).header["licence_name"] == "free for non-commercial use"


def test_a_placeholder_ab_is_not_a_repeat(tmp_path):
    """ Bezae has an empty <ab n="B03K6V5"> with a note where Luke 6:5 would be, and the verse after 6:10. """
    path = tmp_path / "bezae.xml"
    path.write_text('<TEI xmlns="http://www.tei-c.org/ns/1.0"><text xml:lang="grc"><body>'
                    '<ab n="B03K6V5"><note type="editorial">Luke 6:5 is found after Luke 6:10</note><lb/></ab>'
                    '<ab n="B03K6V10"><w>a</w></ab><ab n="B03K6V5"><w>b</w></ab></body></text></TEI>')
    assert read_transcription(path).errors == []
    no_words = tmp_path / "dcodex.xml"
    no_words.write_text('<TEI><text xml:lang="ar"><body><ab n="B10K1V1"><note>1r</note></ab><ab n="B10K1V1">نص</ab>'
                        '<ab n="B10K1V3"><note>2r</note>ج</ab><ab n="B10K1V3"><note>2v</note></ab>'
                        '<ab n="B10K1V2">ا</ab><ab n="B10K1V2">ب</ab></body></text></TEI>')
    assert read_transcription(no_words).errors == [
        '1 verse appears in more than one <ab> (mark a split verse with part="I" ... part="F"): B10K1V2']


def test_identifier_spellings(tmp_path):
    path = tmp_path / "ids.xml"
    path.write_text('<TEI><teiHeader><fileDesc><sourceDesc><msDesc><msIdentifier>'
                    '<altIdentifier type="Gregory-Aland"><idno>010</idno></altIdentifier>'
                    '<altIdentifier type="VetusLatina"><idno>78</idno></altIdentifier>'
                    '<altIdentifier type="Trismegistos"><idno>999740</idno></altIdentifier>'
                    '</msIdentifier></msDesc></sourceDesc></fileDesc></teiHeader><text xml:lang="lat"/></TEI>')
    t = read_transcription(path)
    assert (t.identifier("GA"), t.identifier("VL"), t.identifier("TM")) == ("010", "78", "999740")
    tm = next(i for i in t.header["identifiers"] if i["type"] == "Trismegistos")
    assert tm["url"] == "https://www.trismegistos.org/text/999740" and tm["label"] == "Trismegistos"


def test_document_title_is_a_ga_number_only_when_it_looks_like_one(tmp_path):
    path = tmp_path / "igntp.xml"
    path.write_text('<TEI><teiHeader><fileDesc><titleStmt><title type="document" n="0278">A transcription of Ephesians in 0278'
                    '</title></titleStmt></fileDesc></teiHeader><text xml:lang="grc"/></TEI>')
    assert read_transcription(path).header["title"] == "A transcription of Ephesians in 0278"


@pytest.mark.parametrize("text, name, url", [
    ("This is an open access work licensed under a Creative Commons Attribution 4.0 International license.",
     "CC BY 4.0", "https://creativecommons.org/licenses/by/4.0/"),
    ("Licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 3.0 License.",
     "CC BY-NC-SA 3.0", "https://creativecommons.org/licenses/by-nc-sa/3.0/"),
    ("Creative Commons Attribution-NoDerivatives 4.0", "CC BY-ND 4.0", "https://creativecommons.org/licenses/by-nd/4.0/"),
])
def test_licence_written_out_in_words(tmp_path, text, name, url):
    path = tmp_path / "words.xml"
    path.write_text(f'<TEI><teiHeader><fileDesc><publicationStmt><availability><p>{text}</p></availability>'
                    '</publicationStmt></fileDesc></teiHeader><text xml:lang="ar"/></TEI>')
    header = read_transcription(path).header
    assert (header["licence_name"], header["licence_url"]) == (name, url)
