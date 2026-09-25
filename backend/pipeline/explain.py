"""Stage 8: the explanation object. One entry per token: original -> normalized -> concept ->
confidence -> which rule produced it. This is exactly what the UI chips render."""
from __future__ import annotations

from .concepts import CONCEPT, FILLER, GUESSED, KEYWORD, METHOD_TEXT, QUANTITY, SURE, Match
from .language import label
from .lexicon import Resources


def concept_label(concept: str, res: Resources) -> str:
    return res.concepts[concept]["en"]


def token_explanation(original: str, script: str, lang: str, lang_reason: str,
                      m: Match, res: Resources) -> dict:
    return {
        "original": original,
        "normalized": m.normalized,
        "script": script,
        "language": lang,
        "language_label": label(lang, res),
        "language_reason": lang_reason,
        "role": m.role,
        "concepts": m.concepts,
        "concept_labels": [concept_label(c, res) for c in m.concepts],
        "keyword": m.keyword,
        "confidence": m.confidence,
        "score": m.score,
        "similar_to": m.similar_to,
        "matched_form": m.matched_form,
        "method": m.method,
        "why": METHOD_TEXT.get(m.method, m.method),
        "steps": m.steps,
        "notes": m.notes,
        "phrase": m.phrase,
    }


def _meaning(t: dict) -> str:
    if t["role"] == KEYWORD:
        return f'the product word "{t["keyword"]}"'
    labels = t["concept_labels"]
    return " or ".join(labels)


def sentence(t: dict) -> str | None:
    """Plain-English line for one token, or None if it's not worth saying (fillers, quantities)."""
    if t["role"] in (FILLER, QUANTITY):
        return None
    word = t["phrase"] or t["original"]
    lang = f' ({t["language_label"]})' if t["language"] != "unknown" else ""
    if t["method"] == "store_approved":
        return f'We read "{word}" as {_meaning(t)}: learned from shoppers and approved by the store.'
    if t["confidence"] == SURE:
        return f'We read "{word}" as {_meaning(t)}{lang}.'
    if t["confidence"] == GUESSED:
        if len(t["concepts"]) > 1:
            return f'"{word}" can mean {_meaning(t)}{lang}, so we show both.'
        closeness = f', {t["score"]}% similar to "{t["similar_to"]}"' if t["score"] is not None else ""
        return f'We guessed "{word}" means {_meaning(t)}{lang}{closeness}.'
    return f'We don\'t know "{word}" yet, so we kept it as typed and did not guess.'


def summary(tokens: list[dict]) -> list[str]:
    seen, lines = set(), []
    for t in tokens:
        s = sentence(t)
        key = t["phrase"] or t["original"]
        if s and key not in seen:  # a two-word phrase would otherwise be described twice
            seen.add(key)
            lines.append(s)
    return lines
