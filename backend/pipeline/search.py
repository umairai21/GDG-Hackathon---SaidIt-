"""Stage 7: rank catalog products by matched concepts, leftover keywords and quantity."""
from __future__ import annotations

from dataclasses import dataclass, field

from .concepts import CONCEPT, GUESSED, KEYWORD, Match
from .lexicon import Resources, lookup_key
from .tokenizer import Quantity, parse_size

# Weights are deliberately simple so the ranking can be explained in one sentence:
# "a product earns 1 point per concept it matches, less if we guessed, plus small bonuses".
W_SURE = 1.0
W_GUESSED = 0.8
W_KEYWORD = 0.5      # a catalog word (brand, "basmati") narrows results but isn't a product type
BONUS_NAME = 0.2     # the typed word literally appears in the product name ("orange" in Orange Juice)
BONUS_SIZE = 0.3     # pack size equals the requested quantity


@dataclass
class Result:
    product: dict
    score: float
    matched_concepts: list[str] = field(default_factory=list)
    matched_keywords: list[str] = field(default_factory=list)
    size_match: bool = False


def query_terms(matches: list[Match]) -> tuple[dict[str, float], dict[str, float], set[str]]:
    """Turn token matches into (concept weights, keyword weights, words to look for in names).
    An ambiguous token splits its weight across its meanings instead of picking one."""
    concept_w: dict[str, float] = {}
    keyword_w: dict[str, float] = {}
    name_words: set[str] = set()
    for m in matches:
        base = W_GUESSED if m.confidence == GUESSED else W_SURE
        if m.role == CONCEPT and m.concepts:
            share = base / len(m.concepts)
            for c in m.concepts:
                concept_w[c] = max(concept_w.get(c, 0.0), share)
            name_words.add(lookup_key(m.normalized))
        elif m.role == KEYWORD and m.keyword:
            keyword_w[m.keyword] = max(keyword_w.get(m.keyword, 0.0), base * W_KEYWORD)
    return concept_w, keyword_w, name_words


def _size_equal(product: dict, quantity: Quantity | None) -> bool:
    if not quantity or quantity.value is None or quantity.unit is None:
        return False
    size = parse_size(product["size"])
    return bool(size and size.unit == quantity.unit and abs((size.value or 0) - quantity.value) < 1e-6)


def search(matches: list[Match], quantity: Quantity | None, res: Resources, top_k: int = 10) -> list[Result]:
    concept_w, keyword_w, name_words = query_terms(matches)
    results: list[Result] = []
    for p in res.catalog:
        terms = res.product_terms[p["id"]]
        hit_concepts = [c for c in concept_w if c in p["concepts"]]
        hit_keywords = [k for k in keyword_w if k in terms]
        if not hit_concepts and not hit_keywords:
            continue  # never return a product that matches nothing the customer typed
        score = sum(concept_w[c] for c in hit_concepts) + sum(keyword_w[k] for k in hit_keywords)
        score += BONUS_NAME * len(name_words & terms)
        size_ok = _size_equal(p, quantity)
        if size_ok:
            score += BONUS_SIZE
        results.append(Result(p, round(score, 3), hit_concepts, hit_keywords, size_ok))
    results.sort(key=lambda r: (-r.score, r.product["id"]))
    return _interleave_ties(results)[:top_k]


def _interleave_ties(results: list[Result]) -> list[Result]:
    """Within a block of equal scores, alternate between concepts. Why: for an ambiguous word
    like "3eish" (rice or bread) the top 3 should show both meanings, not 3 rice bags."""
    out: list[Result] = []
    i = 0
    while i < len(results):
        j = i
        while j < len(results) and results[j].score == results[i].score:
            j += 1
        groups: dict[str, list[Result]] = {}
        for r in results[i:j]:
            groups.setdefault(r.matched_concepts[0] if r.matched_concepts else "", []).append(r)
        queues = list(groups.values())
        while any(queues):
            for q in queues:
                if q:
                    out.append(q.pop(0))
        i = j
    return out
