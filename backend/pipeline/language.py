"""Stage 3: tag each token's language (English / Urdu-Hindi / Arabizi / Arabic / unknown).

Two passes:
  tag_initial  - before normalization: exact word-list hits and surface rules
  refine       - after concept mapping: a token we first called 'unknown' takes the language of
                 the word list its match came from; remaining unknowns may borrow from context.
The tag is explanatory: it tells the customer and the store *which way of writing* was used.
"""
from __future__ import annotations

import re
from collections import Counter

from .lexicon import Resources, lookup_key
from .script import ARABIC, DIGITS

ENGLISH, ROMAN_URDU, ARABIZI, ARABIC_LANG, UNKNOWN_LANG = (
    "english", "roman_urdu", "arabizi", "arabic", "unknown")

# A digit used as a letter: touching a letter on at least one side (3eish, la7m, na3na3).
# Only digits that stand for Arabic sounds count; 1/4/0 are not used as letters in common Arabizi.
_ARABIZI_SHAPE = re.compile(r"[a-z][235679]|[235679][a-z]")

# Urdu/Hindi possessive and agentive endings attached to a word ("doodhwala", "chaiwali").
_ROMAN_URDU_SUFFIX = re.compile(r"[a-z]{2,}(wala|wali|wale|walay)$")


def tag_initial(norm: str, script: str, res: Resources) -> tuple[str, str]:
    """(language, reason) from exact lookups and surface rules only, before normalization."""
    if script == ARABIC:
        return ARABIC_LANG, "written in Arabic script"
    if script == DIGITS:
        return UNKNOWN_LANG, "number"
    key = lookup_key(norm)
    if key in res.exact:
        langs = res.exact[key].languages
        return "+".join(langs), f"found in the {_labels(langs, res)} word list"
    if key in res.fillers:
        langs = res.fillers[key]
        return "+".join(langs), f"common {_labels(langs, res)} connecting word"
    if _ARABIZI_SHAPE.search(norm):
        return ARABIZI, "digits used as Arabic letters (3=ع, 7=ح, 5=خ...)"
    if _ROMAN_URDU_SUFFIX.search(norm):
        return ROMAN_URDU, 'Urdu/Hindi ending "-wala/-wali"'
    return UNKNOWN_LANG, "no language cue yet"


def refine(lang: str, reason: str, script: str, match_languages: list[str], method: str,
           phrase: str | None, res: Resources) -> tuple[str, str]:
    """After mapping: fill an unknown language from the word list the match came from."""
    if phrase and match_languages:  # both words of a phrase share the phrase's language
        return "+".join(match_languages), f'part of the {_labels(match_languages, res)} term "{phrase}"'
    if script != ARABIC and match_languages == [ARABIC_LANG]:
        # Latin letters that only matched after transliteration: an Arabic word typed in Latin.
        return ARABIZI, "Arabic word written in Latin letters"
    if lang != UNKNOWN_LANG or not match_languages:
        return lang, reason
    via = "closest to" if method not in ("catalog_word",) else "found in"
    what = "catalog product names" if method == "catalog_word" else f"the {_labels(match_languages, res)} word list"
    return "+".join(match_languages), f"{via} {what}"


def fill_from_context(langs: list[str]) -> str | None:
    """If the other words in the query agree on one non-English language, return it.
    Used only to label still-unknown tokens (e.g. 'xyz ka' -> probably Urdu/Hindi)."""
    counts = Counter(p for l in langs if l != UNKNOWN_LANG for p in l.split("+") if p != ENGLISH)
    if len(counts) == 1:
        return next(iter(counts))
    return None


def _labels(langs: list[str], res: Resources) -> str:
    return " / ".join(res.language_labels.get(l, l) for l in langs)


def label(lang: str, res: Resources) -> str:
    return _labels(lang.split("+"), res)
