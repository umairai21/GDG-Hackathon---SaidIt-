"""Stages 5-6: map each token to a catalog concept and say how sure we are.

Confidence levels:
  sure     exact hit in a lexicon / catalog word list. Only lossless clean-up is allowed before the
           lookup: lowercasing, Arabic orthography folding (أ->ا, ة->ه), removing the article ال.
  guessed  any step that could be wrong: phonetic key, consonant skeleton, Arabizi transliteration,
           plural stripping, fuzzy match, or a form that has more than one meaning. Carries a score.
  unknown  nothing matched. The token is kept as typed and never silently replaced.

The cascade stops at the first step that matches, and records every step it tried.
"""
from __future__ import annotations

import itertools
import re
from dataclasses import dataclass, field

from rapidfuzz import fuzz, process

from .lexicon import LexEntry, Resources, lookup_key
from .normalize import (
    arabic_prefix_variants,
    arabic_skeleton,
    arabizi_to_arabic,
    latin_skeleton,
    normalize_arabic,
    phonetic_key,
)
from .script import ARABIC, DIGITS
from .tokenizer import Token

SURE, GUESSED, UNKNOWN = "sure", "guessed", "unknown"
CONCEPT, KEYWORD, FILLER, QUANTITY = "concept", "keyword", "filler", "quantity"

FUZZY_MIN_LEN = 4      # fuzzy matching on 3-letter words produces nonsense
FUZZY_CUTOFF = 80      # rapidfuzz ratio (0-100)
_URDU_SUFFIX = re.compile(r"^([a-z0-9]{3,}?)-?(wala|wali|wale|walay)$")


@dataclass
class Match:
    role: str                                    # concept | keyword | filler | quantity | unknown
    confidence: str                              # sure | guessed | unknown
    normalized: str                              # the form we actually looked up
    method: str = "none"                         # machine-readable rule id (see METHOD_TEXT)
    concepts: list[str] = field(default_factory=list)
    keyword: str | None = None                   # catalog word, for role=keyword
    matched_form: str | None = None              # lexicon/catalog form that matched
    score: int | None = None                     # 0-100 similarity to the nearest known spelling
    similar_to: str | None = None                # that nearest known spelling
    languages: list[str] = field(default_factory=list)  # lexicons the matched form came from
    notes: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    phrase: str | None = None                    # set when matched as part of a multi-word form


METHOD_TEXT = {
    "filler": "a small connecting word (like 'of' or 'ka'), ignored for search",
    "quantity": "a quantity/unit, used to prefer matching pack sizes",
    "lexicon_exact": "exact match in our word list",
    "lexicon_ambiguous": "exact match, but this word has more than one meaning",
    "phrase": "matched a multi-word term",
    "phrase_phonetic": "matched a multi-word term after spelling normalization",
    "catalog_word": "appears in product names in the catalog",
    "phonetic_key": "same sound, different spelling (vowels / doubled letters / digits folded)",
    "consonant_skeleton": "same consonants, different vowels",
    "arabizi_transliteration": "rewritten in Arabic script and found in the Arabic word list",
    "arabic_skeleton": "same Arabic consonants, different vowel letters",
    "english_plural": "plural of a known word",
    "urdu_suffix": 'known word with the Urdu/Hindi ending "-wala/-wali" removed',
    "fuzzy": "close spelling to a known word (fuzzy match)",
    "store_approved": "learned from customer clicks and approved by the store",
    "none": "no rule matched; kept as typed",
}


# ---------------------------------------------------------------- helpers

def _from_entry(entry: LexEntry, normalized: str, method: str, steps: list[str],
                confident: bool) -> Match:
    confidence = SURE if confident and not entry.ambiguous else GUESSED
    if confident and entry.ambiguous:
        method = "lexicon_ambiguous"
    return Match(
        role=CONCEPT, confidence=confidence, normalized=normalized, method=method,
        concepts=list(entry.concepts), matched_form=entry.form, languages=list(entry.languages),
        notes=list(entry.notes), steps=steps,
    )


def _nearest_score(token: str, match: Match, res: Resources, arabic: bool) -> None:
    """Fill score/similar_to: how close the typed token is to a spelling we know for this concept."""
    if arabic or not match.concepts:
        target = match.matched_form or match.keyword or ""
        match.score, match.similar_to = round(fuzz.ratio(token, lookup_key(target))), target
        return
    candidates = [f for c in match.concepts for f in res.concept_latin_forms.get(c, [])]
    if not candidates:
        return
    best, score, _ = process.extractOne(token, candidates, scorer=fuzz.ratio)
    match.score, match.similar_to = round(score), best


def _pick_unique(entries: list[LexEntry]) -> LexEntry:
    # Buckets were filtered at load time to hold a single meaning; take the first spelling.
    return entries[0]


# ---------------------------------------------------------------- Latin / Arabizi tokens

def _map_latin(t: str, res: Resources) -> Match:
    steps: list[str] = []

    if t in res.fillers:
        return Match(FILLER, SURE, t, "filler", languages=res.fillers[t], steps=["filler word"])

    if t in res.exact:
        return _from_entry(res.exact[t], t, "lexicon_exact", [f'exact lookup "{t}"'], True)
    steps.append(f'no exact entry for "{t}"')

    if t in res.vocab_en:
        return Match(KEYWORD, SURE, t, "catalog_word", keyword=t, languages=["english"],
                     steps=steps + [f'"{t}" appears in product names'])

    # Urdu/Hindi "-wala" ("the X one"): doodhwala -> doodh. Only kept if the stem means something.
    suffix = _URDU_SUFFIX.match(t)
    if suffix:
        inner = _map_latin(suffix.group(1), res)
        if inner.role in (CONCEPT, KEYWORD):
            inner.steps = steps + [f'removed Urdu/Hindi ending "-{suffix.group(2)}"'] + inner.steps
            inner.confidence, inner.method = GUESSED, "urdu_suffix"
            inner.score = inner.score or round(fuzz.ratio(t, suffix.group(1)))
            inner.similar_to = inner.similar_to or suffix.group(1)
            return inner

    key = phonetic_key(t)
    steps.append(f'phonetic key "{t}" -> "{key}"')
    if key in res.phonetic:
        m = _from_entry(_pick_unique(res.phonetic[key]), key, "phonetic_key", steps, False)
        _nearest_score(t, m, res, arabic=False)
        return m

    skel = latin_skeleton(t)
    if skel:
        steps.append(f'consonant skeleton -> "{skel}"')
        if skel in res.latin_skel:
            m = _from_entry(_pick_unique(res.latin_skel[skel]), skel, "consonant_skeleton", steps, False)
            _nearest_score(t, m, res, arabic=False)
            return m

    candidates = arabizi_to_arabic(t)
    if candidates:
        steps.append(f'Arabizi -> Arabic: {", ".join(candidates[:3])}{"..." if len(candidates) > 3 else ""}')
    for cand in candidates:
        for variant, why in arabic_prefix_variants(cand):
            if variant in res.exact:
                m = _from_entry(res.exact[variant], variant, "arabizi_transliteration",
                                steps + ([why] if why else []) + [f'found "{variant}"'], False)
                _nearest_score(t, m, res, arabic=False)
                return m
    for cand in candidates:
        skel_ar = arabic_skeleton(cand)
        if skel_ar in res.arabic_skel:
            m = _from_entry(_pick_unique(res.arabic_skel[skel_ar]), cand, "arabic_skeleton",
                            steps + [f'Arabic consonants "{skel_ar}"'], False)
            _nearest_score(t, m, res, arabic=False)
            return m

    # English plural: "tomatos" -> "tomato", "lentilz" won't be caught here but fuzzy may.
    for suffix in ("es", "s"):
        stem = t[: -len(suffix)]
        if t.endswith(suffix) and len(stem) >= 3:
            if stem in res.exact:
                m = _from_entry(res.exact[stem], stem, "english_plural",
                                steps + [f'plural "{t}" -> "{stem}"'], False)
                m.score, m.similar_to = round(fuzz.ratio(t, stem)), stem
                return m
            if stem in res.vocab_en:
                return Match(KEYWORD, GUESSED, stem, "english_plural", keyword=stem,
                             languages=["english"], score=round(fuzz.ratio(t, stem)),
                             similar_to=stem, steps=steps + [f'plural "{t}" -> "{stem}"'])

    if len(t) >= FUZZY_MIN_LEN:
        choices = res.latin_forms + sorted(res.vocab_en)
        hit = process.extractOne(t, choices, scorer=fuzz.ratio, score_cutoff=FUZZY_CUTOFF)
        if hit:
            form, score, idx = hit
            steps.append(f'fuzzy match "{form}" ({round(score)}%)')
            if idx < len(res.latin_forms):
                m = _from_entry(res.exact[form], form, "fuzzy", steps, False)
            else:
                m = Match(KEYWORD, GUESSED, form, "fuzzy", keyword=form, languages=["english"], steps=steps)
            m.score, m.similar_to = round(score), form
            return m
        steps.append(f"no spelling within {FUZZY_CUTOFF}% similarity")

    return Match("unknown", UNKNOWN, t, "none", steps=steps)


# ---------------------------------------------------------------- Arabic-script tokens

def _map_arabic(raw: str, res: Resources) -> Match:
    t = normalize_arabic(raw)
    steps = [f'normalized spelling "{raw}" -> "{t}"'] if t != raw else []

    if t in res.fillers:
        return Match(FILLER, SURE, t, "filler", languages=res.fillers[t], steps=steps + ["filler word"])

    variants = arabic_prefix_variants(t)
    for variant, why in variants:
        if variant in res.exact:
            return _from_entry(res.exact[variant], variant, "lexicon_exact",
                               steps + ([why] if why else []) + [f'exact lookup "{variant}"'], True)
    for variant, why in variants:
        if variant in res.vocab_ar:
            return Match(KEYWORD, SURE, variant, "catalog_word", keyword=variant, languages=["arabic"],
                         steps=steps + ([why] if why else []) + [f'"{variant}" appears in product names'])
    steps.append("no exact entry")

    for variant, why in variants:
        skel = arabic_skeleton(variant)
        if skel in res.arabic_skel:
            m = _from_entry(_pick_unique(res.arabic_skel[skel]), variant, "arabic_skeleton",
                            steps + ([why] if why else []) + [f'consonants "{skel}"'], False)
            _nearest_score(variant, m, res, arabic=True)
            return m

    choices = res.arabic_forms + sorted(res.vocab_ar)
    for variant, why in variants:
        if len(variant) < 3:
            continue
        hit = process.extractOne(variant, choices, scorer=fuzz.ratio, score_cutoff=FUZZY_CUTOFF)
        if hit:
            form, score, idx = hit
            s = steps + ([why] if why else []) + [f'fuzzy match "{form}" ({round(score)}%)']
            if idx < len(res.arabic_forms):
                m = _from_entry(res.exact[form], form, "fuzzy", s, False)
            else:
                m = Match(KEYWORD, GUESSED, form, "fuzzy", keyword=form, languages=["arabic"], steps=s)
            m.score, m.similar_to = round(score), form
            return m

    return Match("unknown", UNKNOWN, t, "none", steps=steps + ["no close Arabic spelling"])


# ---------------------------------------------------------------- public API

def map_token(token: Token, script: str, res: Resources,
              approved: dict[str, str] | None = None) -> Match:
    """approved: token -> concept mappings the store approved on the dashboard. They are checked
    first (so the store can settle an ambiguous word), and nothing else can add to this dict."""
    if token.is_quantity:
        return Match(QUANTITY, SURE, token.norm, "quantity", steps=["parsed as quantity"])
    key = lookup_key(token.norm)
    if approved and key in approved:
        concept = approved[key]
        known = res.exact.get(key)
        return Match(CONCEPT, SURE, key, "store_approved", concepts=[concept],
                     languages=list(known.languages) if known else [],
                     steps=[f'store approved "{key}" -> {concept} on the dashboard'])
    if script == ARABIC:
        return _map_arabic(token.text, res)
    if script == DIGITS:  # a bare number that wasn't a quantity (shouldn't normally happen)
        return Match("unknown", UNKNOWN, token.norm, "none", steps=["number without unit"])
    return _map_latin(token.norm, res)


MAX_PHRASE_WORDS = 3  # "zaitoon ka tel" (olive oil, lit. "oil of olive")


def _phrase_entry(window: list[Token], res: Resources) -> tuple[LexEntry | None, str]:
    # Arabic: also try each word without its article ("الفلفل الأخضر").
    variant_lists = [[v for v, _ in arabic_prefix_variants(normalize_arabic(t.norm))] for t in window]
    for combo in itertools.product(*variant_lists):
        entry = res.phrases.get(" ".join(combo))
        if entry:
            return entry, "phrase"
    entry = res.phrase_keys.get(" ".join(phonetic_key(t.norm) for t in window))
    return entry, "phrase_phonetic"


def find_phrases(tokens: list[Token], res: Resources) -> dict[int, Match]:
    """Match runs of 2-3 adjacent words against multi-word lexicon forms ("hari mirch",
    "زيت زيتون"), longest first. Returns {token index: Match} for every word in a matched run."""
    found: dict[int, Match] = {}
    for n in range(MAX_PHRASE_WORDS, 1, -1):
        for start in range(len(tokens) - n + 1):
            window = tokens[start:start + n]
            if any(t.is_quantity or t.index in found for t in window):
                continue
            entry, method = _phrase_entry(window, res)
            if entry is None:
                continue
            phrase_text = " ".join(t.text for t in window)
            for tok in window:
                m = _from_entry(entry, tok.norm, method, [f'part of "{phrase_text}"'], method == "phrase")
                m.phrase = phrase_text
                if m.confidence == GUESSED and not entry.ambiguous:
                    m.score, m.similar_to = round(fuzz.ratio(phrase_text.lower(), entry.form)), entry.form
                found[tok.index] = m
    return found
