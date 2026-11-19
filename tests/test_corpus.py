import json
import re

import pytest

from hexapla.build import word_map
from hexapla.config import load_config
from hexapla.conllu import parse_conllu
from hexapla.corpus import CorpusError, load_project, resolve_verse

from .conftest import CONFIG_NAME, PROJECT, read_config, write_config

CONLLU = """# sent_id = V7
# text = εγραψα υμιν .
# verse = 1John 2:14
1	εγραψα	γράφω	VERB	V-	_	0	root	_	Conf=form:0.97
2-3	υμιν.	_	_	_	_	_	_	_	_
2	υμιν	ὑμεῖς	PRON	Pp	_	1	obl	_	_
3	.	.	PUNCT	_	_	_	_	_	SpaceAfter=No
3.1	x	x	X	_	_	_	_	_	_

# sent_id = 12
1	x	x	X	_	_	0	root	_	Ref=ROM_1.7

# sent_id = nothing
1	x	x	X	_	_	0	root	_	_
"""


def load(project_dir=None):
    return load_project(load_config((project_dir or PROJECT) / CONFIG_NAME))


def test_resolve_verse():
    first, second, third = parse_conllu(CONLLU)
    assert resolve_verse(first) == ("B23K02V14", "1 John 2:14")
    assert resolve_verse(second) == ("B06K01V07", "Romans 1:7")  # from MISC Ref=
    assert resolve_verse(third) is None


def test_load_project():
    project = load()
    assert set(project.witnesses) == {"claro-greek", "claro-latin"}
    greek = project.witnesses["claro-greek"]
    assert greek.language == "grc" and greek.label == "Greek" and not greek.rtl
    assert greek.name == "Codex Claromontanus"
    assert greek.licence is None  # the site licence applies
    assert project.witnesses["claro-latin"].licence["name"] == "CC BY 4.0"
    assert len(greek.sentences) == 3

    (pair,) = project.pairs
    assert pair.id == "claro"
    assert pair.title == "Codex Claromontanus"
    assert pair.siglum == "06"
    assert pair.category == "Greek-Latin"
    assert pair.metadata == {"gregoryaland": "06", "vl": "75", "trismegistos": "65887",
                             "date": "6th century", "description": "Greek-Latin bilingual of the Pauline epistles."}
    assert pair.lang_a.id == "greek" and pair.lang_b.id == "latin"
    assert pair.lang_a.witness is greek
    assert [v.id for v in pair.verses] == ["B06K01V07", "B06K01V08", "B06K01V09"]
    assert pair.verses[0].label == "Romans 1:7"
    assert pair.verses[0].links and pair.problems == []
    assert pair.licence is None
    assert project.site_licence["name"] == "CC BY-NC-SA 4.0"
    assert pair.stats()["verses"] == 3 and pair.stats()["greek_words"] > 0


def test_verse_notes_are_keyed_by_verse_id():
    pair = load().pairs[0]
    notes = pair.lang_a.verse_notes("B06K01V07")
    assert notes == [{"folios": ["1r"], "corrections": 1, "lacunae": 0, "supplied": 0, "unclear": 0, "notes": [],
                      "unit": "folio"}]
    assert pair.lang_a.verse_notes("B06K01V08")[0]["folios"] == ["1r", "1v"]
    assert pair.lang_b.verse_notes("B99K01V01") == []


def test_alignment_name_and_licence_override(project_dir):
    data = read_config(project_dir)
    data["alignments"]["claro"].update(name="Claromontanus (GA 06)", licence="CC-BY-4.0")
    pair = load_project(load_config(write_config(project_dir, data))).pairs[0]
    assert pair.title == "Claromontanus (GA 06)"
    assert pair.licence["name"] == "CC BY 4.0"


def test_title_from_two_manuscripts_and_siglum_fallback(project_dir):
    for name in ("greek", "latin"):
        path = project_dir / "claro" / f"claro-{name}.xml"
        text = path.read_text().replace("Codex Claromontanus", f"Codex {name.title()}")
        text = re.sub(r'<altIdentifier type="GA">.*?</altIdentifier>', "", text)
        path.write_text(text)
    pair = load(project_dir).pairs[0]
    assert pair.title == "Codex Greek / Codex Latin"
    assert pair.siglum == "Codex Greek / Codex Latin"
    assert "gregoryaland" not in pair.metadata


def test_manuscript_name_falls_back_to_ga_number_then_title_then_id(project_dir):
    greek = project_dir / "claro" / "claro-greek.xml"
    greek.write_text(greek.read_text().replace("<msName>Codex Claromontanus</msName>", ""))
    latin = project_dir / "claro" / "claro-latin.xml"
    text = latin.read_text().replace("<msName>Codex Claromontanus</msName>", "")
    text = re.sub(r'<altIdentifier type="GA">.*?</altIdentifier>', "", text)
    latin.write_text(text)
    project = load(project_dir)
    assert project.witnesses["claro-greek"].name == "GA 06"
    assert project.witnesses["claro-latin"].name == "A transcription of Romans in Codex Claromontanus (Latin)"
    latin.write_text(re.sub(r"<titleStmt>.*?</titleStmt>", "<titleStmt/>", text, flags=re.S))
    assert load(project_dir).witnesses["claro-latin"].name == "claro-latin"


def test_same_language_on_both_sides_uses_manuscript_ids(project_dir):
    latin = project_dir / "claro" / "claro-latin.xml"
    latin.write_text(latin.read_text().replace('xml:lang="lat"', 'xml:lang="grc"'))
    pair = load(project_dir).pairs[0]
    assert (pair.lang_a.id, pair.lang_b.id) == ("claro-greek", "claro-latin")
    assert pair.category == "Greek-Greek"


def test_rtl_comes_from_the_language(project_dir):
    latin = project_dir / "claro" / "claro-latin.xml"
    latin.write_text(latin.read_text().replace('xml:lang="lat"', 'xml:lang="ar"'))
    pair = load(project_dir).pairs[0]
    assert pair.lang_b.rtl and pair.lang_b.label == "Arabic"


def test_order_of_manuscripts_sets_the_sides(project_dir):
    """ The links file's source is the first manuscript: listing them the other way round mismatches the ids. """
    data = read_config(project_dir)
    data["alignments"]["claro"]["manuscripts"] = ["claro-latin", "claro-greek"]
    pair = load_project(load_config(write_config(project_dir, data))).pairs[0]
    assert pair.lang_a.id == "latin"
    assert any("do not exist" in problem for problem in pair.problems)


def test_problems_are_reported_but_do_not_stop_the_build(project_dir):
    links = project_dir / "claro" / "claro-links.jsonl"
    with open(links, "a") as f:
        f.write(json.dumps({"sent_id": "B06K01V09", "links": [{"source": "999", "target": "1"}]}) + "\n")
        f.write(json.dumps({"sent_id": "elsewhere", "links": [{"source": "1", "target": "1"}]}) + "\n")
    greek = project_dir / "claro" / "claro-greek.conllu"
    greek.write_text(greek.read_text() + "\n# sent_id = extra\n1\tx\tx\tX\t_\t_\t0\troot\t_\t_\n")
    latin = project_dir / "claro" / "claro-latin.conllu"
    latin.write_text(latin.read_text() + "\n# sent_id = extra-latin\n1\tx\tx\tX\t_\t_\t0\troot\t_\t_\n")
    pair = load(project_dir).pairs[0]
    text = " | ".join(pair.problems)
    assert "999-1" in text
    assert "1 sentence(s) only in Greek: extra" in text
    assert "1 sentence(s) only in Latin: extra-latin" in text
    assert "not in both CoNLL-U files: elsewhere" in text
    assert all(link.source != 999 for verse in pair.verses for link in verse.links)


def test_verse_ids_stay_unique(project_dir):
    """ Two sentences naming the same verse get ids from their sent_ids. """
    for name in ("greek", "latin"):
        path = project_dir / "claro" / f"claro-{name}.conllu"
        text = path.read_text()
        path.write_text(text + "\n" + text.split("\n\n")[0].replace("B06K01V07", "again")
                        + "\n\n" + text.split("\n\n")[0].replace("B06K01V07", "AGAIN") + "\n")
    pair = load(project_dir).pairs[0]
    assert [v.id for v in pair.verses][-2:] == ["again", "again-2"]


def test_untitled_sentences_use_their_sent_id(project_dir):
    for name in ("greek", "latin"):
        path = project_dir / "claro" / f"claro-{name}.conllu"
        path.write_text(path.read_text() + "\n# sent_id = Colophon\n1\tx\tx\tX\t_\t_\t0\troot\t_\t_\n")
    verse = load(project_dir).pairs[0].verses[-1]
    assert (verse.id, verse.label) == ("colophon", "Colophon")


@pytest.mark.parametrize("edit, message", [
    (lambda p: p.write_text(p.read_text().replace(' xml:lang="grc"', "")), "has no language: add xml:lang to <text>"),
    (lambda p: p.write_text(p.read_text().replace('<ab n="Rom.1.9">', '<ab n="Rom.1.8">')), "1 verse appears in more than one <ab> (mark a split verse with part=\"I\" ... part=\"F\"): Rom.1.8"),
    (lambda p: p.write_text("<TEI><unclosed>"), "could not read"),
])
def test_tei_errors_stop_the_build(project_dir, edit, message):
    edit(project_dir / "claro" / "claro-greek.xml")
    with pytest.raises(CorpusError) as caught:
        load(project_dir)
    assert message in str(caught.value)
    assert "claro-greek.xml" in str(caught.value)


def test_every_error_is_reported_at_once(project_dir):
    greek = project_dir / "claro" / "claro-greek.conllu"
    greek.write_text(greek.read_text() + "\n" + greek.read_text().split("\n\n")[0] + "\n")
    latin = project_dir / "claro" / "claro-latin.xml"
    latin.write_text(latin.read_text().replace(' xml:lang="lat"', ""))
    with pytest.raises(CorpusError) as caught:
        load(project_dir)
    assert len(caught.value.errors) == 2
    assert "duplicate sent_id 'B06K01V07'" in str(caught.value)
    assert "claro-latin.xml: the transcription has no language" in str(caught.value)


def test_parses_must_share_sentences(project_dir):
    latin = project_dir / "claro" / "claro-latin.conllu"
    latin.write_text(latin.read_text().replace("B06K01V", "Z"))
    with pytest.raises(CorpusError, match="alignment claro: no sent_id is shared by claro-greek.conllu and claro-latin.conllu"):
        load(project_dir)


def test_bad_links_file_stops_the_build(project_dir):
    (project_dir / "claro" / "claro-links.jsonl").write_text("{not json\n")
    with pytest.raises(CorpusError, match="claro-links.jsonl"):
        load(project_dir)


def test_word_map_many_to_many():
    pair = load().pairs[0]
    verse = pair.verses[1]
    mapping = word_map(verse, pair.lang_a, pair.lang_b)
    source = next(link.source for link in verse.links)
    partners = mapping[f"greek-{source}"]
    assert {p["svgId"] for p in partners} == {"latin"}
    assert sum(len(v) for k, v in mapping.items() if k.startswith("greek-")) == len(verse.links)


def test_unreadable_parse_is_reported(project_dir):
    greek = project_dir / "claro" / "claro-greek.conllu"
    greek.write_text("conll-u\n" + greek.read_text())
    with pytest.raises(CorpusError) as caught:
        load(project_dir)
    assert "claro-greek.conllu:1: expected tab-separated CoNLL-U columns" in str(caught.value)
