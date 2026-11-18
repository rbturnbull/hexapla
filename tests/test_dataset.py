import json
import re
import shutil
from pathlib import Path

import pytest
import yaml

from bilingualnavigator.alignment import Link, parse_ugarit, read_alignment
from bilingualnavigator.build import build_website, word_map
from bilingualnavigator.conllu import parse_conllu
from bilingualnavigator.dataset import DatasetError, load_dataset, load_datasets, resolve_verse

SAMPLE = Path(__file__).parent / "data" / "claromontanus-sample"

CONLLU = """# sent_id = V7
# text = εγραψα υμιν .
# verse = 1John 2:14
1	εγραψα	γράφω	VERB	V-	_	0	root	_	Conf=form:0.97
2-3	υμιν.	_	_	_	_	_	_	_	_
2	υμιν	ὑμεῖς	PRON	Pp	_	1	obl	_	_
3	.	.	PUNCT	_	_	_	_	_	SpaceAfter=No
3.1	x	x	X	_	_	_	_	_	_

# sent_id = 12
1	x	x	X	_	_	0	root	_	Ref=ROM_1.7
"""


def test_parse_conllu():
    first, second = parse_conllu(CONLLU)
    assert first.sent_id == "V7"
    assert first.comments["verse"] == "1John 2:14"
    assert [w.id for w in first.words] == [1, 2, 3]
    assert first.words[2].head is None  # "_" head from mcparser
    assert first.no_space_after == [2, 3]
    assert first.text == "εγραψα υμιν ."
    assert second.text == "x"


def test_resolve_verse():
    first, second = parse_conllu(CONLLU)
    assert resolve_verse(first) == ("B23K02V14", "1 John 2:14")
    assert resolve_verse(second) == ("B06K01V07", "Romans 1:7")  # from MISC Ref=


def test_parse_ugarit():
    assert parse_ugarit("1-2S 3-5P 4-4") == [Link(1, 2, True), Link(3, 5, False), Link(4, 4, True)]
    with pytest.raises(ValueError):
        parse_ugarit("1-2-3S")


def test_read_alignment_formats(tmp_path):
    jsonl = tmp_path / "a.jsonl"
    jsonl.write_text(
        json.dumps({"sent_id": "V1", "links": [
            {"source": "1", "target": "2", "sure": False, "confidence": 0.5, "agent": "aligner"},
            {"source": "5.1", "target": "2"},
        ]}) + "\n"
    )
    assert read_alignment(jsonl) == {"V1": [Link(1, 2, False, 0.5, "aligner")]}

    yml = tmp_path / "a.yaml"
    yml.write_text("V1: 1-2P 3-3S\n")
    assert read_alignment(yml) == {"V1": [Link(1, 2, False), Link(3, 3, True)]}


def test_load_sample_dataset():
    dataset = load_dataset(SAMPLE)
    assert dataset.id == "claromontanus-sample"
    assert dataset.category == "Greek-Latin"
    assert dataset.siglum == "06"
    assert [v.id for v in dataset.verses] == ["B06K01V07", "B06K01V08", "B06K01V09"]
    assert dataset.verses[0].label == "Romans 1:7"
    assert dataset.verses[0].links and dataset.problems == []
    assert not dataset.lang_a.rtl


def copy_sample(tmp_path, **changes):
    target = tmp_path / "datasets" / "claro"
    shutil.copytree(SAMPLE, target)
    manifest = yaml.safe_load((target / "dataset.yaml").read_text())
    for key, value in changes.items():
        manifest[key] = value
    (target / "dataset.yaml").write_text(yaml.safe_dump(manifest, allow_unicode=True))
    return target


def test_swapped_alignment_sides(tmp_path):
    target = copy_sample(tmp_path, alignment={"path": "alignment.jsonl", "source": "latin", "target": "greek"})
    original = load_dataset(SAMPLE).verses[0].links
    # Pretend the aligner was run with Latin as side A: the file's source/target are swapped.
    lines = [json.loads(line) for line in (target / "alignment.jsonl").read_text().splitlines()]
    for record in lines:
        for link in record["links"]:
            link["source"], link["target"] = link["target"], link["source"]
    (target / "alignment.jsonl").write_text("\n".join(json.dumps(r) for r in lines))
    assert load_dataset(target).verses[0].links == original


def test_bad_links_are_reported(tmp_path):
    target = copy_sample(tmp_path)
    with open(target / "alignment.jsonl", "a") as f:
        f.write(json.dumps({"sent_id": "B06K01V09", "links": [{"source": "999", "target": "1", "sure": True}]}) + "\n")
    dataset = load_dataset(target)
    assert any("999-1" in problem for problem in dataset.problems)
    assert all(link.source != 999 for verse in dataset.verses for link in verse.links)


def test_filters(tmp_path):
    target = copy_sample(tmp_path, alignment={"path": "alignment.jsonl", "min_confidence": 0.96, "include_probable": False})
    links = [link for verse in load_dataset(target).verses for link in verse.links]
    assert links and all(link.sure and link.confidence >= 0.96 for link in links)


def test_manifest_errors(tmp_path):
    target = copy_sample(tmp_path, languages=[{"id": "greek", "conllu": "greek.conllu"}])
    with pytest.raises(DatasetError, match="exactly two"):
        load_dataset(target)
    with pytest.warns(UserWarning, match="Skipping claro"):
        assert load_datasets(tmp_path / "datasets") == []


def test_word_map_many_to_many():
    dataset = load_dataset(SAMPLE)
    verse = dataset.verses[1]
    mapping = word_map(verse, dataset.lang_a, dataset.lang_b)
    source = next(link.source for link in verse.links)
    partners = mapping[f"greek-{source}"]
    assert {p["svgId"] for p in partners} == {"latin"}
    assert sum(len(v) for k, v in mapping.items() if k.startswith("greek-")) == len(verse.links)


def test_build_website(tmp_path):
    copy_sample(tmp_path)
    website = tmp_path / "website"
    (website / "mss" / "stale").mkdir(parents=True)
    datasets = load_datasets(tmp_path / "datasets")
    build_website(datasets, website)

    assert not (website / "mss" / "stale").exists()
    home = (website / "index.html").read_text()
    assert "./mss/claro/" in home and "Greek-Latin" in home

    verse_dir = website / "mss" / "claro" / "B06K01V07"
    page = (verse_dir / "index.html").read_text()
    assert "Romans 1:7" in page and "Codex Claromontanus (sample)" in page
    js = (verse_dir / "claro-B06K01V07.js").read_text()
    word_map_json = re.search(r"const wordMap = (.*);", js).group(1)
    assert all(isinstance(v, list) for v in json.loads(word_map_json).values())

    lemma_pages = list((website / "mss" / "claro" / "latin").glob("*/index.html"))
    assert lemma_pages
    assert (website / "mss" / "claro" / "greek" / "χάρις" / "index.html").exists()
