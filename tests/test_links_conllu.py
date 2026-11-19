import json

import pytest

from hexapla.conllu import Word, parse_conllu, read_conllu
from hexapla.links import Link, parse_ugarit, read_links

CONLLU = """# sent_id = V7
# text = εγραψα υμιν .
# not a key value comment
1	εγραψα	γράφω	VERB	V-	_	0	root	_	Conf=form:0.97
2-3	υμιν.	_	_	_	_	_	_	_	SpaceAfter=No
2	υμιν	ὑμεῖς	PRON	Pp	_	1	obl	_	_
3	.	.	PUNCT	_	_	_	_	_	_
3.1	x	x	X	_	_	_	_	_	_
x-y	ignored range

1	anonymous	_	X
"""


def test_parse_conllu():
    first, second = parse_conllu(CONLLU)
    assert first.sent_id == "V7"
    assert [w.id for w in first.words] == [1, 2, 3]
    assert first.words[2].head is None  # "_" head from mcparser
    assert first.no_space_after == [2, 3]
    assert first.text == "εγραψα υμιν ."
    assert first.word_ids == {1, 2, 3}
    assert first.to_conllu().splitlines()[2] == "3\t.\t.\tPUNCT\t_\t_\t_\t_\t_\t_"
    assert second.sent_id == "s1" and second.text == "anonymous"
    assert second.words[0].lemma == "_" and second.words[0].misc_dict == {}


def test_parse_conllu_errors(tmp_path):
    with pytest.raises(ValueError, match="tab-separated"):
        parse_conllu("1 no tabs here")
    with pytest.raises(ValueError, match="cannot read word id"):
        parse_conllu("one\tword")
    path = tmp_path / "x.conllu"
    path.write_text(CONLLU, encoding="utf-8")
    assert len(read_conllu(path)) == 2


def test_word_misc():
    assert Word(id=1, form="x", misc="SpaceAfter=No|Ref=ROM_1.7").misc_dict == {"SpaceAfter": "No", "Ref": "ROM_1.7"}


def test_parse_ugarit():
    assert parse_ugarit("1-2S 3-5P 4-4") == [Link(1, 2, True), Link(3, 5, False), Link(4, 4, True)]
    assert parse_ugarit(None) == []
    with pytest.raises(ValueError):
        parse_ugarit("1-2-3S")


def test_read_links_formats(tmp_path):
    jsonl = tmp_path / "a.jsonl"
    jsonl.write_text(
        json.dumps({"sent_id": "V1", "links": [
            {"source": "1", "target": "2", "sure": False, "confidence": 0.5, "agent": "aligner"},
            {"source": "5.1", "target": "2"},
        ]}) + "\n\n" + json.dumps({"sent_id": "V2"}) + "\n"
    )
    assert read_links(jsonl) == {"V1": [Link(1, 2, False, 0.5, "aligner")], "V2": []}

    yml = tmp_path / "a.yaml"
    yml.write_text("V1: 1-2P 3-3S\n")
    assert read_links(yml) == {"V1": [Link(1, 2, False), Link(3, 3, True)]}
    empty = tmp_path / "empty.yml"
    empty.write_text("")
    assert read_links(empty) == {}


@pytest.mark.parametrize("name, text, message", [
    ("bad.jsonl", "{oops", "invalid JSON"),
    ("bad.jsonl", '{"links": []}', "missing sent_id"),
    ("bad.yaml", "- a list", "expected a mapping"),
    ("bad.yaml", "V1: 1-2-3", "V1"),
    ("bad.txt", "", "unknown alignment format"),
])
def test_read_links_errors(tmp_path, name, text, message):
    path = tmp_path / name
    path.write_text(text)
    with pytest.raises(ValueError, match=message):
        read_links(path)
