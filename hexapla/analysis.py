"""
Statistics over a dataset for the overview, lexicon, insights and review pages.

Everything here is plain data (dicts, lists, numbers) so it can be dumped to JSON for the pages.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from .links import Link
from .conllu import Sentence, Word
from .corpus import AlignedPair as Dataset, Verse

LOW_CONFIDENCE = 0.8  # MCParser's default refinement threshold
CONFIDENCE_COLUMNS = ("lemma", "upos", "feats", "head", "deprel")
NOMINAL_UPOS = {"NOUN", "PROPN", "PRON", "ADJ", "DET", "NUM"}
VERBAL_UPOS = {"VERB", "AUX"}
MISSING = "—"
MAX_EXAMPLES = 12

# The grammatical correspondences shown on the insights page: (key, title, feature, description)
FEATURES = [
    ("Case", "Case", "How the cases of one language are rendered in the other"),
    ("Number", "Number", "Singular, plural and dual across the translation"),
    ("Tense", "Tense", "Tense of aligned verbs"),
    ("Aspect", "Aspect", "Verbal aspect of aligned verbs"),
    ("Mood", "Mood", "Indicative, subjunctive, imperative... of aligned verbs"),
    ("VerbForm", "Verb form", "Finite verbs, participles, infinitives..."),
    ("Voice", "Voice", "Active, middle and passive"),
]


def word_confidence(word: Word) -> float | None:
    """ The lowest MCParser confidence (MISC ``Conf=``) over the columns that matter for display. """
    conf = word.misc_dict.get("Conf")
    if not conf:
        return None
    values = {}
    for item in conf.split(","):
        column, _, value = item.partition(":")
        try:
            values[column] = float(value)
        except ValueError:
            continue
    relevant = [values[c] for c in CONFIDENCE_COLUMNS if c in values]
    return min(relevant) if relevant else None


def feats_dict(word: Word) -> dict[str, str]:
    if not word.feats or word.feats == "_":
        return {}
    return dict(item.split("=", 1) for item in word.feats.split("|") if "=" in item)


def reordering(links: list[Link]) -> float | None:
    """
    Share of link pairs that cross (0 = the two texts keep the same word order, 1 = fully reversed).
    Pairs sharing a word on either side are ignored. None when there are fewer than two such pairs.
    """
    pairs = crossing = 0
    for i, first in enumerate(links):
        for second in links[i + 1:]:
            ds = first.source - second.source
            dt = first.target - second.target
            if ds == 0 or dt == 0:
                continue
            pairs += 1
            if ds * dt < 0:
                crossing += 1
    return crossing / pairs if pairs >= 2 else None


def alignment_groups(links: list[Link]) -> list[tuple[set[int], set[int]]]:
    """ Connected groups of linked words: ({A ids}, {B ids}). """
    parent: dict[tuple[str, int], tuple[str, int]] = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for link in links:
        parent[find(("a", link.source))] = find(("b", link.target))
    groups: dict[tuple[str, int], tuple[set[int], set[int]]] = defaultdict(lambda: (set(), set()))
    for node in list(parent):
        side, word_id = node
        groups[find(node)][0 if side == "a" else 1].add(word_id)
    return list(groups.values())


def group_shape(a_ids: set[int], b_ids: set[int]) -> str:
    a = "1" if len(a_ids) == 1 else "n"
    b = "1" if len(b_ids) == 1 else "n"
    return {"11": "1:1", "1n": "1:n", "n1": "n:1", "nn": "n:m"}[a + b]


@dataclass
class VerseStats:
    verse: Verse
    index: int

    def as_dict(self) -> dict:
        verse = self.verse
        aligned_a = {link.source for link in verse.links}
        aligned_b = {link.target for link in verse.links}
        words_a, words_b = len(verse.a.words), len(verse.b.words)
        confidences = [link.confidence for link in verse.links if link.confidence is not None]
        word_confs = [c for w in verse.a.words + verse.b.words if (c := word_confidence(w)) is not None]
        return {
            "i": self.index,
            "id": verse.id,
            "label": verse.label,
            "words_a": words_a,
            "words_b": words_b,
            "links": len(verse.links),
            "probable": sum(1 for link in verse.links if not link.sure),
            "coverage_a": round(len(aligned_a) / words_a, 3) if words_a else 0,
            "coverage_b": round(len(aligned_b) / words_b, 3) if words_b else 0,
            "coverage": round((len(aligned_a) + len(aligned_b)) / (words_a + words_b), 3) if words_a + words_b else 0,
            "link_confidence": round(sum(confidences) / len(confidences), 3) if confidences else None,
            "reordering": None if (r := reordering(verse.links)) is None else round(r, 3),
            "parse_confidence": round(sum(word_confs) / len(word_confs), 3) if word_confs else None,
            "low_confidence_words": sum(1 for c in word_confs if c < LOW_CONFIDENCE),
        }


def verse_stats(dataset: Dataset) -> list[dict]:
    return [VerseStats(verse, i).as_dict() for i, verse in enumerate(dataset.verses)]


def summary(dataset: Dataset, verses: list[dict] | None = None) -> dict:
    verses = verses if verses is not None else verse_stats(dataset)
    links = [link for verse in dataset.verses for link in verse.links]
    words_a = sum(v["words_a"] for v in verses)
    words_b = sum(v["words_b"] for v in verses)
    aligned_a = sum(round(v["coverage_a"] * v["words_a"]) for v in verses)
    aligned_b = sum(round(v["coverage_b"] * v["words_b"]) for v in verses)
    confidences = [link.confidence for link in links if link.confidence is not None]
    reorderings = [v["reordering"] for v in verses if v["reordering"] is not None]
    parse = [v["parse_confidence"] for v in verses if v["parse_confidence"] is not None]

    shapes = Counter()
    for verse in dataset.verses:
        for a_ids, b_ids in alignment_groups(verse.links):
            shapes[group_shape(a_ids, b_ids)] += 1

    return {
        "verses": len(verses),
        "aligned_verses": sum(1 for v in verses if v["links"]),
        "words_a": words_a,
        "words_b": words_b,
        "aligned_a": aligned_a,
        "aligned_b": aligned_b,
        "coverage_a": aligned_a / words_a if words_a else 0,
        "coverage_b": aligned_b / words_b if words_b else 0,
        "links": len(links),
        "sure": sum(1 for link in links if link.sure),
        "probable": sum(1 for link in links if not link.sure),
        "link_confidence": sum(confidences) / len(confidences) if confidences else None,
        "reordering": sum(reorderings) / len(reorderings) if reorderings else None,
        "parse_confidence": sum(parse) / len(parse) if parse else None,
        "low_confidence_words": sum(v["low_confidence_words"] for v in verses),
        "shapes": {shape: shapes.get(shape, 0) for shape in ("1:1", "1:n", "n:1", "n:m")},
        "books": books(dataset),
    }


def books(dataset: Dataset) -> list[dict]:
    """ Verse counts per book, in order of first appearance. """
    counts: dict[str, int] = {}
    for verse in dataset.verses:
        book = verse.label.rsplit(" ", 1)[0] if ":" in verse.label else "Other"
        counts[book] = counts.get(book, 0) + 1
    return [{"book": book, "verses": n} for book, n in counts.items()]


class Matrix:
    """ Counts of (A value, B value) pairs with a few examples per cell. """

    def __init__(self):
        self.counts: Counter = Counter()
        self.examples: dict[tuple[str, str], list] = defaultdict(list)

    def add(self, a_value: str, b_value: str, verse_index: int, a_id: int, b_id: int):
        key = (a_value, b_value)
        self.counts[key] += 1
        examples = self.examples[key]
        if len(examples) < MAX_EXAMPLES and not any(e[0] == verse_index and e[1] == a_id for e in examples):
            examples.append([verse_index, a_id, b_id])

    def as_dict(self) -> dict:
        row_totals, col_totals = Counter(), Counter()
        for (a, b), n in self.counts.items():
            row_totals[a] += n
            col_totals[b] += n

        def order(totals):
            # Most frequent first, the "missing" value last.
            return sorted(totals, key=lambda v: (v == MISSING, -totals[v], v))

        return {
            "rows": order(row_totals),
            "cols": order(col_totals),
            "cells": [
                {"a": a, "b": b, "n": n, "ex": self.examples[(a, b)]}
                for (a, b), n in sorted(self.counts.items(), key=lambda item: -item[1])
            ],
            "total": sum(self.counts.values()),
        }


def correspondences(dataset: Dataset) -> list[dict]:
    """ Part of speech and morphological feature correspondences across alignment links. """
    upos = Matrix()
    features = {key: Matrix() for key, _, _ in FEATURES}

    for index, verse in enumerate(dataset.verses):
        words_a = {w.id: w for w in verse.a.words}
        words_b = {w.id: w for w in verse.b.words}
        for link in verse.links:
            a, b = words_a[link.source], words_b[link.target]
            if a.upos == "PUNCT" or b.upos == "PUNCT":
                continue
            upos.add(a.upos, b.upos, index, a.id, b.id)
            fa, fb = feats_dict(a), feats_dict(b)
            for key, _, _ in FEATURES:
                if key in fa or key in fb:
                    features[key].add(fa.get(key, MISSING), fb.get(key, MISSING), index, a.id, b.id)

    result = [{"key": "upos", "title": "Part of speech",
               "description": "Universal part-of-speech tags of aligned words", **upos.as_dict()}]
    for key, title, description in FEATURES:
        matrix = features[key].as_dict()
        if matrix["total"]:
            result.append({"key": key.lower(), "title": title, "description": description, **matrix})
    return result


def unaligned_by_upos(dataset: Dataset) -> dict[str, list[dict]]:
    """ For each side: per part of speech, how many words have no counterpart. """
    result = {}
    for side in ("a", "b"):
        totals, unaligned = Counter(), Counter()
        examples: dict[str, list] = defaultdict(list)
        for index, verse in enumerate(dataset.verses):
            sentence = verse.a if side == "a" else verse.b
            linked = {link.source if side == "a" else link.target for link in verse.links}
            if not verse.links:
                continue  # unaligned verses say nothing about translation technique
            for word in sentence.words:
                if word.upos == "PUNCT":
                    continue
                totals[word.upos] += 1
                if word.id not in linked:
                    unaligned[word.upos] += 1
                    if len(examples[word.upos]) < MAX_EXAMPLES:
                        examples[word.upos].append([index, word.id])
        rows = [
            {"upos": upos, "total": totals[upos], "unaligned": unaligned[upos],
             "share": unaligned[upos] / totals[upos], "ex": examples[upos]}
            for upos in totals
        ]
        result[side] = sorted(rows, key=lambda r: (-r["share"], -r["total"]))
    return result


GAP = "…"


def equivalent(partner_ids: list[int], other_words: dict) -> tuple[str, ...]:
    """
    The lemmas a word is linked to, in text order, as one equivalent: "in Christus" for one word
    rather than "in" and "Christus". Words that are not next to each other are separated by "…".
    """
    lemmas: list[str] = []
    previous = None
    for partner_id in sorted(set(partner_ids)):
        partner = other_words.get(partner_id)
        if partner and partner.lemma and partner.lemma != "_":
            if lemmas and previous is not None and partner_id - previous > 1 and lemmas[-1] != GAP:
                lemmas.append(GAP)
            lemmas.append(partner.lemma)
        previous = partner_id
    return tuple(lemmas)


def lexicon(dataset: Dataset, side: str, top: int = 6) -> list[dict]:
    """ Each lemma of one side with its frequency, share aligned and most frequent equivalents. """
    entries: dict[str, dict] = {}
    for verse in dataset.verses:
        this, other = (verse.a, verse.b) if side == "a" else (verse.b, verse.a)
        other_words = {w.id: w for w in other.words}
        partners: dict[int, list[int]] = defaultdict(list)
        for link in verse.links:
            if side == "a":
                partners[link.source].append(link.target)
            else:
                partners[link.target].append(link.source)
        for word in this.words:
            if word.upos == "PUNCT" or not word.lemma or word.lemma == "_":
                continue
            entry = entries.setdefault(word.lemma, {"count": 0, "aligned": 0, "in_aligned": 0, "upos": Counter(),
                                                    "forms": Counter(), "eq": Counter(), "verses": set()})
            entry["count"] += 1
            entry["in_aligned"] += bool(verse.links)
            entry["upos"][word.upos] += 1
            entry["forms"][word.form] += 1
            entry["verses"].add(verse.id)
            ids = partners.get(word.id, [])
            if ids:
                entry["aligned"] += 1
            if lemmas := equivalent(ids, other_words):
                entry["eq"][lemmas] += 1
    return sorted(
        (
            {
                "lemma": lemma,
                "upos": entry["upos"].most_common(1)[0][0],
                "count": entry["count"],
                "aligned": entry["aligned"],
                "in_aligned": entry["in_aligned"],
                "verses": len(entry["verses"]),
                "forms": len(entry["forms"]),
                # [label, count] or, for several linked words, [label, count, [lemma, ...]]
                "eq": [[" ".join(lemmas), n] + ([list(lemmas)] if len(lemmas) > 1 else [])
                       for lemmas, n in entry["eq"].most_common(top)],
                "eq_total": len(entry["eq"]),
            }
            for lemma, entry in entries.items()
        ),
        key=lambda e: (-e["count"], e["lemma"]),
    )


def review(dataset: Dataset, limit: int = 300) -> dict:
    """ The links and words most worth checking: least confident first. """
    links, words = [], []
    for index, verse in enumerate(dataset.verses):
        words_a = {w.id: w for w in verse.a.words}
        words_b = {w.id: w for w in verse.b.words}
        for link in verse.links:
            if link.confidence is None and link.sure:
                continue
            links.append({
                "v": index, "a": link.source, "b": link.target, "sure": link.sure,
                "confidence": link.confidence, "agent": link.agent,
                "a_form": words_a[link.source].form, "b_form": words_b[link.target].form,
            })
        for side, sentence in (("a", verse.a), ("b", verse.b)):
            for word in sentence.words:
                if word.upos == "PUNCT":
                    continue
                confidence = word_confidence(word)
                if confidence is not None and confidence < LOW_CONFIDENCE:
                    words.append({"v": index, "side": side, "id": word.id, "form": word.form, "lemma": word.lemma,
                                  "upos": word.upos, "deprel": word.deprel, "confidence": confidence})
    links.sort(key=lambda l: (l["sure"], l["confidence"] if l["confidence"] is not None else 1))
    words.sort(key=lambda w: w["confidence"])
    return {"links": links[:limit], "links_total": len(links), "words": words[:limit], "words_total": len(words)}


def corpus(dataset: Dataset) -> list[dict]:
    """ Compact verse texts for pages that show examples: forms, ids and no-space-after ids per side. """
    def side(sentence: Sentence):
        return {"ids": [w.id for w in sentence.words], "forms": [w.form for w in sentence.words],
                "ns": sentence.no_space_after}
    return [{"id": v.id, "label": v.label, "a": side(v.a), "b": side(v.b)} for v in dataset.verses]
