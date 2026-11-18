"""
Reading what the site shows about a transcription from an IGNTP-style TEI file.

``read_transcription`` returns:

* the header: titles, shelfmark and identifiers, who made it, edition, publisher,
  licence, project and editorial notes, revision history;
* a summary of the body: folios, verses, corrections, lacunae, supplied and unclear text,
  nomina sacra;
* for each verse (keyed by the ``<ab n="John.1.25">`` reference): the folios its words are on and
  counts of corrections, lacunae, supplied and unclear text, and editorial notes.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

TEI_NS = "http://www.tei-c.org/ns/1.0"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"

# Links for identifiers listed in <altIdentifier type="...">.
IDENTIFIER_LINKS = {
    "TM": "https://www.trismegistos.org/text/{}",
    "LDAB": "https://www.trismegistos.org/ldab/text.php?tm={}",
}
NTVMR_URL = "https://ntvmr.uni-muenster.de/manuscript-workspace?docID={}"
IDENTIFIER_LABELS = {
    "GA": "Gregory-Aland",
    "Liste": "Liste",
    "TM": "Trismegistos",
    "LDAB": "LDAB",
    "smr": "Schmitz-Mink-Richter", "SMR": "Schmitz-Mink-Richter", "VetusLatina": "Vetus Latina",
    "NTVMR": "NTVMR",
    "partial": "Also",
    "VL": "Vetus Latina",
}


@dataclass
class VerseNotes:
    folios: list[str] = field(default_factory=list)
    corrections: int = 0
    lacunae: int = 0
    supplied: int = 0
    unclear: int = 0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "folios": self.folios,
            "corrections": self.corrections,
            "lacunae": self.lacunae,
            "supplied": self.supplied,
            "unclear": self.unclear,
            "notes": self.notes,
        }


@dataclass
class Transcription:
    path: Path
    header: dict
    summary: dict
    verses: dict[str, VerseNotes]
    problems: list[str] = field(default_factory=list)


def _local(tag) -> str:
    return tag.split("}")[-1] if isinstance(tag, str) else ""


def _children(element, name: str):
    return [child for child in element if _local(child.tag) == name]


def _find(element, path: str):
    """ Like ``element.find`` with un-namespaced names: ``_find(header, "fileDesc/titleStmt")``. """
    if element is None:
        return None
    for name in path.split("/"):
        matches = _children(element, name)
        if not matches:
            return None
        element = matches[0]
    return element


def _iter(element, name: str):
    return [el for el in element.iter() if _local(el.tag) == name] if element is not None else []


def _text(element) -> str:
    """ The element's text with whitespace collapsed; ``<ptr target>`` becomes its URL. """
    if element is None:
        return ""
    parts = []

    def walk(el):
        if el.text:
            parts.append(el.text)
        for child in el:
            if _local(child.tag) == "ptr" and child.get("target"):
                parts.append(child.get("target"))
            else:
                walk(child)
            if child.tail:
                parts.append(child.tail)

    walk(element)
    return re.sub(r"\s+", " ", "".join(parts)).strip()


def _ptrs(element) -> list[str]:
    return [ptr.get("target") for ptr in _iter(element, "ptr") if ptr.get("target")]


def _read_header(header) -> dict:
    file_desc = _find(header, "fileDesc")
    title_stmt = _find(file_desc, "titleStmt")
    titles = {}
    document = {}
    for title in _children(title_stmt, "title") if title_stmt is not None else []:
        kind = title.get("type") or "main"
        titles.setdefault(kind, _text(title))
        if kind == "document":
            document = {"key": title.get("key"), "n": title.get("n")}

    responsibility = []
    for resp_stmt in _children(title_stmt, "respStmt") if title_stmt is not None else []:
        responsibility.append({
            "resp": _text(_find(resp_stmt, "resp")),
            "names": [_text(name) for name in _children(resp_stmt, "name")],
        })
    funders = [_text(el) for el in _children(title_stmt, "funder")] if title_stmt is not None else []
    sponsors = [_text(el) for el in _children(title_stmt, "sponsor")] if title_stmt is not None else []

    edition = _find(file_desc, "editionStmt/edition")
    publication = _find(file_desc, "publicationStmt")
    availability = _find(publication, "availability")
    licence_text = _text(availability)
    licence_url = next(iter(_ptrs(availability)), None)
    if "<" in licence_text:  # HTML in a CDATA section, as the NTVMR writes it
        href = re.search(r'href="([^"]+)"', licence_text)
        licence_url = licence_url or (href.group(1) if href else None)
        licence_text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", licence_text)).strip()
    licence_name = None
    match = re.search(r"Creative Commons [A-Za-z\-]+(?: [A-Za-z\-]+)* [\d.]+(?: International)? License \(([^)]+)\)", licence_text)
    cc_url = re.search(r"creativecommons\.org/licenses/([a-z\-]+)/([\d.]+)", licence_url or "")
    if match:
        licence_name = match.group(1)
    elif cc_short := re.search(r"Creative Commons \(?(by(?:-n[cd])*(?:-sa)?)\b", licence_text, re.I):  # "(Creative Commons by-nc-sa)"
        licence_name = f"CC {cc_short.group(1).upper()}"
    elif cc_url:
        licence_name = f"CC {cc_url.group(1).upper()} {cc_url.group(2)}"
    elif re.search(r"non-?commercial", licence_text, re.I):
        licence_name = "free for non-commercial use"

    # A printed edition the transcription is based on (e.g. Streitberg for the Gothic), when there is no msDesc.
    source = []
    for bibl in _iter(_find(file_desc, "sourceDesc"), "biblStruct") + _iter(_find(file_desc, "sourceDesc"), "bibl"):
        monogr = _find(bibl, "monogr") or bibl
        parts = [_text(_find(monogr, key)) for key in ("author", "title", "edition", "imprint")]
        text = ". ".join(part.rstrip(".") for part in parts if part)
        if text:
            source.append(text)

    shelfmarks = []
    identifiers = []
    for ms_identifier in _iter(file_desc, "msIdentifier"):
        shelfmark = {}
        for key in ("country", "settlement", "repository", "idno", "msName"):
            element = _find(ms_identifier, key)
            if element is not None and _text(element):
                shelfmark[key] = _text(element)
        if shelfmark:
            shelfmarks.append(shelfmark)
        for alt in _children(ms_identifier, "altIdentifier"):
            kind = alt.get("type") or ""
            value = _text(_find(alt, "idno"))
            if not value:
                continue
            url = IDENTIFIER_LINKS.get(kind, "").format(value) or None
            if kind in ("Liste", "NTVMR"):
                url = NTVMR_URL.format(value)
            identifiers.append({"type": kind, "label": IDENTIFIER_LABELS.get(kind, kind), "value": value, "url": url})
    if document.get("key") and not any(identifier["type"] in ("Liste", "NTVMR") for identifier in identifiers):
        identifiers.append({"type": "NTVMR", "label": "NTVMR", "value": document["key"], "url": NTVMR_URL.format(document["key"])})

    encoding = _find(header, "encodingDesc")
    project = [_text(p) for p in _children(_find(encoding, "projectDesc"), "p")] if _find(encoding, "projectDesc") is not None else []
    editorial = [_text(p) for p in _children(_find(encoding, "editorialDecl"), "p")] if _find(encoding, "editorialDecl") is not None else []

    revisions = []
    for change in _iter(_find(header, "revisionDesc"), "change"):
        revisions.append({"when": change.get("when"), "n": change.get("n"), "text": _text(change)})

    return {
        "title": titles.get("main") or (f"GA {titles['document']}" if titles.get("document") else ""),
        "document": titles.get("document", ""),
        "document_key": document.get("key"),
        "work": titles.get("work", ""),
        "responsibility": responsibility,
        "funders": funders,
        "sponsors": sponsors,
        "edition": _text(edition),
        "edition_n": edition.get("n") if edition is not None else None,
        "publishers": [_text(name) for name in _iter(_find(publication, "publisher"), "name")],
        "authority": _text(_find(publication, "authority")),
        "source": source,
        "published": _text(_find(publication, "date")),
        "licence": licence_text,
        "licence_name": licence_name,
        "licence_url": licence_url,
        "shelfmark": shelfmarks[0] if shelfmarks else {},
        "shelfmarks": shelfmarks,
        "identifiers": identifiers,
        "project": project,
        "editorial": editorial,
        "revisions": revisions,
    }


FOLIO_NOTE = re.compile(r"\d+[rv]")


def _find_restarts(text_element) -> set[int]:
    """
    Where verse numbers restart inside a chapter, as positions in the sequence of <ab n> elements.
    A drop in verse number starts a run (up to the next drop or chapter). The run is a restart when it repeats a
    verse already seen in the chapter: sa117 labels John 6:21-58 as John.4.21-58 after John.4.45-52. A run of new
    numbers is just fragments out of order (ac1: John.13.13 before 13.10-12) and keeps its labels.
    """
    if text_element is None:
        return set()
    chapters: list[list[tuple[int, str, int]]] = [[]]
    index = -1
    for element in text_element.iter():
        if not isinstance(element.tag, str):
            continue
        name = _local(element.tag)
        if name == "div" and element.get("type") == "chapter":
            chapters.append([])
        elif name == "ab" and element.get("n"):
            index += 1
            match = re.fullmatch(r"(.*)\.(\d+)", element.get("n"))
            if match:
                chapters[-1].append((index, element.get("n"), int(match.group(2))))
    starts = set()
    for abs_ in chapters:
        runs: list[list[tuple[int, str, int]]] = []
        for item in abs_:
            if not runs or item[2] < runs[-1][-1][2]:
                runs.append([])
            runs[-1].append(item)
        seen = set()
        for k, run in enumerate(runs):
            refs = {ref for _, ref, _ in run}
            if k > 0 and refs & seen:
                starts.add(run[0][0])
            seen |= refs
    return starts


def _read_body(text_element, renumber_restarts: list[str]) -> tuple[dict, dict[str, VerseNotes], list[str]]:
    verses: dict[str, VerseNotes] = {}
    problems: list[str] = []
    restarts = 0  # how many times verse numbers have dropped back inside a chapter, across the file
    chapter = {"restart": None}
    restart_starts = _find_restarts(text_element)  # positions (in <ab n> order) where a restart begins
    ab_index = -1
    folios: list[dict] = []
    totals = Counter()
    gaps = Counter()
    current_folio: str | None = None
    # Files without <w> (D-Codex): words are counted from the text, and a verse is on the folios its text is on.
    has_words = text_element is not None and any(_local(el.tag) == "w" for el in text_element.iter() if isinstance(el.tag, str))

    def on_text(text: str | None, verse: VerseNotes | None):
        if has_words or verse is None or not text:
            return
        words = [token for token in text.split() if token.strip("_-/.·:")]
        totals["words"] += len(words)
        if words and current_folio and current_folio not in verse.folios:
            verse.folios.append(current_folio)

    def walk(element, verse: VerseNotes | None):
        nonlocal current_folio
        if not isinstance(element.tag, str):  # comments, processing instructions
            return
        name = _local(element.tag)
        if name == "pb":
            current_folio = element.get("n") or element.get(XML_ID)
            folios.append({"n": current_folio, "type": element.get("type")})
        elif name == "div" and element.get("type") == "chapter":
            chapter.update(restart=None)
        elif name == "ab" and element.get("n"):
            nonlocal ab_index
            ab_index += 1
            verse = verses.setdefault(_renumber(element.get("n"), ab_index), VerseNotes())
        elif name == "app":
            totals["corrections"] += 1
            if verse is not None:
                verse.corrections += 1
        elif name == "gap":
            reason = element.get("reason") or "gap"
            gaps[reason] += 1
            if reason == "lacuna" or (reason == "gap" and not has_words):  # a bare <gap/> in D-Codex is lost text
                totals["lacunae"] += 1
                if verse is not None:
                    verse.lacunae += 1
        elif name == "supplied":
            totals["supplied"] += 1
            if verse is not None:
                verse.supplied += 1
        elif name == "unclear":
            totals["unclear"] += 1
            if verse is not None:
                verse.unclear += 1
        elif name == "abbr" and element.get("type") == "nomSac":
            totals["nomina_sacra"] += 1
        elif name == "note":
            note = _text(element)
            if not has_words and FOLIO_NOTE.fullmatch(note):  # D-Codex marks folios with <note>1r</note>
                current_folio = note
                folios.append({"n": note, "type": "folio"})
            elif verse is not None and note:
                verse.notes.append(note)
        elif name == "w":
            totals["words"] += 1
            # A verse is on the folios its words are on (an <ab> can run on past page breaks after its last word).
            if verse is not None and current_folio and current_folio not in verse.folios:
                verse.folios.append(current_folio)
        if name not in ("note", "teiHeader"):
            on_text(element.text, verse)
        for child in element:
            walk(child, verse)
            on_text(child.tail, verse)

    def _renumber(ref: str, index: int) -> str:
        """ Some files restart the verse numbers inside a chapter (a run of chapter 6 labelled John.4.21...).
        Each restart is relabelled with the next chapter in ``renumber_restarts``, or left out if none is given. """
        nonlocal restarts
        match = re.fullmatch(r"(.*)\.(\d+)", ref)
        if not match:
            return ref
        number = int(match.group(2))
        if index in restart_starts:
            restarts += 1
            chapter["restart"] = restarts
            if restarts <= len(renumber_restarts):
                problems.append(f"verse numbers restart at {ref}; relabelled as {renumber_restarts[restarts - 1]}.{number} onwards")
            else:
                problems.append(f"verse numbers restart at {ref}; these verses are left out (set renumber_restarts to relabel them)")
        if chapter["restart"] is None:
            return ref
        if chapter["restart"] <= len(renumber_restarts):
            return f"{renumber_restarts[chapter['restart'] - 1]}.{number}"
        return f"{ref}#restart{chapter['restart']}"

    if text_element is not None:
        walk(text_element, None)
    for ref in [ref for ref in verses if "#restart" in ref]:
        del verses[ref]

    refs = list(verses)
    summary = {
        "folios": [folio["n"] for folio in folios if folio["n"]],
        # "page" when every break is a numbered page (<pb type="page">), else "folio"
        "unit": "page" if folios and all(folio["type"] == "page" for folio in folios) else "folio",
        "verses": len(refs),
        "first": refs[0] if refs else None,
        "last": refs[-1] if refs else None,
        "words": totals["words"],
        "corrections": totals["corrections"],
        "lacunae": totals["lacunae"],
        "supplied": totals["supplied"],
        "unclear": totals["unclear"],
        "nomina_sacra": totals["nomina_sacra"],
        "gaps": dict(gaps),
    }
    return summary, verses, problems


def read_transcription(path: Path | str, renumber_restarts: list[str] | None = None) -> Transcription:
    path = Path(path)
    root = ET.parse(path).getroot()
    header = _find(root, "teiHeader")
    text_element = _find(root, "text")
    header_info = _read_header(header) if header is not None else {}
    summary, verses, problems = _read_body(text_element, list(renumber_restarts or []))
    return Transcription(path=path, header=header_info, summary=summary, verses=verses, problems=problems)
