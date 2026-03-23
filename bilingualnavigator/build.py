#!/usr/bin/env python3

from pathlib import Path
from urllib.parse import quote
import html
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
home_template = env.get_template("home.html")

ARABIC_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]")


def gregory_aland_to_intf_id(gregory_aland):
    m = re.match(r"GA(0?\d+)", gregory_aland)
    if m:
        gregory_aland = m.group(1)

    if len(gregory_aland) == 0:
        print(f"Cannot get GA number.")
        return

    # Get INTF ID
    m = re.match(r"P(\d+)", gregory_aland)
    if m:
        intf_id = 10000 + int(m.group(1))
    else:
        m = re.match(r"0(\d+)", gregory_aland)
        if m:
            intf_id = 20000 + int(m.group(1))
        elif gregory_aland.isdigit():
            intf_id = 30000 + int(gregory_aland)
        else:
            m = re.match(r"L(\d+)", gregory_aland)
            if m:
                intf_id = 40000 + int(m.group(1))
            else:
                print(f"Cannot get INTF ID from {gregory_aland}")
                return

    return intf_id


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
            tokens.append({"id": tok_id, "lemma": parts[2], "form": parts[1]})
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


def display_name_for_language(language):
    return language.replace("_", " ").replace("-", " ").title()


def display_siglum(manuscript_id, metadata):
    return (
        metadata.get("gregoryaland")
        or metadata.get("name")
        or manuscript_id
    )


def sidebar_sort_key(item):
    gregory_aland = item.get("gregoryaland")
    if gregory_aland:
        intf_id = gregory_aland_to_intf_id(gregory_aland)
        if intf_id is not None:
            return (0, intf_id, item["siglum"])
    return (1, item["siglum"])


def build_sidebar_sections(data_dir=DATA_DIR, href_prefix="../../../mss"):
    metadata_path = data_dir / "bilingual-mss.yaml"
    if not metadata_path.exists():
        return []

    metadata_by_id = yaml.safe_load(metadata_path.read_text(encoding="utf-8")) or {}

    sections = {}
    for manuscript_id, metadata in metadata_by_id.items():
        transcriptions = metadata.get("transcriptions") or {}
        languages = [language for language in transcriptions.keys()]

        if len(languages) < 2:
            continue

        category = "-".join(display_name_for_language(language) for language in languages[:2])
        sections.setdefault(category, []).append(
            {
                "siglum": display_siglum(manuscript_id, metadata),
                "gregoryaland": metadata.get("gregoryaland"),
                "href": f"{href_prefix}/{manuscript_id}/",
            }
        )

    return [
        {"title": title, "manuscripts": sorted(items, key=sidebar_sort_key)}
        for title, items in sorted(sections.items())
    ]


def build_home_page(sidebar_sections=None):
    if sidebar_sections is None:
        sidebar_sections = build_sidebar_sections(href_prefix="./mss")

    WEBSITE_DIR.mkdir(parents=True, exist_ok=True)
    home_html = home_template.render(sidebar_sections=sidebar_sections)
    (WEBSITE_DIR / "index.html").write_text(home_html, encoding="utf-8")

def render_highlighted_tokens(tokens, highlight_ids, no_space_after, highlight_class):
    highlight_set = set(highlight_ids or [])
    no_space_after_set = set(no_space_after or [])
    parts = []
    for index, token in enumerate(tokens):
        form = html.escape(token.get("form", ""))
        if token.get("id") in highlight_set:
            form = f'<span class="{highlight_class}">{form}</span>'
        parts.append(form)
        if index < len(tokens) - 1 and token.get("id") not in no_space_after_set:
            parts.append(" ")
    return "".join(parts)


def build_from_yaml(path:Path, sidebar_sections=None):
    my_data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    siglum = path.with_suffix("").name
    if sidebar_sections is None:
        sidebar_sections = build_sidebar_sections()

    ms_dir = MSS_DIR / siglum
    ms_dir.mkdir(parents=True, exist_ok=True)

    verse_list = list(my_data.keys())
    verse_items = []
    lemma_index = {}
    language_slugs = {}
    language_rtl = {}
    verse_label_by_id = {}
    verse_language_tokens = {}
    verse_language_no_space_after = {}
    verse_items = []
    for verse in verse_list:
        verse_data = my_data.get(verse) or {}
        language_keys = [key for key in verse_data.keys() if key != "alignment"]
        verbose = None
        for language in language_keys:
            verbose = verse_data.get(language, {}).get("verse")
            if verbose:
                break
        verse_label = verbose or verse
        verse_items.append({"id": verse, "label": verse_label})
        verse_label_by_id[verse] = verse_label

        if len(language_keys) >= 2:
            first_language = language_keys[0]
            second_language = language_keys[1]
            first_svg_id = svg_id_for(first_language)
            second_svg_id = svg_id_for(second_language)
            language_slugs[first_language] = first_svg_id
            language_slugs[second_language] = second_svg_id

            _, lang_a_no_space_after, lang_a_rtl, lang_a_tokens = parse_conllu(
                verse_data.get(first_language, {}).get("conllu", "").strip()
            )
            _, lang_b_no_space_after, lang_b_rtl, lang_b_tokens = parse_conllu(
                verse_data.get(second_language, {}).get("conllu", "").strip()
            )
            verse_language_tokens[(verse, first_language)] = lang_a_tokens
            verse_language_tokens[(verse, second_language)] = lang_b_tokens
            verse_language_no_space_after[(verse, first_language)] = lang_a_no_space_after
            verse_language_no_space_after[(verse, second_language)] = lang_b_no_space_after
            language_rtl[first_language] = lang_a_rtl or language_rtl.get(first_language, False)
            language_rtl[second_language] = lang_b_rtl or language_rtl.get(second_language, False)

            mapping = build_alignment_mapping(verse_data.get("alignment", ""), first_svg_id, second_svg_id)
            lang_a_id_to_lemma = {t["id"]: t["lemma"] for t in lang_a_tokens}
            lang_b_id_to_lemma = {t["id"]: t["lemma"] for t in lang_b_tokens}

            for token in lang_a_tokens:
                lemma = token["lemma"]
                if not lemma or lemma == "_":
                    continue
                lemma_data = lemma_index.setdefault(first_language, {}).setdefault(
                    lemma, {"count": 0, "parallel": 0, "aligned": {}, "unaligned": {}}
                )
                lemma_data["count"] += 1
                aligned_key = mapping.get(f"{first_svg_id}-{token['id']}")
                if aligned_key:
                    lemma_data["parallel"] += 1
                    _, aligned_id_str = aligned_key.rsplit("-", 1)
                    aligned_id = int(aligned_id_str)
                    other_lemma = lang_b_id_to_lemma.get(aligned_id)
                    if other_lemma and other_lemma != "_":
                        aligned = lemma_data["aligned"].setdefault(
                            other_lemma, {"count": 0, "examples": {}}
                        )
                        aligned["count"] += 1
                        example = aligned["examples"].setdefault(
                            verse,
                            {
                                "verse": verse,
                                "label": verse_label,
                                "other_language": second_language,
                                "highlight_ids_this": [],
                                "highlight_ids_other": [],
                            },
                        )
                        example["highlight_ids_this"].append(token["id"])
                        example["highlight_ids_other"].append(aligned_id)
                else:
                    unaligned = lemma_data["unaligned"].setdefault(
                        verse,
                        {"verse": verse, "label": verse_label, "highlight_ids_this": []},
                    )
                    unaligned["highlight_ids_this"].append(token["id"])

            for token in lang_b_tokens:
                lemma = token["lemma"]
                if not lemma or lemma == "_":
                    continue
                lemma_data = lemma_index.setdefault(second_language, {}).setdefault(
                    lemma, {"count": 0, "parallel": 0, "aligned": {}, "unaligned": {}}
                )
                lemma_data["count"] += 1
                aligned_key = mapping.get(f"{second_svg_id}-{token['id']}")
                if aligned_key:
                    lemma_data["parallel"] += 1
                    _, aligned_id_str = aligned_key.rsplit("-", 1)
                    aligned_id = int(aligned_id_str)
                    other_lemma = lang_a_id_to_lemma.get(aligned_id)
                    if other_lemma and other_lemma != "_":
                        aligned = lemma_data["aligned"].setdefault(
                            other_lemma, {"count": 0, "examples": {}}
                        )
                        aligned["count"] += 1
                        example = aligned["examples"].setdefault(
                            verse,
                            {
                                "verse": verse,
                                "label": verse_label,
                                "other_language": first_language,
                                "highlight_ids_this": [],
                                "highlight_ids_other": [],
                            },
                        )
                        example["highlight_ids_this"].append(token["id"])
                        example["highlight_ids_other"].append(aligned_id)
                else:
                    unaligned = lemma_data["unaligned"].setdefault(
                        verse,
                        {"verse": verse, "label": verse_label, "highlight_ids_this": []},
                    )
                    unaligned["highlight_ids_this"].append(token["id"])

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
            sidebar_sections=sidebar_sections,
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
            aligned_items = []
            for other_lemma, aligned in sorted(
                counts.get("aligned", {}).items(), key=lambda item: (-item[1]["count"], item[0])
            ):
                examples = []
                for ex in aligned.get("examples", {}).values():
                    tokens_this = verse_language_tokens.get((ex["verse"], language), [])
                    tokens_other = verse_language_tokens.get((ex["verse"], ex["other_language"]), [])
                    no_space_after_this = verse_language_no_space_after.get((ex["verse"], language), [])
                    no_space_after_other = verse_language_no_space_after.get(
                        (ex["verse"], ex["other_language"]), []
                    )
                    examples.append(
                        {
                            "verse_id": ex["verse"],
                            "label": ex["label"],
                            "text_this_html": render_highlighted_tokens(
                                tokens_this,
                                ex.get("highlight_ids_this", []),
                                no_space_after_this,
                                "highlight-main",
                            ),
                            "text_other_html": render_highlighted_tokens(
                                tokens_other,
                                ex.get("highlight_ids_other", []),
                                no_space_after_other,
                                "highlight-other",
                            ),
                            "rtl_this": language_rtl.get(language, False),
                            "rtl_other": language_rtl.get(ex["other_language"], False),
                            "other_language": ex["other_language"],
                        }
                    )
                aligned_items.append(
                    {
                        "lemma": other_lemma,
                        "count": aligned["count"],
                        "examples": examples,
                    }
                )
            unaligned_examples = []
            for ex in counts.get("unaligned", {}).values():
                tokens_this = verse_language_tokens.get((ex["verse"], language), [])
                no_space_after_this = verse_language_no_space_after.get((ex["verse"], language), [])
                unaligned_examples.append(
                    {
                        "verse_id": ex["verse"],
                        "label": ex["label"],
                        "text_this_html": render_highlighted_tokens(
                            tokens_this,
                            ex.get("highlight_ids_this", []),
                            no_space_after_this,
                            "highlight-main",
                        ),
                        "rtl_this": language_rtl.get(language, False),
                    }
                )
            lemma_html = lemma_template.render(
                siglum=siglum,
                language=language,
                language_slug=language_slug,
                lemma=lemma,
                lemma_items=lemma_items,
                occurrences=counts["count"],
                parallels=counts["parallel"],
                aligned_items=aligned_items,
                unaligned_examples=unaligned_examples,
                rtl=language_rtl.get(language, False),
            )
            (lemma_dir / "index.html").write_text(lemma_html, encoding="utf-8")
