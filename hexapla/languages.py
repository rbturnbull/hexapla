"""
Names and writing direction for the language codes used in ``<text xml:lang>`` (ISO 639 with optional subtags).
"""
from __future__ import annotations

LANGUAGE_NAMES = {
    "grc": "Greek", "el": "Greek", "gre": "Greek", "ell": "Greek",
    "la": "Latin", "lat": "Latin",
    "ar": "Arabic", "ara": "Arabic", "arb": "Arabic",
    "cop": "Coptic",
    "got": "Gothic",
    "syc": "Syriac", "syr": "Syriac",
    "hy": "Armenian", "hye": "Armenian", "arm": "Armenian", "xcl": "Armenian",
    "ka": "Georgian", "kat": "Georgian", "geo": "Georgian", "oge": "Georgian",
    "gez": "Ge'ez",
    "he": "Hebrew", "heb": "Hebrew", "hbo": "Hebrew",
    "cu": "Church Slavonic", "chu": "Church Slavonic",
    "en": "English", "eng": "English",
    "de": "German", "deu": "German", "ger": "German",
    "fr": "French", "fra": "French", "fre": "French",
}

RTL_LANGUAGES = {"ar", "ara", "arb", "syc", "syr", "he", "heb", "hbo"}


def _base(code: str) -> str:
    """ ``cop-x-sa`` → ``cop``, ``en-GB`` → ``en``. """
    return code.split("-")[0].lower()


def language_name(code: str) -> str:
    return LANGUAGE_NAMES.get(_base(code), _base(code).upper())


def is_rtl(code: str) -> bool:
    return _base(code) in RTL_LANGUAGES
