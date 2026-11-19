"""
Loads a project from its config: each manuscript (a TEI transcription and its CoNLL-U parse) becomes a
``Witness``, and each alignment an ``AlignedPair`` of two witnesses with their verses paired by ``sent_id``.

Mistakes in the files that the site cannot show correctly (a TEI file without a language, a verse number
used twice, a duplicate ``sent_id``) are collected into one ``CorpusError``. Smaller ones (a sentence in only
one parse, a link to a word that does not exist) are listed in the pair's ``problems`` and the site is built.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .bible import read_verse_ref
from .config import Alignment, Config, Manuscript
from .conllu import Sentence, read_conllu
from .languages import is_rtl, language_name
from .licences import licence_info
from .links import Link, read_links
from .transcription import Transcription, VerseNotes, read_transcription


class CorpusError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("\n".join(errors))


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(text).strip().lower()).strip("-")
    return slug or "x"


def _verse_id(ref: str) -> str | None:
    """ The site's id for a verse reference (``John.1.25`` → ``B04K01V25``), or None if it is not one. """
    try:
        verse_id, _ = read_verse_ref(ref.replace("_", " "))
    except Exception:
        return None
    return None if verse_id.startswith("B-") else verse_id


def resolve_verse(sentence: Sentence) -> tuple[str, str] | None:
    """ ``(verse_id, label)`` such as ``("B06K01V07", "Romans 1:7")`` if the sentence names a verse. """
    for candidate in sentence.ref_candidates():
        verse_id = _verse_id(candidate)
        if verse_id:
            return verse_id, read_verse_ref(candidate.replace("_", " "))[1] or candidate
    return None


@dataclass
class Witness:
    """ One manuscript text: a TEI transcription with its CoNLL-U parse. """
    id: str
    manuscript: Manuscript
    transcription: Transcription
    sentences: dict[str, Sentence]

    @property
    def language(self) -> str:
        return self.transcription.header["language"]

    @property
    def label(self) -> str:
        return language_name(self.language)

    @property
    def rtl(self) -> bool:
        return is_rtl(self.language)

    @property
    def name(self) -> str:
        header = self.transcription.header
        ga = self.transcription.identifier("GA")
        return header["ms_name"] or (f"GA {ga}" if ga else "") or header["title"] or self.id

    @property
    def licence(self) -> dict | None:
        """ The parsing licence, if it differs from the site's. """
        return licence_info(self.manuscript.parsing_licence)

    def verse_notes(self, verse_id: str) -> list[dict]:
        notes = self.transcription.verses.get(verse_id)
        if notes is None:
            return []
        return [{**notes.to_dict(), "unit": self.transcription.summary["unit"]}]


@dataclass
class Language:
    """ One side of an aligned pair. ``id`` names it in URLs and the verse page's SVGs. """
    id: str
    witness: Witness

    @property
    def label(self) -> str:
        return self.witness.label

    @property
    def rtl(self) -> bool:
        return self.witness.rtl

    @property
    def sentences(self) -> dict[str, Sentence]:
        return self.witness.sentences

    def verse_notes(self, verse_id: str) -> list[dict]:
        return self.witness.verse_notes(verse_id)


@dataclass
class Verse:
    id: str  # used in URLs
    label: str  # shown to readers
    sent_id: str
    a: Sentence
    b: Sentence
    links: list[Link]


@dataclass
class AlignedPair:
    id: str
    alignment: Alignment
    title: str
    siglum: str
    metadata: dict
    lang_a: Language
    lang_b: Language
    verses: list[Verse]
    problems: list[str] = field(default_factory=list)

    @property
    def category(self) -> str:
        return f"{self.lang_a.label}-{self.lang_b.label}"

    @property
    def licence(self) -> dict | None:
        """ The alignment's licence, if it differs from the site's. """
        return licence_info(self.alignment.licence)

    @property
    def witnesses(self) -> list[Witness]:
        return [self.lang_a.witness, self.lang_b.witness]

    def stats(self) -> dict:
        links = [link for verse in self.verses for link in verse.links]
        return {
            "verses": len(self.verses),
            "aligned_verses": sum(1 for verse in self.verses if verse.links),
            "links": len(links),
            "sure": sum(1 for link in links if link.sure),
            "probable": sum(1 for link in links if not link.sure),
            f"{self.lang_a.id}_words": sum(len(verse.a.words) for verse in self.verses),
            f"{self.lang_b.id}_words": sum(len(verse.b.words) for verse in self.verses),
        }


@dataclass
class Project:
    config: Config
    witnesses: dict[str, Witness]
    pairs: list[AlignedPair]

    @property
    def site_licence(self) -> dict | None:
        return licence_info(self.config.theme.licence)


def _key_by_verse_id(verses: dict[str, VerseNotes]) -> dict[str, VerseNotes]:
    """ Keys a transcription's verse notes by the site's verse ids (B04K01V25), whatever the TEI's style. """
    return {_verse_id(ref) or ref: notes for ref, notes in verses.items()}


def load_witness(manuscript: Manuscript, errors: list[str]) -> Witness | None:
    found: list[str] = []
    transcription = None
    try:
        transcription = read_transcription(manuscript.tei)
    except Exception as err:
        found.append(f"{manuscript.tei}: could not read the TEI: {err}")
    if transcription is not None:
        if not transcription.header["language"]:
            found.append(f"{manuscript.tei}: the transcription has no language: add xml:lang to <text>")
        found.extend(f"{manuscript.tei}: {error}" for error in transcription.errors)
        transcription.verses = _key_by_verse_id(transcription.verses)

    sentences: dict[str, Sentence] = {}
    try:
        parsed = read_conllu(manuscript.parsing)
    except ValueError as err:  # the message names the file and line
        found.append(str(err))
        parsed = []
    for sentence in parsed:
        if sentence.sent_id in sentences:
            found.append(f"{manuscript.parsing}: duplicate sent_id {sentence.sent_id!r}")
        sentences[sentence.sent_id] = sentence

    errors.extend(found)
    if found:
        return None
    return Witness(id=manuscript.id, manuscript=manuscript, transcription=transcription, sentences=sentences)


def _first(witnesses: list[Witness], kind: str) -> str | None:
    return next((value for witness in witnesses if (value := witness.transcription.identifier(kind))), None)


def load_pair(alignment: Alignment, witness_a: Witness, witness_b: Witness, errors: list[str]) -> AlignedPair | None:
    ids = ((slugify(witness_a.label), slugify(witness_b.label)) if witness_a.label != witness_b.label
           else (witness_a.id, witness_b.id))
    lang_a, lang_b = Language(ids[0], witness_a), Language(ids[1], witness_b)
    problems: list[str] = []

    try:
        links_by_sentence = read_links(alignment.links)
    except ValueError as err:
        errors.append(str(err))
        return None

    only_a = [sent_id for sent_id in lang_a.sentences if sent_id not in lang_b.sentences]
    only_b = [sent_id for sent_id in lang_b.sentences if sent_id not in lang_a.sentences]
    if only_a:
        problems.append(f"{len(only_a)} sentence(s) only in {lang_a.label}: {', '.join(only_a[:5])}")
    if only_b:
        problems.append(f"{len(only_b)} sentence(s) only in {lang_b.label}: {', '.join(only_b[:5])}")

    # Pair sentences by sent_id, in the order of side A's file.
    verses: list[Verse] = []
    used_ids: set[str] = set()
    for sent_id, sentence_a in lang_a.sentences.items():
        sentence_b = lang_b.sentences.get(sent_id)
        if sentence_b is None:
            continue
        resolved = resolve_verse(sentence_a) or resolve_verse(sentence_b)
        verse_id, label = resolved if resolved else (slugify(sent_id), sent_id)
        if verse_id in used_ids:
            base, n = slugify(sent_id), 2
            verse_id = base
            while verse_id in used_ids:
                verse_id = f"{base}-{n}"
                n += 1
        used_ids.add(verse_id)

        links = links_by_sentence.get(sent_id, [])
        bad = [link for link in links if link.source not in sentence_a.word_ids or link.target not in sentence_b.word_ids]
        if bad:
            problems.append(f"{sent_id}: {len(bad)} link(s) to words that do not exist, ignored: "
                            + " ".join(f"{link.source}-{link.target}" for link in bad[:5]))
            links = [link for link in links if link not in bad]
        verses.append(Verse(id=verse_id, label=label, sent_id=sent_id, a=sentence_a, b=sentence_b, links=links))

    orphan = [sent_id for sent_id in links_by_sentence if sent_id not in lang_a.sentences or sent_id not in lang_b.sentences]
    if orphan:
        problems.append(f"{len(orphan)} aligned sent_id(s) not in both CoNLL-U files: {', '.join(orphan[:5])}")

    if not verses:
        errors.append(f"alignment {alignment.id}: no sent_id is shared by {witness_a.manuscript.parsing.name} "
                      f"and {witness_b.manuscript.parsing.name}")
        return None

    witnesses = [witness_a, witness_b]
    names = list(dict.fromkeys(witness.name for witness in witnesses))
    title = alignment.name or " / ".join(names)
    date = next((h["date"]["text"] for w in witnesses if (h := w.transcription.header)["date"]), None)
    description = next((w.transcription.header["description"] for w in witnesses if w.transcription.header["description"]), None)
    metadata = {
        "gregoryaland": _first(witnesses, "GA"),
        "vl": _first(witnesses, "VL"),
        "trismegistos": _first(witnesses, "TM"),
        "date": date,
        "description": description,
    }
    metadata = {key: value for key, value in metadata.items() if value}
    return AlignedPair(
        id=alignment.id,
        alignment=alignment,
        title=title,
        siglum=metadata.get("gregoryaland") or title,
        metadata=metadata,
        lang_a=lang_a,
        lang_b=lang_b,
        verses=verses,
        problems=problems,
    )


def load_project(config: Config) -> Project:
    errors: list[str] = []
    witnesses = {manuscript.id: load_witness(manuscript, errors) for manuscript in config.manuscripts}
    pairs = []
    for alignment in config.alignments:
        witness_a, witness_b = (witnesses[ms] for ms in alignment.manuscripts)
        if witness_a and witness_b:
            pair = load_pair(alignment, witness_a, witness_b, errors)
            if pair:
                pairs.append(pair)
    if errors:
        raise CorpusError(errors)
    return Project(config=config, witnesses=witnesses, pairs=pairs)
