"""
Builds the static website for a project (see ``config.py`` and ``corpus.py``).

site/
  index.html                                       home page
  about/index.html                                 the theme's about page (Markdown), if any
  css/hexapla.css                                  Bootstrap and Hexapla's styles, with the theme's variables
  js/, img/                                        scripts, the logo and the favicon
  assets/                                          the theme's assets folder (images and files for the about page)
  manuscripts/<ms>/index.html                      a manuscript: its TEI header and transcription summary
  manuscripts/<ms>/<file>.xml                      the TEI transcription, for download
  alignments/<id>/index.html                       overview: statistics, verse table
  alignments/<id>/corpus.js                        verse texts for the pages that show examples
  alignments/<id>/verses.js                        verse ids and labels for the verse selector
  alignments/<id>/lexicon/index.html               searchable bilingual lexicon
  alignments/<id>/insights/index.html              grammatical correspondences, untranslated words
  alignments/<id>/review/index.html                least confident links and parses
  alignments/<id>/<verse>/index.html               verse page (trees, interlinear, alignment matrix)
  alignments/<id>/<verse>/<id>-<verse>.js          data for the verse page
  alignments/<id>/<lang>/lemmas.js                 lemma list for the lemma selector
  alignments/<id>/<lang>/<lemma>/index.html        lemma page (translation equivalents)
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
from .about import render_about
from .bible import read_verse_ref
from .config import FAVICON_TYPES
from .conllu import Sentence
from .corpus import AlignedPair, Language, Project, Verse, Witness
from .theme import compile_css

PACKAGE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = PACKAGE_DIR / "templates"
STATIC_DIR = PACKAGE_DIR / "static"
DEFAULT_LOGO = STATIC_DIR / "img" / "hexapla-logo.svg"
SMALL_LOGO = STATIC_DIR / "img" / "hexapla-small.svg"  # "Built with Hexapla" in every page's footer
HEXAPLA_URL = "https://github.com/rbturnbull/hexapla"
MARKER = ".hexapla"
RESERVED_NAMES = {"lexicon", "insights", "review", "corpus.js", "verses.js"}

env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(),
)


class OutputDirError(Exception):
    pass


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


def build_sidebar_sections(datasets: list[AlignedPair], summaries: dict[str, dict] | None = None) -> list[dict]:
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


def langs_context(dataset: AlignedPair) -> dict:
    return {
        side: {"id": lang.id, "label": lang.label, "rtl": lang.rtl}
        for side, lang in (("a", dataset.lang_a), ("b", dataset.lang_b))
    }


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


def build_lemma_index(dataset: AlignedPair) -> dict[str, dict[str, dict]]:
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


def transcription_context(witness: Witness, site_licence: dict | None) -> dict:
    """ What the pages show about a witness's TEI file: its header and body summary, and the licences that apply. """
    transcription = witness.transcription
    header = transcription.header
    named = header["licence_name"] or header["licence_url"]
    tei_licence = {"name": header["licence_name"] or "Licence", "url": header["licence_url"]} if named else None
    return {
        "id": witness.id,
        "name": witness.name,
        "language": witness.label,
        "language_code": witness.language,
        "file": transcription.path.name,
        "source": transcription.path,
        "header": header,
        "summary": transcription.summary,
        "range": _ref_range(transcription.summary["first"], transcription.summary["last"]),
        # The TEI's own licence overrides the site's; its text is shown when it could not be named.
        "licence": tei_licence or site_licence,
        "licence_text": header["licence"] if not tei_licence and header["licence"] else "",
        "parsing_licence": witness.licence or site_licence,
    }


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


def attribution(transcriptions: list[dict]) -> list[dict]:
    """ Short credit lines for the footer, which CC BY asks for: who made each transcription, and its licence. """
    lines = []
    for item in transcriptions:
        header = item["header"]
        # Skip machine credits such as the NTVMR's "edition metadata assembled by VMRCRE".
        names = list(dict.fromkeys(name for resp in header.get("responsibility", []) for name in resp["names"]
                                   if "metadata" not in resp["resp"].lower()))
        credit = ", ".join(names) or ", ".join(header.get("publishers", []))
        if header.get("authority"):  # e.g. Project Wulfila, whose licence asks for the project to be named
            credit = f"{credit}, {header['authority']}" if credit else header["authority"]
        licence = item["licence"] or {}
        lines.append({"language": item["language"], "credit": credit or "transcriber not named in the file",
                      "licence": licence.get("name") or "no licence stated", "licence_url": licence.get("url")})
    return lines


def json_compact(data) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def licence_lines(dataset: AlignedPair, transcriptions: list[dict], site_licence: dict | None) -> list[dict]:
    """ The licences of the parses and the links (the site's, unless the config overrides them). """
    lines = [{"label": f"{item['language']} parsing", **item["parsing_licence"]}
             for item in transcriptions if item["parsing_licence"]]
    alignment_licence = dataset.licence or site_licence
    if alignment_licence:
        lines.append({"label": "Alignment", **alignment_licence})
    return lines


def build_pair(dataset: AlignedPair, site: dict, sidebar_sections: list[dict], website_dir: Path,
               verses: list[dict], summary: dict):
    lang_a, lang_b = dataset.lang_a, dataset.lang_b
    clashes = RESERVED_NAMES & ({lang_a.id, lang_b.id} | {verse.id for verse in dataset.verses})
    if clashes:
        raise ValueError(f"{dataset.id}: language or verse ids clash with page names: {', '.join(sorted(clashes))}")

    ms_dir = website_dir / "alignments" / dataset.id
    verse_list = [verse.id for verse in dataset.verses]
    has_confidence = summary["parse_confidence"] is not None
    transcriptions = [transcription_context(witness, site["licence"]) for witness in dataset.witnesses]

    common = dict(
        site=site,
        transcriptions=transcriptions,
        attribution=attribution(transcriptions),
        licences=licence_lines(dataset, transcriptions, site["licence"]),
        siglum=dataset.id,
        title=dataset.title,
        display_siglum=dataset.siglum,
        metadata=dataset.metadata,
        langs=langs_context(dataset),
        first_verse=verse_list[0],
        sidebar_sections=sidebar_sections,
    )

    # Overview, lexicon, insights, review
    write(ms_dir / "index.html", env.get_template("alignment.html").render(
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
                {"language": language.label, "manuscript": language.witness.id, "notes": language.verse_notes(verse.id)}
                for language in (lang_a, lang_b)
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


def prepare_output(output: Path):
    """ Empties the output folder, but only one Hexapla built (it holds a marker file) or an empty one. """
    if output.exists():
        if not output.is_dir():
            raise OutputDirError(f"{output} is a file, not a folder")
        if any(output.iterdir()) and not (output / MARKER).exists():
            raise OutputDirError(f"{output} is not empty and was not built by Hexapla: choose another folder or empty it")
        shutil.rmtree(output)
    output.mkdir(parents=True)
    (output / MARKER).write_text("Built by Hexapla. This folder is replaced on every build.\n", encoding="utf-8")


def build_manuscript(witness: Witness, pairs: list[AlignedPair], site: dict, sidebar_sections: list[dict],
                     website_dir: Path):
    item = transcription_context(witness, site["licence"])
    ms_dir = website_dir / "manuscripts" / witness.id
    ms_dir.mkdir(parents=True)
    shutil.copyfile(item["source"], ms_dir / item["file"])
    write(ms_dir / "index.html", env.get_template("manuscript.html").render(
        root="../../", page="manuscript", site=site, sidebar_sections=sidebar_sections, title=witness.name,
        siglum=None, t=item,
        alignments=[{"id": pair.id, "title": pair.title, "category": pair.category}
                    for pair in pairs if witness in pair.witnesses],
    ))


def build_site(project: Project, output: Path | str):
    """ Writes the whole site to ``output``, replacing what an earlier build left there. """
    output = Path(output)
    theme = project.config.theme
    css = compile_css(theme.variables)  # before emptying the output, so a broken theme keeps the last build
    pairs = project.pairs
    stats = {pair.id: analysis.verse_stats(pair) for pair in pairs}
    summaries = {pair.id: analysis.summary(pair, stats[pair.id]) for pair in pairs}

    prepare_output(output)
    write(output / "css" / "hexapla.css", css)
    shutil.copytree(STATIC_DIR / "js", output / "js")
    logo = theme.logo or DEFAULT_LOGO
    logo_name = f"logo{logo.suffix}" if theme.logo else DEFAULT_LOGO.name
    (output / "img").mkdir()
    shutil.copyfile(logo, output / "img" / logo_name)
    shutil.copyfile(SMALL_LOGO, output / "img" / SMALL_LOGO.name)
    favicon = None
    if theme.favicon:
        suffix = theme.favicon.suffix.lower()
        favicon = {"name": f"favicon{suffix}", "type": FAVICON_TYPES[suffix]}
        shutil.copyfile(theme.favicon, output / "img" / favicon["name"])
    if theme.assets:
        shutil.copytree(theme.assets, output / "assets")

    site = {"name": theme.name, "logo": logo_name, "favicon": favicon, "about": theme.about is not None, "licence": project.site_licence,
            "hexapla_url": HEXAPLA_URL, "hexapla_logo": SMALL_LOGO.name}
    sidebar_sections = build_sidebar_sections(pairs)
    sections = build_sidebar_sections(pairs, summaries)
    write(output / "index.html", env.get_template("home.html").render(
        root="./", page="home", title="Home", site=site, siglum=None, sidebar_sections=sidebar_sections, cards=sections,
    ))
    if theme.about:
        about = render_about(theme.about, theme.assets, root="../")
        write(output / "about" / "index.html", env.get_template("about.html").render(
            root="../", page="about", title="About", site=site, siglum=None, sidebar_sections=sidebar_sections,
            about_html=about,
        ))
    for witness in project.witnesses.values():
        build_manuscript(witness, pairs, site, sidebar_sections, output)
    for pair in pairs:
        build_pair(pair, site, sidebar_sections, output, stats[pair.id], summaries[pair.id])
