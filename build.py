#!/usr/bin/env python3

from pathlib import Path
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

def normalize_conllu(conllu):
    lines = []
    for line in conllu.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        token_id = line.split("\t", 1)[0]
        if "-" in token_id or "." in token_id:
            continue
        lines.append(line)
    return "\n".join(lines)


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

    ms_path = ms_dir / "index.html"
    ms_html = ms_template.render(
        siglum=siglum,
        verse_list=verse_list,
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

        greek = normalize_conllu(verse_data[first_language].get("conllu", "").strip())
        latin = normalize_conllu(verse_data[second_language].get("conllu", "").strip())
        alignment = verse_data.get("alignment", "")
        mapping = build_alignment_mapping(alignment, first_svg_id, second_svg_id)

        verse_html = verse_template.render(
            siglum=siglum,
            verse_list=verse_list,
            verse=verse,
            lang_a_label=first_language,
            lang_b_label=second_language,
            lang_a_id=first_svg_id,
            lang_b_id=second_svg_id,
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
        )
        verse_js.write_text(verse_js_content, encoding="utf-8")
