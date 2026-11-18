"""
Datasets: a bilingual manuscript parsed with MCParser and aligned with MCAligner.

Each dataset is a folder under ``datasets/`` with a ``dataset.yaml`` manifest that
points at the files those tools wrote. See ``datasets/README.md`` for the format.
"""
from __future__ import annotations

import re
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .alignment import Link, read_alignment
from .bible import read_verse_ref
from .conllu import Sentence, read_conllu
from .transcription import Transcription, VerseNotes, read_transcription

MANIFEST_NAME = "dataset.yaml"
DATASETS_DIR = Path("datasets")
ARABIC_RE = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿ]")
HEBREW_SYRIAC_RE = re.compile(r"[֐-׿܀-ݏ]")


class DatasetError(Exception):
    pass


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(text).strip().lower()).strip("-")
    return slug or "x"


def resolve_verse(sentence: Sentence) -> tuple[str, str] | None:
    """ Returns ``(verse_id, label)`` such as ``("B06K01V07", "Romans 1:7")`` if the sentence names a verse. """
    for candidate in sentence.ref_candidates():
        try:
            verse_id, label = read_verse_ref(candidate.replace("_", " "))
        except Exception:
            continue
        if not verse_id.startswith("B-"):
            return verse_id, label or candidate
    return None


@dataclass
class Language:
    id: str
    label: str
    conllu: Path
    rtl: bool
    sentences: dict[str, Sentence]
    transcriptions: list[Transcription] = field(default_factory=list)

    def verse_notes(self, verse_id: str) -> list[dict]:
        """ What the transcriptions record for this verse: folios, corrections, lacunae... (one dict per file that has it). """
        found = []
        for transcription in self.transcriptions:
            notes = transcription.verses.get(verse_id)
            if notes is not None:
                found.append(notes.to_dict())
        return found


@dataclass
class Verse:
    id: str  # used in URLs
    label: str  # shown to readers
    sent_id: str
    a: Sentence
    b: Sentence
    links: list[Link]


@dataclass
class Dataset:
    id: str
    path: Path
    title: str
    siglum: str
    metadata: dict
    lang_a: Language
    lang_b: Language
    verses: list[Verse]
    alignment_path: Path | None
    problems: list[str] = field(default_factory=list)

    @property
    def category(self) -> str:
        return f"{self.lang_a.label}-{self.lang_b.label}"

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


def _require(mapping: dict, key: str, where: str):
    if key not in mapping or mapping[key] in (None, ""):
        raise DatasetError(f"{where}: missing required field '{key}'")
    return mapping[key]


def _resolve_path(base: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else base / path


def _detect_rtl(sentences: dict[str, Sentence]) -> bool:
    sample = " ".join(sentence.text for sentence in list(sentences.values())[:20])
    return bool(ARABIC_RE.search(sample) or HEBREW_SYRIAC_RE.search(sample))


def _load_language(config: dict, base: Path, where: str) -> Language:
    language_id = slugify(_require(config, "id", where))
    conllu_path = _resolve_path(base, _require(config, "conllu", where))
    if not conllu_path.exists():
        raise DatasetError(f"{where}: CoNLL-U file not found: {conllu_path}")

    sentences: dict[str, Sentence] = {}
    for sentence in read_conllu(conllu_path):
        if sentence.sent_id in sentences:
            raise DatasetError(f"{conllu_path}: duplicate sent_id {sentence.sent_id!r}")
        sentences[sentence.sent_id] = sentence

    transcriptions = []
    transcription_config = config.get("transcription") or []
    if not isinstance(transcription_config, list):
        transcription_config = [transcription_config]
    for value in transcription_config:
        # Either a path, or {path: ..., renumber_restarts: [John.6]} for files whose verse numbers restart mid-chapter.
        options = value if isinstance(value, dict) else {"path": value}
        tei_path = _resolve_path(base, _require(options, "path", f"{where}: transcription"))
        if not tei_path.exists():
            raise DatasetError(f"{where}: transcription file not found: {tei_path}")
        try:
            transcription = read_transcription(tei_path, options.get("renumber_restarts"))
        except Exception as err:
            raise DatasetError(f"{where}: could not read transcription {tei_path}: {err}") from err
        # Key the verse notes by the site's verse ids (B04K01V25) so they line up whatever the sent_id style.
        transcription.verses = _key_by_verse_id(transcription.verses)
        transcriptions.append(transcription)

    rtl = config.get("rtl")
    return Language(
        id=language_id,
        label=str(config.get("label") or config["id"]).strip(),
        conllu=conllu_path,
        rtl=_detect_rtl(sentences) if rtl is None else bool(rtl),
        sentences=sentences,
        transcriptions=transcriptions,
    )


def _key_by_verse_id(verses: dict[str, VerseNotes]) -> dict[str, VerseNotes]:
    keyed = {}
    for ref, notes in verses.items():
        try:
            verse_id, _ = read_verse_ref(ref.replace("_", " "))
        except Exception:
            verse_id = None
        keyed[verse_id if verse_id and not verse_id.startswith("B-") else ref] = notes
    return keyed


def load_dataset(manifest_path: Path | str) -> Dataset:
    manifest_path = Path(manifest_path)
    if manifest_path.is_dir():
        manifest_path = manifest_path / MANIFEST_NAME
    base = manifest_path.parent
    where = str(manifest_path)

    config = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    if not isinstance(config, dict):
        raise DatasetError(f"{where}: expected a YAML mapping")

    dataset_id = slugify(config.get("id") or base.name)
    title = str(_require(config, "title", where))

    languages = config.get("languages")
    if not isinstance(languages, list) or len(languages) != 2:
        raise DatasetError(f"{where}: 'languages' must list exactly two languages")
    lang_a = _load_language(languages[0], base, f"{where}: languages[0]")
    lang_b = _load_language(languages[1], base, f"{where}: languages[1]")
    if lang_a.id == lang_b.id:
        raise DatasetError(f"{where}: the two languages need different ids")

    problems: list[str] = []

    # Alignment (optional: without it the verses are shown unaligned)
    alignment: dict[str, list[Link]] = {}
    alignment_path = None
    swap = False
    alignment_config = config.get("alignment")
    if isinstance(alignment_config, str):
        alignment_config = {"path": alignment_config}
    if alignment_config:
        alignment_path = _resolve_path(base, _require(alignment_config, "path", f"{where}: alignment"))
        if not alignment_path.exists():
            raise DatasetError(f"{where}: alignment file not found: {alignment_path}")
        alignment = read_alignment(alignment_path)

        source = slugify(alignment_config.get("source") or lang_a.id)
        target = slugify(alignment_config.get("target") or (lang_b.id if source == lang_a.id else lang_a.id))
        if {source, target} != {lang_a.id, lang_b.id}:
            raise DatasetError(
                f"{where}: alignment source/target ({source}, {target}) must be the language ids "
                f"({lang_a.id}, {lang_b.id})"
            )
        swap = source != lang_a.id

        min_confidence = alignment_config.get("min_confidence")
        include_probable = alignment_config.get("include_probable", True)
        for sent_id, links in alignment.items():
            kept = []
            for link in links:
                if swap:
                    link = Link(link.target, link.source, link.sure, link.confidence, link.agent)
                if not include_probable and not link.sure:
                    continue
                if min_confidence is not None and link.confidence is not None and link.confidence < min_confidence:
                    continue
                kept.append(link)
            alignment[sent_id] = kept

    # Pair sentences by sent_id, in the order of side A's file.
    verses: list[Verse] = []
    used_ids: set[str] = set()
    only_a = [sent_id for sent_id in lang_a.sentences if sent_id not in lang_b.sentences]
    only_b = [sent_id for sent_id in lang_b.sentences if sent_id not in lang_a.sentences]
    if only_a:
        problems.append(f"{len(only_a)} sentence(s) only in {lang_a.label}: {', '.join(only_a[:5])}")
    if only_b:
        problems.append(f"{len(only_b)} sentence(s) only in {lang_b.label}: {', '.join(only_b[:5])}")

    for sent_id, sentence_a in lang_a.sentences.items():
        sentence_b = lang_b.sentences.get(sent_id)
        if sentence_b is None:
            continue

        resolved = resolve_verse(sentence_a) or resolve_verse(sentence_b)
        verse_id, label = resolved if resolved else (slugify(sent_id), sent_id)
        if verse_id in used_ids:
            verse_id = slugify(sent_id)
            n = 2
            while verse_id in used_ids:
                verse_id = f"{slugify(sent_id)}-{n}"
                n += 1
        used_ids.add(verse_id)

        links = alignment.get(sent_id, [])
        ids_a, ids_b = sentence_a.word_ids, sentence_b.word_ids
        bad = [link for link in links if link.source not in ids_a or link.target not in ids_b]
        if bad:
            problems.append(
                f"{sent_id}: {len(bad)} link(s) to words that do not exist, ignored: "
                + " ".join(f"{link.source}-{link.target}" for link in bad[:5])
            )
            links = [link for link in links if link not in bad]

        verses.append(Verse(id=verse_id, label=label, sent_id=sent_id, a=sentence_a, b=sentence_b, links=links))

    if alignment:
        orphan = [sent_id for sent_id in alignment if sent_id not in lang_a.sentences or sent_id not in lang_b.sentences]
        if orphan:
            problems.append(f"{len(orphan)} aligned sent_id(s) not in both CoNLL-U files: {', '.join(orphan[:5])}")

    if not verses:
        raise DatasetError(f"{where}: no sent_id is shared by the two CoNLL-U files")

    for language in (lang_a, lang_b):
        for transcription in language.transcriptions:
            problems.extend(f"{language.label} transcription {transcription.path.name}: {problem}" for problem in transcription.problems)

    metadata = {
        key: value for key, value in config.items() if key not in {"id", "languages", "alignment"}
    }
    siglum = str(config.get("siglum") or config.get("gregoryaland") or title)

    return Dataset(
        id=dataset_id,
        path=manifest_path,
        title=title,
        siglum=siglum,
        metadata=metadata,
        lang_a=lang_a,
        lang_b=lang_b,
        verses=verses,
        alignment_path=alignment_path,
        problems=problems,
    )


def find_manifests(datasets_dir: Path | str = DATASETS_DIR) -> list[Path]:
    datasets_dir = Path(datasets_dir)
    if not datasets_dir.exists():
        return []
    return sorted(datasets_dir.glob(f"*/{MANIFEST_NAME}"))


def load_datasets(datasets_dir: Path | str = DATASETS_DIR, only: list[str] | None = None) -> list[Dataset]:
    """ Loads every dataset; one that cannot be loaded is skipped with a warning so the rest still build. """
    datasets = []
    for manifest in find_manifests(datasets_dir):
        if only and manifest.parent.name not in only:
            continue
        try:
            datasets.append(load_dataset(manifest))
        except (DatasetError, ValueError, OSError) as err:
            warnings.warn(f"Skipping {manifest.parent.name}: {err}", stacklevel=2)
    return datasets
