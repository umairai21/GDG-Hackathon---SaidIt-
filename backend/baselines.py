"""The two baselines we compare against. Both search the same catalog as our pipeline.

1. keyword_search  - what a basic store search does: every word of the query must appear
                     (as a substring) in the product's English name, Arabic name or category.
2. fuzzy_search    - what a "smarter" typical app does: rapidfuzz similarity between the whole
                     query and each product name, returning the closest products. This never
                     says "I'm not sure"; the closest-but-wrong product is shown as if it were right.
"""
from __future__ import annotations

from rapidfuzz import fuzz, process

FUZZY_CUTOFF = 60  # typical default; below this even a fuzzy search shows "no results"


def keyword_search(query: str, catalog: list[dict], top_k: int = 10) -> list[dict]:
    words = query.lower().split()
    if not words:
        return []
    hits = []
    for p in catalog:
        text = f"{p['name_en']} {p['name_ar']} {p['category']}".lower()
        if all(w in text for w in words):
            hits.append(p)
    hits.sort(key=lambda p: (len(p["name_en"]), p["id"]))  # shorter name = closer match
    return hits[:top_k]


def fuzzy_search(query: str, catalog: list[dict], top_k: int = 10) -> list[dict]:
    q = query.lower().strip()
    if not q:
        return []
    # Each product is scored on whichever of its names (English / Arabic) matches best.
    names = {i: p["name_en"].lower() for i, p in enumerate(catalog)}
    names_ar = {i: p["name_ar"] for i, p in enumerate(catalog)}
    best: dict[int, float] = {}
    for choices in (names, names_ar):
        for _, score, i in process.extract(q, choices, scorer=fuzz.WRatio, limit=None,
                                           score_cutoff=FUZZY_CUTOFF):
            best[i] = max(best.get(i, 0), score)
    ranked = sorted(best, key=lambda i: (-best[i], catalog[i]["id"]))
    return [catalog[i] for i in ranked[:top_k]]
