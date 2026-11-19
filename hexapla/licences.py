"""
Licences given in a config file as SPDX ids (``CC-BY-NC-SA-4.0``), turned into a name and a link for the site.
"""
from __future__ import annotations

import re

CC_RE = re.compile(r"CC-(BY(?:-NC)?(?:-ND|-SA)?)(?:-(\d\.\d))?", re.IGNORECASE)
CC0_RE = re.compile(r"CC0(?:-1\.0)?", re.IGNORECASE)


def licence_info(value: str | None) -> dict | None:
    """ ``{"id", "name", "url"}`` for a licence: a Creative Commons SPDX id, a URL, or any other text. """
    if not value:
        return None
    if match := CC_RE.fullmatch(value):
        kind, version = match.group(1).upper(), match.group(2) or "4.0"
        return {"id": value, "name": f"CC {kind} {version}",
                "url": f"https://creativecommons.org/licenses/{kind.lower()}/{version}/"}
    if CC0_RE.fullmatch(value):
        return {"id": value, "name": "CC0 1.0", "url": "https://creativecommons.org/publicdomain/zero/1.0/"}
    if value.startswith(("http://", "https://")):
        return {"id": value, "name": value, "url": value}
    return {"id": value, "name": value, "url": None}
