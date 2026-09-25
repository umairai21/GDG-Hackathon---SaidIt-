"""Runs the stages in order: tokenize -> script -> language -> normalize+map -> confidence ->
search -> explanation. No network, no model, no API key."""
from __future__ import annotations

from .concepts import FILLER, QUANTITY, find_phrases, map_token
from .explain import summary, token_explanation
from .language import UNKNOWN_LANG, fill_from_context, refine, tag_initial
from .lexicon import Resources, default_resources
from .script import LATIN, MIXED, detect_script
from .search import search
from .tokenizer import tokenize


def interpret(query: str, res: Resources | None = None, top_k: int = 10,
              approved: dict[str, str] | None = None) -> dict:
    """approved: store-approved learned mappings {token: concept}; None = lexicon only (used by eval)."""
    res = res or default_resources()
    tokens, quantity = tokenize(query)
    phrase_matches = find_phrases(tokens, res)

    rows = []  # (token, script, lang, reason, match)
    for tok in tokens:
        script = detect_script(tok.text)
        lang, reason = tag_initial(tok.norm, script, res)
        match = phrase_matches.get(tok.index) or map_token(tok, script, res, approved)
        lang, reason = refine(lang, reason, script, match.languages, match.method, match.phrase, res)
        rows.append([tok, script, lang, reason, match])

    # Label still-unknown Latin words by the language of the rest of the query.
    context = fill_from_context([r[2] for r in rows])
    if context:
        for r in rows:
            if r[2] == UNKNOWN_LANG and r[1] in (LATIN, MIXED) and r[4].role not in (QUANTITY,):
                r[2], r[3] = context, "guessed from the other words in the query"

    explanations = [token_explanation(tok.text, script, lang, reason, m, res)
                    for tok, script, lang, reason, m in rows]
    results = search([r[4] for r in rows], quantity, res, top_k=top_k)

    return {
        "query": query,
        "tokens": explanations,
        "quantity": None if quantity is None else {
            "raw": quantity.raw, "value": quantity.value, "unit": quantity.unit,
            "display": quantity.display,
        },
        "summary": summary(explanations),
        "results": [
            {**r.product, "score": r.score, "matched_concepts": r.matched_concepts,
             "matched_keywords": r.matched_keywords, "size_match": r.size_match}
            for r in results
        ],
    }


def meaningful_tokens(interpretation: dict) -> list[dict]:
    """Tokens that carry search meaning (not fillers or quantities)."""
    return [t for t in interpretation["tokens"] if t["role"] not in (FILLER, QUANTITY)]
