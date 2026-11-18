import json
import re
import shutil
from pathlib import Path

from bilingualnavigator import analysis
from bilingualnavigator.alignment import Link
from bilingualnavigator.build import build_website
from bilingualnavigator.conllu import Word
from bilingualnavigator.dataset import load_dataset, load_datasets

SAMPLE = Path(__file__).parent / "data" / "claromontanus-sample"


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
    dataset = load_dataset(SAMPLE)
    verses = analysis.verse_stats(dataset)
    assert [v["id"] for v in verses] == ["B06K01V07", "B06K01V08", "B06K01V09"]
    assert all(0 <= v["coverage"] <= 1 for v in verses)
    summary = analysis.summary(dataset, verses)
    assert summary["links"] == sum(v["links"] for v in verses)
    assert sum(summary["shapes"].values()) > 0
    assert summary["books"] == [{"book": "Romans", "verses": 3}]


def test_correspondences():
    dataset = load_dataset(SAMPLE)
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
    dataset = load_dataset(SAMPLE)
    greek = {entry["lemma"]: entry for entry in analysis.lexicon(dataset, "a")}
    assert greek["θεός"]["eq"][0][0] == "deus"
    assert greek["θεός"]["aligned"] <= greek["θεός"]["in_aligned"] <= greek["θεός"]["count"]
    review = analysis.review(dataset)
    probable_first = [link["sure"] for link in review["links"]]
    assert probable_first == sorted(probable_first)
    assert all(word["confidence"] < analysis.LOW_CONFIDENCE for word in review["words"])


def test_build_new_pages(tmp_path):
    shutil.copytree(SAMPLE, tmp_path / "datasets" / "claro")
    website = tmp_path / "website"
    build_website(load_datasets(tmp_path / "datasets"), website)
    ms = website / "mss" / "claro"
    for page in ("index.html", "lexicon/index.html", "insights/index.html", "review/index.html", "corpus.js"):
        assert (ms / page).exists(), page

    overview = (ms / "index.html").read_text()
    data = json.loads(re.search(r"const OVERVIEW = (.*);</script>", overview).group(1))
    assert len(data["verses"]) == 3
    corpus = json.loads(re.search(r"window.CORPUS = (.*);", (ms / "corpus.js").read_text()).group(1))
    assert corpus[0]["label"] == "Romans 1:7"
    home = (website / "index.html").read_text()
    assert "Codex Claromontanus (sample)" in home and "words aligned" in home


def test_equivalent_groups_linked_words_and_marks_gaps():
    from types import SimpleNamespace as W
    from bilingualnavigator.analysis import equivalent
    words = {1: W(lemma="in"), 2: W(lemma="Christus"), 3: W(lemma="_"), 4: W(lemma="sum"), 6: W(lemma="non")}
    assert equivalent([2, 1], words) == ("in", "Christus")
    assert equivalent([1, 4], words) == ("in", "…", "sum")
    assert equivalent([2, 3, 4], words) == ("Christus", "sum")  # adjacent through an unlemmatised word
    assert equivalent([4, 6], words) == ("sum", "…", "non")
    assert equivalent([3], words) == ()
