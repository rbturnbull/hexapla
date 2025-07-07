from pathlib import Path
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape


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

for path in DATA_DIR.glob("*.yaml"):
    my_data = yaml.safe_load(path.read_text(encoding="utf-8"))
    print(my_data)
    siglum = path.with_suffix("").name

    ms_dir = MSS_DIR / siglum
    ms_dir.mkdir(parents=True, exist_ok=True)

    verse_list = list(my_data["verses"].keys())

    ms_path = ms_dir / "index.html"
    ms_html = ms_template.render(
        siglum=siglum,
        verse_list=verse_list,
    )
    ms_path.write_text(ms_html, encoding="utf-8")

    for verse_index, verse in enumerate(my_data["verses"]):
        verse_data = my_data["verses"][verse]
        verse_path = ms_dir / verse / f"index.html"
        verse_path.parent.mkdir(parents=True, exist_ok=True)

        greek = verse_data['Greek'].strip()
        latin = verse_data['Latin'].strip()
        mapping = verse_data["mapping"]

        verse_html = verse_template.render(
            siglum=siglum,
            verse_list=verse_list,
            verse=verse,
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
        )
        verse_js.write_text(verse_js_content, encoding="utf-8")
