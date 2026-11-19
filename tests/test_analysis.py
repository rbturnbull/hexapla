import json
import re

from hexapla import analysis
from hexapla.build import build_site
from hexapla.config import load_config
from hexapla.conllu import Word
from hexapla.corpus import load_project
from hexapla.links import Link

from .conftest import CONFIG_NAME, PROJECT


def load_pair():
    return load_project(load_config(PROJECT / CONFIG_NAME)).pairs[0]



def test_reordering():
    assert analysis.reordering([Link(1, 1), Link(2, 2), Link(3, 3)]) == 0
    assert analysis.reordering([Link(1, 3), Link(2, 2), Link(3, 1)]) == 1
    assert analysis.reordering([Link(1, 1), Link(2, 3), Link(3, 2)]) == 1 / 3
    assert analysis.reordering([Link(1, 1)]) is None


def test_alignment_groups_and_shapes():
    groups = analysis.alignment_groups([Link(1, 1), Link(2, 2), Link(2, 3), Link(4, 5), Link(5, 5)])
    shapes = sorted(analysis.group_shape(a, b) for a, b in groups)
    assert shapes == ["1:1", "1:n", "n:1"]


def test_word_confidence():
    word = Word(id=1, form="x", misc="Conf=form:0.99,lemma:0.9,upos:0.7,head:0.95|SpaceAfter=No")
    assert analysis.word_confidence(word) == 0.7
    assert analysis.word_confidence(Word(id=1, form="x")) is None


def test_summary_and_verse_stats():
    dataset = load_pair()
    verses = analysis.verse_stats(dataset)
    assert [v["id"] for v in verses] == ["B06K01V07", "B06K01V08", "B06K01V09"]
    assert all(0 <= v["coverage"] <= 1 for v in verses)
    summary = analysis.summary(dataset, verses)
    assert summary["links"] == sum(v["links"] for v in verses)
    assert sum(summary["shapes"].values()) > 0
    assert summary["books"] == [{"book": "Romans", "verses": 3}]


def test_correspondences():
    dataset = load_pair()
    matrices = {m["key"]: m for m in analysis.correspondences(dataset)}
    assert {"upos", "case"} <= set(matrices)
    upos = matrices["upos"]
    assert upos["total"] == sum(c["n"] for c in upos["cells"])
    assert "PUNCT" not in upos["rows"]
    cell = upos["cells"][0]
    verse_index, a_id, b_id = cell["ex"][0]
    verse = dataset.verses[verse_index]
    assert any(link.source == a_id and link.target == b_id for link in verse.links)


def test_lexicon_and_review():
    dataset = load_pair()
    greek = {entry["lemma"]: entry for entry in analysis.lexicon(dataset, "a")}
    assert greek["θεός"]["eq"][0][0] == "deus"
    assert greek["θεός"]["aligned"] <= greek["θεός"]["in_aligned"] <= greek["θεός"]["count"]
    review = analysis.review(dataset)
    probable_first = [link["sure"] for link in review["links"]]
    assert probable_first == sorted(probable_first)
    assert all(word["confidence"] < analysis.LOW_CONFIDENCE for word in review["words"])


def test_build_new_pages(tmp_path):
    website = tmp_path / "website"
    build_site(load_project(load_config(PROJECT / CONFIG_NAME)), website)
    ms = website / "alignments" / "claro"
    for page in ("index.html", "lexicon/index.html", "insights/index.html", "review/index.html", "corpus.js"):
        assert (ms / page).exists(), page

    overview = (ms / "index.html").read_text()
    data = json.loads(re.search(r"const OVERVIEW = (.*);</script>", overview).group(1))
    assert len(data["verses"]) == 3
    corpus = json.loads(re.search(r"window.CORPUS = (.*);", (ms / "corpus.js").read_text()).group(1))
    assert corpus[0]["label"] == "Romans 1:7"
    home = (website / "index.html").read_text()
    assert "Codex Claromontanus" in home and "words aligned" in home


def test_equivalent_groups_linked_words_and_marks_gaps():
    from types import SimpleNamespace as W
    from hexapla.analysis import equivalent
    words = {1: W(lemma="in"), 2: W(lemma="Christus"), 3: W(lemma="_"), 4: W(lemma="sum"), 6: W(lemma="non")}
    assert equivalent([2, 1], words) == ("in", "Christus")
    assert equivalent([1, 4], words) == ("in", "…", "sum")
    assert equivalent([2, 3, 4], words) == ("Christus", "sum")  # adjacent through an unlemmatised word
    assert equivalent([4, 6], words) == ("sum", "…", "non")
    assert equivalent([3], words) == ()


def synthetic_pair():
    """ Punctuation, missing and unusable lemmas, links without confidences, a low-confidence parse and an unaligned verse. """
    from types import SimpleNamespace

    from hexapla.conllu import parse_conllu
    from hexapla.corpus import Verse

    a1, a2 = parse_conllu(
        "# sent_id = v1\n"
        "1\talpha\talpha\tNOUN\t_\tCase=Nom\t0\troot\t_\tConf=lemma:0.5,upos:x\n"
        "2\tbeta\t_\tVERB\t_\t_\t1\tdep\t_\t_\n"
        "3\t.\t.\tPUNCT\t_\t_\t1\tpunct\t_\t_\n"
        "4\tgamma\tgamma\tNOUN\t_\t_\t1\tdep\t_\t_\n"
        "\n# sent_id = v2\n1\tdelta\tdelta\tNOUN\t_\t_\t0\troot\t_\t_\n"
    )
    b1, b2 = parse_conllu(
        "# sent_id = v1\n"
        "1\tuno\tunus\tNUM\t_\tCase=Acc\t0\troot\t_\t_\n"
        "2\tdue\tdir/x\tNUM\t_\t_\t1\tdep\t_\t_\n"
        "3\t.\t.\tPUNCT\t_\t_\t1\tpunct\t_\t_\n"
        "4\ttre\t_\tNUM\t_\t_\t1\tdep\t_\t_\n"
        "\n# sent_id = v2\n1\tquattro\tquattuor\tNUM\t_\t_\t0\troot\t_\t_\n"
    )
    links = [Link(1, 1), Link(2, 2, sure=False), Link(3, 3, confidence=0.9), Link(4, 4, confidence=0.9)]
    verses = [Verse("v1", "Verse 1", "v1", a1, b1, links), Verse("v2", "Verse 2", "v2", a2, b2, [])]
    side = lambda id_: SimpleNamespace(id=id_, label=id_.title(), rtl=False)
    return SimpleNamespace(verses=verses, lang_a=side("a"), lang_b=side("b"))


def test_analysis_skips_punctuation_and_unaligned_verses():
    pair = synthetic_pair()
    upos = analysis.correspondences(pair)[0]
    assert "PUNCT" not in upos["rows"] and "PUNCT" not in upos["cols"]
    unaligned = analysis.unaligned_by_upos(pair)
    assert all(row["upos"] != "PUNCT" for row in unaligned["a"])
    assert sum(row["total"] for row in unaligned["a"]) == 3  # verse 2 has no links: left out
    lexicon = {entry["lemma"]: entry for entry in analysis.lexicon(pair, "a")}
    assert "_" not in lexicon and "." not in lexicon
    assert lexicon["gamma"]["eq"] == []  # linked only to a word without a lemma
    review = analysis.review(pair)
    assert [(link["a"], link["b"]) for link in review["links"]] == [(2, 2), (3, 3), (4, 4)]  # sure links without a confidence are skipped
    assert [(word["side"], word["id"], word["confidence"]) for word in review["words"]] == [("a", 1, 0.5)]


def test_lemma_index_and_verse_data_for_awkward_words():
    from hexapla.build import build_lemma_index, linkable_lemma, sentence_js_data

    pair = synthetic_pair()
    index = build_lemma_index(pair)
    assert "dir/x" not in index["b"] and "." not in index["a"]
    assert index["a"]["gamma"]["parallel"] == 1 and index["a"]["gamma"]["aligned"] == {}
    assert index["a"]["delta"]["unaligned"]
    words = pair.verses[0].a.words
    assert not linkable_lemma(words[1]) and not linkable_lemma(words[2]) and linkable_lemma(words[0])
    data = sentence_js_data(pair.verses[0].a, pair.lang_a)
    assert data["lowConf"] == [1] and 2 not in data["lemmaMap"]
