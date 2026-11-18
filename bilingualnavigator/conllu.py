"""
Reading CoNLL-U files as written by MCParser (``mcparser run``).

MCParser keeps every comment of its input file (``# sent_id``, ``# text`` and any
extra ones such as ``# verse = Romans 1:7``) and adds per-cell confidences to MISC
(``Conf=form:0.97,lemma:0.88,...``). Only the basic word lines are used for display:
multiword token ranges (``3-4``) mark words written without a space between them,
and empty nodes (``5.1``) are skipped.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

COMMENT_RE = re.compile(r"^#\s*([^=]+?)\s*=\s?(.*)$")


@dataclass
class Word:
    id: int
    form: str
    lemma: str = "_"
    upos: str = "_"
    xpos: str = "_"
    feats: str = "_"
    head: int | None = None
    deprel: str = "_"
    deps: str = "_"
    misc: str = "_"

    @property
    def misc_dict(self) -> dict[str, str]:
        if not self.misc or self.misc == "_":
            return {}
        result = {}
        for item in self.misc.split("|"):
            key, _, value = item.partition("=")
            result[key] = value
        return result

    def to_line(self) -> str:
        head = "_" if self.head is None else str(self.head)
        return "\t".join(
            [str(self.id), self.form, self.lemma, self.upos, self.xpos, self.feats, head, self.deprel, self.deps, self.misc]
        )


@dataclass
class Sentence:
    sent_id: str
    comments: dict[str, str] = field(default_factory=dict)
    words: list[Word] = field(default_factory=list)
    no_space_after: list[int] = field(default_factory=list)

    @property
    def text(self) -> str:
        if "text" in self.comments:
            return self.comments["text"]
        return " ".join(word.form for word in self.words)

    @property
    def word_ids(self) -> set[int]:
        return {word.id for word in self.words}

    def to_conllu(self) -> str:
        """ The basic word lines, as used by the verse page's JavaScript. """
        return "\n".join(word.to_line() for word in self.words)

    def ref_candidates(self) -> list[str]:
        """ Strings that may hold a Bible reference for this sentence, most specific first. """
        candidates = []
        for key in ("verse", "ref", "reference", "verse_ref", "bibleref"):
            if self.comments.get(key):
                candidates.append(self.comments[key])
        candidates.append(self.sent_id)
        for word in self.words[:1]:
            ref = word.misc_dict.get("Ref")
            if ref:
                candidates.append(ref)
        return candidates


def _parse_int(value: str) -> int | None:
    try:
        return int(value)
    except ValueError:
        return None


def parse_conllu(text: str, source: str = "<string>") -> list[Sentence]:
    """ Parses CoNLL-U text into sentences, in file order. """
    sentences: list[Sentence] = []
    comments: dict[str, str] = {}
    words: list[Word] = []
    no_space_after: set[int] = set()
    anonymous = 0

    def flush():
        nonlocal comments, words, no_space_after, anonymous
        if words:
            sent_id = comments.get("sent_id")
            if not sent_id:
                anonymous += 1
                sent_id = f"s{anonymous}"
            for word in words:
                if word.misc_dict.get("SpaceAfter") == "No":
                    no_space_after.add(word.id)
            sentences.append(
                Sentence(sent_id=sent_id, comments=comments, words=words, no_space_after=sorted(no_space_after))
            )
        comments, words, no_space_after = {}, [], set()

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.rstrip("\r\n")
        if not line.strip():
            flush()
            continue
        if line.startswith("#"):
            match = COMMENT_RE.match(line)
            if match:
                comments[match.group(1).strip()] = match.group(2).strip()
            continue

        columns = line.split("\t")
        if len(columns) < 2:
            raise ValueError(f"{source}:{line_number}: expected tab-separated CoNLL-U columns")
        columns += ["_"] * (10 - len(columns))
        token_id = columns[0]

        if "-" in token_id:
            start, _, end = token_id.partition("-")
            start_id, end_id = _parse_int(start), _parse_int(end)
            if start_id is not None and end_id is not None:
                no_space_after.update(range(start_id, end_id))
                if "SpaceAfter=No" in columns[9]:
                    no_space_after.add(end_id)
            continue
        if "." in token_id:
            continue

        word_id = _parse_int(token_id)
        if word_id is None:
            raise ValueError(f"{source}:{line_number}: cannot read word id {token_id!r}")

        words.append(
            Word(
                id=word_id,
                form=columns[1],
                lemma=columns[2],
                upos=columns[3],
                xpos=columns[4],
                feats=columns[5],
                head=_parse_int(columns[6]),
                deprel=columns[7],
                deps=columns[8],
                misc=columns[9],
            )
        )
    flush()
    return sentences


def read_conllu(path: Path | str) -> list[Sentence]:
    path = Path(path)
    return parse_conllu(path.read_text(encoding="utf-8"), source=str(path))
