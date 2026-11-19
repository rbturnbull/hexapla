"""
Reading word alignments as written by MCAligner (``mcaligner run``) and MCParser (``mcparser align``).

Two formats are accepted:

- **JSON Lines** (the alignment set that ``mcaligner run --target`` writes), one sentence pair per line::

    {"sent_id": "B06K01V07", "links": [{"source": "1", "target": "2", "sure": true, "confidence": 0.95, "agent": "aligner"}]}

- **YAML** (``mcparser align export -f yaml``): a mapping from ``sent_id`` to Ugarit-style links
  with CoNLL-U word ids, ``B06K01V07: 1-1S 2-3P``.

``source`` is a word of side A and ``target`` a word of side B, in the order the two
sources were given to MCAligner (``-a pred=grc,lat,...`` makes Greek side A).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

UGARIT_LINK_RE = re.compile(r"^(\d+)-(\d+)([SP]?)$", re.IGNORECASE)


@dataclass(frozen=True)
class Link:
    source: int
    target: int
    sure: bool = True
    confidence: float | None = None
    agent: str | None = None


def parse_ugarit(text: str) -> list[Link]:
    """ Parses Ugarit/Pharaoh links with CoNLL-U ids (``1-2S 3-5P``); a missing S/P means sure. """
    links = []
    for item in str(text or "").split():
        match = UGARIT_LINK_RE.match(item)
        if not match:
            raise ValueError(f"cannot read alignment link {item!r} (expected e.g. 3-5S)")
        source, target, kind = match.groups()
        links.append(Link(source=int(source), target=int(target), sure=kind.upper() != "P"))
    return links


def _link_from_json(data: dict) -> Link | None:
    try:
        source = int(data["source"])
        target = int(data["target"])
    except (KeyError, TypeError, ValueError):
        # e.g. empty nodes ("5.1"), which are not displayed
        return None
    confidence = data.get("confidence")
    return Link(
        source=source,
        target=target,
        sure=bool(data.get("sure", True)),
        confidence=float(confidence) if confidence is not None else None,
        agent=data.get("agent"),
    )


def read_links_jsonl(path: Path) -> dict[str, list[Link]]:
    alignment: dict[str, list[Link]] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as err:
            raise ValueError(f"{path}:{line_number}: invalid JSON: {err}") from err
        sent_id = str(record.get("sent_id", "")).strip()
        if not sent_id:
            raise ValueError(f"{path}:{line_number}: missing sent_id")
        links = [link for link in map(_link_from_json, record.get("links") or []) if link]
        # A later line for the same pair replaces an earlier one, as in MCParser's store.
        alignment[sent_id] = links
    return alignment


def read_links_yaml(path: Path) -> dict[str, list[Link]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a mapping from sent_id to links")
    alignment = {}
    for sent_id, links in data.items():
        try:
            alignment[str(sent_id)] = parse_ugarit(links)
        except ValueError as err:
            raise ValueError(f"{path}: {sent_id}: {err}") from err
    return alignment


def read_links(path: Path | str) -> dict[str, list[Link]]:
    """ Reads an alignment set (``.jsonl``) or Ugarit YAML export (``.yaml``/``.yml``), keyed by sent_id. """
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in {".jsonl", ".json"}:
        return read_links_jsonl(path)
    if suffix in {".yaml", ".yml"}:
        return read_links_yaml(path)
    raise ValueError(f"{path}: unknown alignment format {suffix!r} (expected .jsonl or .yaml)")
