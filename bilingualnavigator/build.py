"""
Builds the static website from the datasets in ``datasets/`` (see ``dataset.py``).

website/
  index.html                                   home page
  mss/<dataset>/index.html                     overview: statistics, verse table
  mss/<dataset>/corpus.js                      verse texts for the pages that show examples
  mss/<dataset>/verses.js                      verse ids and labels for the verse selector
  mss/<dataset>/tei/<file>.xml                 the TEI transcriptions, for download
  mss/<dataset>/<lang>/lemmas.js               lemma list for the lemma selector
  mss/<dataset>/lexicon/index.html             searchable bilingual lexicon
  mss/<dataset>/insights/index.html            grammatical correspondences, untranslated words
  mss/<dataset>/review/index.html              least confident links and parses
  mss/<dataset>/<verse>/index.html             verse page (trees, interlinear, alignment matrix)
  mss/<dataset>/<verse>/<dataset>-<verse>.js   data for the verse page
  mss/<dataset>/<language>/<lemma>/index.html  lemma page (translation equivalents)
"""
from __future__ import annotations

import html
import json
import re
import shutil
from collections import Counter
from pathlib import Path
from urllib.parse import quote

from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import analysis
from .conllu import Sentence
from .bible import read_verse_ref
from .dataset import Dataset, Language, Verse

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = PACKAGE_ROOT / "templates"
WEBSITE_DIR = Path("website")
RESERVED_NAMES = {"lexicon", "insights", "review", "tei", "corpus.js", "verses.js"}

env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(),
)


def gregory_aland_to_intf_id(gregory_aland):
    gregory_aland = str(gregory_aland or "")
    m = re.match(r"GA(0?\d+)", gregory_aland)
    if m:
        gregory_aland = m.group(1)

    if len(gregory_aland) == 0:
        return None

    m = re.match(r"P(\d+)", gregory_aland)
    if m:
        return 10000 + int(m.group(1))
    m = re.match(r"0(\d+)", gregory_aland)
    if m:
        return 20000 + int(m.group(1))
    if gregory_aland.isdigit():
        return 30000 + int(gregory_aland)
    m = re.match(r"L(\d+)", gregory_aland)
    if m:
        return 40000 + int(m.group(1))
    return None


def sidebar_sort_key(item):
    intf_id = gregory_aland_to_intf_id(item.get("gregoryaland"))
    if intf_id is not None:
        return (0, intf_id, item["siglum"])
    return (1, 0, item["siglum"])


def build_sidebar_sections(datasets: list[Dataset], summaries: dict[str, dict] | None = None) -> list[dict]:
    sections: dict[str, list[dict]] = {}
    for dataset in datasets:
        item = {
            "id": dataset.id,
            "siglum": dataset.siglum,
            "title": dataset.title,
            "gregoryaland": dataset.metadata.get("gregoryaland"),
            "vl": dataset.metadata.get("vl"),
            "date": dataset.metadata.get("date"),
            "description": dataset.metadata.get("description"),
        }
        if summaries and dataset.id in summaries:
            s = summaries[dataset.id]
            words = s["words_a"] + s["words_b"]
            item.update(verses=s["verses"], links=s["links"],
                        coverage=(s["aligned_a"] + s["aligned_b"]) / words if words else 0)
        sections.setdefault(dataset.category, []).append(item)
    return [
        {"title": title, "manuscripts": sorted(items, key=sidebar_sort_key)}
        for title, items in sorted(sections.items())
    ]


def langs_context(dataset: Dataset) -> dict:
    return {
        side: {"id": lang.id, "label": lang.label, "rtl": lang.rtl}
        for side, lang in (("a", dataset.lang_a), ("b", dataset.lang_b))
    }


def build_home_page(datasets: list[Dataset], website_dir: Path = WEBSITE_DIR, summaries: dict | None = None):
    website_dir.mkdir(parents=True, exist_ok=True)
    sections = build_sidebar_sections(datasets, summaries)
    home_html = env.get_template("home.html").render(
        root="./", page="home", title="Bilingual Navigator", siglum=None,
        sidebar_sections=sections, cards=sections if summaries else [],
    )
    (website_dir / "index.html").write_text(home_html, encoding="utf-8")


def linkable_lemma(word) -> bool:
    """ Whether a word gets a lemma page (its lemma is used as a directory name). """
    lemma = word.lemma
    if not lemma or lemma in {"_", ".", ".."} or "/" in lemma or "\\" in lemma:
        return False
    return word.upos != "PUNCT"


def linkable_lemma_name(lemma: str) -> bool:
    return bool(lemma) and lemma not in {"_", ".", ".."} and "/" not in lemma and "\\" not in lemma


def render_highlighted_tokens(sentence: Sentence, highlight_ids, highlight_class: str) -> str:
    highlight_set = set(highlight_ids or [])
    no_space_after = set(sentence.no_space_after)
    parts = []
    for index, word in enumerate(sentence.words):
        form = html.escape(word.form)
        if word.id in highlight_set:
            form = f'<span class="{highlight_class}">{form}</span>'
        parts.append(form)
        if index < len(sentence.words) - 1 and word.id not in no_space_after:
            parts.append(" ")
    return "".join(parts)


def word_map(verse: Verse, lang_a: Language, lang_b: Language) -> dict[str, list[dict]]:
    """
    Maps each aligned word to its partners for the verse page, e.g.
    ``{"greek-3": [{"svgId": "latin", "id": 8, "sure": true, "confidence": 0.95}]}``.
    """
    mapping: dict[str, list[dict]] = {}
    for link in verse.links:
        mapping.setdefault(f"{lang_a.id}-{link.source}", []).append(
            {"svgId": lang_b.id, "id": link.target, "sure": link.sure, "confidence": link.confidence}
        )
        mapping.setdefault(f"{lang_b.id}-{link.target}", []).append(
            {"svgId": lang_a.id, "id": link.source, "sure": link.sure, "confidence": link.confidence}
        )
    return mapping


def sentence_js_data(sentence: Sentence, language: Language) -> dict:
    low_conf = []
    for word in sentence.words:
        confidence = analysis.word_confidence(word)
        if confidence is not None and confidence < analysis.LOW_CONFIDENCE:
            low_conf.append(word.id)
    return {
        "svgId": language.id,
        "data": sentence.to_conllu(),
        "rtl": language.rtl,
        "noSpaceAfter": sentence.no_space_after,
        "languageSlug": language.id,
        "lemmaMap": {word.id: word.lemma for word in sentence.words if linkable_lemma(word)},
        "lowConf": low_conf,
    }


def build_lemma_index(dataset: Dataset) -> dict[str, dict[str, dict]]:
    """ For each language and lemma: occurrences, aligned lemmas in the other language (with examples) and unaligned verses. """
    index: dict[str, dict[str, dict]] = {dataset.lang_a.id: {}, dataset.lang_b.id: {}}

    def add_side(verse: Verse, this: Language, other: Language, this_sentence: Sentence,
                 other_sentence: Sentence, partners: dict[int, list[int]]):
        other_words = {word.id: word for word in other_sentence.words}
        for word in this_sentence.words:
            if not linkable_lemma(word):
                continue
            entry = index[this.id].setdefault(word.lemma, {"count": 0, "parallel": 0, "aligned": {}, "unaligned": {},
                                                           "forms": Counter(), "verses": set()})
            entry["count"] += 1
            entry["forms"][word.form] += 1
            entry["verses"].add(verse.id)
            partner_ids = partners.get(word.id, [])
            if not partner_ids:
                entry["unaligned"].setdefault(verse.id, {"verse": verse, "highlight_ids_this": []})[
                    "highlight_ids_this"
                ].append(word.id)
                continue
            entry["parallel"] += 1
            lemmas = analysis.equivalent(partner_ids, other_words)
            if not lemmas:
                continue
            aligned = entry["aligned"].setdefault(lemmas, {"count": 0, "examples": {}})
            aligned["count"] += 1
            example = aligned["examples"].setdefault(
                verse.id,
                {"verse": verse, "other": other, "other_sentence": other_sentence,
                 "this_sentence": this_sentence, "highlight_ids_this": [], "highlight_ids_other": []},
            )
            example["highlight_ids_this"].append(word.id)
            example["highlight_ids_other"].extend(partner_ids)

    for verse in dataset.verses:
        a_to_b: dict[int, list[int]] = {}
        b_to_a: dict[int, list[int]] = {}
        for link in verse.links:
            a_to_b.setdefault(link.source, []).append(link.target)
            b_to_a.setdefault(link.target, []).append(link.source)
        add_side(verse, dataset.lang_a, dataset.lang_b, verse.a, verse.b, a_to_b)
        add_side(verse, dataset.lang_b, dataset.lang_a, verse.b, verse.a, b_to_a)
    return index


def transcriptions_context(dataset: Dataset) -> list[dict]:
    """ One entry per TEI file: the language, its header and body summary, and where it is published. """
    items = []
    for language in (dataset.lang_a, dataset.lang_b):
        for transcription in language.transcriptions:
            items.append({
                "language": language.label,
                "language_id": language.id,
                "file": transcription.path.name,
                "source": transcription.path,
                "header": transcription.header,
                "summary": transcription.summary,
                "range": _ref_range(transcription.summary.get("first"), transcription.summary.get("last")),
                "problems": transcription.problems,
            })
    return items


def _ref_label(ref: str | None) -> str:
    if not ref:
        return ""
    try:
        verse_id, label = read_verse_ref(ref.replace("_", " "))
        return label if label and not verse_id.startswith("B-") else ref
    except Exception:
        return ref


def _ref_range(first: str | None, last: str | None) -> str:
    """ "John 1:24 – 8:31" (the book is not repeated). """
    start, end = _ref_label(first), _ref_label(last)
    if not start or start == end:
        return start
    book = start.rsplit(" ", 1)[0]
    if end.startswith(book + " "):
        end = end[len(book) + 1:]
    return f"{start} – {end}"


def attribution(transcriptions: list[dict]) -> list[str]:
    """ Short credit lines for the footer, which CC BY asks for: who made each transcription, and its licence. """
    lines = []
    for item in transcriptions:
        header = item["header"]
        names = list(dict.fromkeys(name for resp in header.get("responsibility", []) for name in resp["names"]))
        credit = ", ".join(names) or ", ".join(header.get("publishers", []))
        if header.get("authority"):  # e.g. Project Wulfila, whose licence asks for the project to be named
            credit = f"{credit}, {header['authority']}" if credit else header["authority"]
        lines.append({"language": item["language"], "credit": credit, "licence": header.get("licence_name"),
                      "licence_url": header.get("licence_url")})
    return lines


def json_compact(data) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_dataset(dataset: Dataset, sidebar_sections: list[dict], website_dir: Path = WEBSITE_DIR,
                  verses: list[dict] | None = None, summary: dict | None = None):
    lang_a, lang_b = dataset.lang_a, dataset.lang_b
    clashes = RESERVED_NAMES & ({lang_a.id, lang_b.id} | {verse.id for verse in dataset.verses})
    if clashes:
        raise ValueError(f"{dataset.id}: language or verse ids clash with page names: {', '.join(sorted(clashes))}")

    ms_dir = website_dir / "mss" / dataset.id
    if ms_dir.exists():
        shutil.rmtree(ms_dir)
    ms_dir.mkdir(parents=True)

    verses = verses if verses is not None else analysis.verse_stats(dataset)
    summary = summary if summary is not None else analysis.summary(dataset, verses)
    verse_list = [verse.id for verse in dataset.verses]
    has_confidence = summary["parse_confidence"] is not None

    transcriptions = transcriptions_context(dataset)
    for item in transcriptions:
        target = ms_dir / "tei" / item["file"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(item["source"], target)

    common = dict(
        transcriptions=transcriptions,
        attribution=attribution(transcriptions),
        siglum=dataset.id,
        title=dataset.title,
        display_siglum=dataset.siglum,
        metadata=dataset.metadata,
        langs=langs_context(dataset),
        first_verse=verse_list[0],
        sidebar_sections=sidebar_sections,
    )

    # Overview, lexicon, insights, review
    write(ms_dir / "index.html", env.get_template("ms.html").render(
        **common, root="../../", page="overview", summary=summary,
        overview={"summary": summary, "verses": verses},
    ))
    corpus = json.dumps(analysis.corpus(dataset), ensure_ascii=False, separators=(",", ":"))
    write(ms_dir / "corpus.js", f"window.CORPUS = {corpus};\n")
    # Selector options live in shared files: embedding them in every page grows the site quadratically.
    write(ms_dir / "verses.js", f"window.SELECT_ITEMS = {json_compact([[verse.id, verse.label] for verse in dataset.verses])};\n")
    write(ms_dir / "lexicon" / "index.html", env.get_template("lexicon.html").render(
        **common, root="../../../", page="lexicon",
        lexicon={"a": analysis.lexicon(dataset, "a"), "b": analysis.lexicon(dataset, "b")},
    ))
    write(ms_dir / "insights" / "index.html", env.get_template("insights.html").render(
        **common, root="../../../", page="insights",
        insights={"matrices": analysis.correspondences(dataset), "unaligned": analysis.unaligned_by_upos(dataset)},
    ))
    write(ms_dir / "review" / "index.html", env.get_template("review.html").render(
        **common, root="../../../", page="review", review=analysis.review(dataset),
    ))

    # Verses
    verse_template = env.get_template("verse.html")
    verse_js_template = env.get_template("verse.js")
    for index, verse in enumerate(dataset.verses):
        verse_dir = ms_dir / verse.id
        write(verse_dir / "index.html", verse_template.render(
            **common,
            root="../../../",
            page="verse",
            verse=verse.id,
            verse_label=verse.label,
            verse_list=verse_list,
            prev_verse=verse_list[index - 1] if index > 0 else None,
            next_verse=verse_list[index + 1] if index + 1 < len(verse_list) else None,
            sent_id=verse.sent_id,
            stats=verses[index],
            verse_notes=[
                {"language": language.label, "notes": language.verse_notes(verse.id)}
                for language in (lang_a, lang_b) if language.transcriptions
            ],
            has_confidence=has_confidence,
            lang_a_label=lang_a.label,
            lang_b_label=lang_b.label,
            lang_a_id=lang_a.id,
            lang_b_id=lang_b.id,
            lang_a_text=verse.a.text,
            lang_b_text=verse.b.text,
            lang_a_rtl=lang_a.rtl,
            lang_b_rtl=lang_b.rtl,
        ))
        write(verse_dir / f"{dataset.id}-{verse.id}.js", verse_js_template.render(
            siglum=dataset.id,
            verse=verse.id,
            mapping=word_map(verse, lang_a, lang_b),
            sentences=[sentence_js_data(verse.a, lang_a), sentence_js_data(verse.b, lang_b)],
        ))

    # Lemmas
    lemma_template = env.get_template("lemma.html")
    languages = {lang_a.id: lang_a, lang_b.id: lang_b}
    for language_id, lemmas in build_lemma_index(dataset).items():
        language = languages[language_id]
        other = lang_b if language is lang_a else lang_a
        sentence_for = (lambda v: v.a) if language is lang_a else (lambda v: v.b)
        items = [[quote(lemma, safe=""), lemma] for lemma in sorted(lemmas)]
        write(ms_dir / language.id / "lemmas.js", f"window.SELECT_ITEMS = {json_compact(items)};\n")
        for lemma, counts in lemmas.items():
            aligned_items = []
            for other_lemma, aligned in sorted(counts["aligned"].items(), key=lambda item: (-item[1]["count"], item[0])):
                examples = [
                    {
                        "verse_id": ex["verse"].id,
                        "label": ex["verse"].label,
                        "text_this_html": render_highlighted_tokens(ex["this_sentence"], ex["highlight_ids_this"], "highlight-main"),
                        "text_other_html": render_highlighted_tokens(ex["other_sentence"], ex["highlight_ids_other"], "highlight-other"),
                        "rtl_this": language.rtl,
                        "rtl_other": ex["other"].rtl,
                        "other_language": ex["other"].label,
                    }
                    for ex in aligned["examples"].values()
                ]
                aligned_items.append({"lemma": " ".join(other_lemma), "count": aligned["count"], "examples": examples,
                                      "parts": [{"lemma": part, "linkable": linkable_lemma_name(part)} for part in other_lemma]})

            unaligned_examples = [
                {
                    "verse_id": ex["verse"].id,
                    "label": ex["verse"].label,
                    "text_this_html": render_highlighted_tokens(sentence_for(ex["verse"]), ex["highlight_ids_this"], "highlight-main"),
                    "rtl_this": language.rtl,
                }
                for ex in counts["unaligned"].values()
            ]

            write(ms_dir / language.id / lemma / "index.html", lemma_template.render(
                **common,
                root="../../../../",
                page="lemma",
                language=language.label,
                language_slug=language.id,
                other_language=other.label,
                other_slug=other.id,
                lemma=lemma,
                lemma_id=quote(lemma, safe=""),
                occurrences=counts["count"],
                parallels=counts["parallel"],
                verse_count=len(counts["verses"]),
                forms=counts["forms"].most_common(),
                aligned_items=aligned_items,
                unaligned_examples=unaligned_examples,
                rtl=language.rtl,
            ))


def build_website(datasets: list[Dataset], website_dir: Path = WEBSITE_DIR, build_ids: set[str] | None = None,
                  clean: bool = True):
    """
    Builds the home page and the datasets (only those in ``build_ids`` if given; the sidebar lists all of them).
    With ``clean``, removes the pages of datasets that no longer exist.
    """
    mss_dir = website_dir / "mss"
    if clean and mss_dir.exists():
        keep = {dataset.id for dataset in datasets}
        for child in mss_dir.iterdir():
            if child.is_dir() and child.name not in keep:
                shutil.rmtree(child)

    stats = {dataset.id: analysis.verse_stats(dataset) for dataset in datasets}
    summaries = {dataset.id: analysis.summary(dataset, stats[dataset.id]) for dataset in datasets}
    build_home_page(datasets, website_dir, summaries)
    sidebar_sections = build_sidebar_sections(datasets)
    for dataset in datasets:
        if build_ids is None or dataset.id in build_ids:
            build_dataset(dataset, sidebar_sections, website_dir, stats[dataset.id], summaries[dataset.id])
