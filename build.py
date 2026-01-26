#!/usr/bin/env python3

from pathlib import Path
from urllib.parse import quote
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
import re


DATA_DIR = Path("data")
WEBSITE_DIR = Path("website")
MSS_DIR = WEBSITE_DIR/"mss"

env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(),
)

ms_template = env.get_template("ms.html")
verse_template = env.get_template("verse.html")
verse_js_template = env.get_template("verse.js")

ARABIC_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]")


def contains_arabic(text):
    return bool(ARABIC_RE.search(text))


def parse_conllu(conllu):
    lines = []
    no_space_after = set()
    tokens = []
    for line in conllu.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        token_id = line.split("\t", 1)[0]
        if "-" in token_id:
            try:
                start, end = token_id.split("-", 1)
                start_id = int(start)
                end_id = int(end)
            except ValueError:
                continue
            for tok_id in range(start_id, end_id):
                no_space_after.add(tok_id)
            continue
        if "." in token_id:
            continue
        lines.append(line)
        parts = line.split("\t")
        if len(parts) > 2:
            try:
                tok_id = int(parts[0])
            except ValueError:
                continue
            tokens.append({"id": tok_id, "lemma": parts[2]})
    normalized = "\n".join(lines)
    rtl = contains_arabic(normalized)
    return normalized, sorted(no_space_after), rtl, tokens


def build_alignment_mapping(alignment, first_svg_id, second_svg_id):
    mapping = {}
    for link in alignment.split():
        match = re.match(r"(\d+)-(\d+)", link)
        if not match:
            continue
        first_id, second_id = match.groups()
        mapping[f"{first_svg_id}-{first_id}"] = f"{second_svg_id}-{second_id}"
        mapping[f"{second_svg_id}-{second_id}"] = f"{first_svg_id}-{first_id}"
    return mapping


def svg_id_for(language):
    svg_id = re.sub(r"[^a-z0-9]+", "-", language.strip().lower()).strip("-")
    return svg_id or "lang"


for path in DATA_DIR.glob("*.yaml"):
    my_data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    siglum = path.with_suffix("").name

    ms_dir = MSS_DIR / siglum
    ms_dir.mkdir(parents=True, exist_ok=True)

    verse_list = list(my_data.keys())
    verse_items = []
    lemma_index = {}
    language_slugs = {}
    language_rtl = {}
    verse_items = []
    for verse in verse_list:
        verse_data = my_data.get(verse) or {}
        language_keys = [key for key in verse_data.keys() if key != "alignment"]
        verbose = None
        for language in language_keys:
            verbose = verse_data.get(language, {}).get("verse")
            if verbose:
                break
        verse_items.append({"id": verse, "label": verbose or verse})

        if len(language_keys) >= 2:
            first_language = language_keys[0]
            second_language = language_keys[1]
            first_svg_id = svg_id_for(first_language)
            second_svg_id = svg_id_for(second_language)
            language_slugs[first_language] = first_svg_id
            language_slugs[second_language] = second_svg_id

            lang_a_norm, _, lang_a_rtl, lang_a_tokens = parse_conllu(
                verse_data.get(first_language, {}).get("conllu", "").strip()
            )
            lang_b_norm, _, lang_b_rtl, lang_b_tokens = parse_conllu(
                verse_data.get(second_language, {}).get("conllu", "").strip()
            )
            language_rtl[first_language] = lang_a_rtl or language_rtl.get(first_language, False)
            language_rtl[second_language] = lang_b_rtl or language_rtl.get(second_language, False)

            mapping = build_alignment_mapping(verse_data.get("alignment", ""), first_svg_id, second_svg_id)

            for token in lang_a_tokens:
                lemma = token["lemma"]
                if not lemma or lemma == "_":
                    continue
                lemma_data = lemma_index.setdefault(first_language, {}).setdefault(
                    lemma, {"count": 0, "parallel": 0}
                )
                lemma_data["count"] += 1
                if mapping.get(f"{first_svg_id}-{token['id']}"):
                    lemma_data["parallel"] += 1

            for token in lang_b_tokens:
                lemma = token["lemma"]
                if not lemma or lemma == "_":
                    continue
                lemma_data = lemma_index.setdefault(second_language, {}).setdefault(
                    lemma, {"count": 0, "parallel": 0}
                )
                lemma_data["count"] += 1
                if mapping.get(f"{second_svg_id}-{token['id']}"):
                    lemma_data["parallel"] += 1

    ms_path = ms_dir / "index.html"
    ms_html = ms_template.render(
        siglum=siglum,
        verse_list=verse_list,
        verse_items=verse_items,
    )
    ms_path.write_text(ms_html, encoding="utf-8")

    for verse in verse_list:
        verse_data = my_data[verse] or {}
        verse_path = ms_dir / verse / f"index.html"
        verse_path.parent.mkdir(parents=True, exist_ok=True)

        language_keys = [key for key in verse_data.keys() if key != "alignment"]
        if len(language_keys) < 2:
            raise ValueError(f"{path}: verse {verse} must include at least two languages")
        first_language = language_keys[0]
        second_language = language_keys[1]
        first_svg_id = svg_id_for(first_language)
        second_svg_id = svg_id_for(second_language)

        greek, greek_no_space_after, greek_rtl, greek_tokens = parse_conllu(
            verse_data[first_language].get("conllu", "").strip()
        )
        latin, latin_no_space_after, latin_rtl, latin_tokens = parse_conllu(
            verse_data[second_language].get("conllu", "").strip()
        )
        alignment = verse_data.get("alignment", "")
        mapping = build_alignment_mapping(alignment, first_svg_id, second_svg_id)

        verse_html = verse_template.render(
            siglum=siglum,
            verse_list=verse_list,
            verse=verse,
            verse_items=verse_items,
            lang_a_label=first_language,
            lang_b_label=second_language,
            lang_a_id=first_svg_id,
            lang_b_id=second_svg_id,
            lang_a_rtl=greek_rtl,
            lang_b_rtl=latin_rtl,
        )
        verse_path.write_text(verse_html, encoding="utf-8")
        print(f"Generated {verse_path}")

        verse_js = ms_dir / verse / f"{siglum}-{verse}.js"

        verse_js_content = verse_js_template.render(
            siglum=siglum,
            verse=verse,
            mapping=mapping,
            greek=greek,
            latin=latin,
            lang_a_id=first_svg_id,
            lang_b_id=second_svg_id,
            lang_a_rtl=greek_rtl,
            lang_b_rtl=latin_rtl,
            lang_a_no_space_after=greek_no_space_after,
            lang_b_no_space_after=latin_no_space_after,
            lang_a_slug=first_svg_id,
            lang_b_slug=second_svg_id,
            lang_a_lemmas={t["id"]: t["lemma"] for t in greek_tokens},
            lang_b_lemmas={t["id"]: t["lemma"] for t in latin_tokens},
        )
        verse_js.write_text(verse_js_content, encoding="utf-8")

    lemma_template = env.get_template("lemma.html")
    for language, lemmas in lemma_index.items():
        language_slug = language_slugs.get(language, svg_id_for(language))
        lemma_items = [
            {"id": quote(lemma, safe=""), "label": lemma}
            for lemma in sorted(lemmas.keys())
        ]
        for lemma, counts in lemmas.items():
            lemma_dir = ms_dir / language_slug / lemma
            lemma_dir.mkdir(parents=True, exist_ok=True)
            lemma_html = lemma_template.render(
                siglum=siglum,
                language=language,
                language_slug=language_slug,
                lemma=lemma,
                lemma_items=lemma_items,
                occurrences=counts["count"],
                parallels=counts["parallel"],
                rtl=language_rtl.get(language, False),
            )
            (lemma_dir / "index.html").write_text(lemma_html, encoding="utf-8")
