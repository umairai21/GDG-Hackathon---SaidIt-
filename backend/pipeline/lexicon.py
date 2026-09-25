"""Loads data/ (concepts, lexicons, catalog) and builds the lookup indexes the pipeline uses.

Every index is a plain dict so any lookup can be explained ("found 'dahi' in roman_urdu.json").
"""
from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from .normalize import (
    arabic_prefix_variants,
    arabic_skeleton,
    latin_skeleton,
    normalize_arabic,
    phonetic_key,
)
from .script import ARABIC, detect_script

DATA_DIR = Path(os.environ.get("SAIDIT_DATA_DIR", Path(__file__).resolve().parents[2] / "data"))
LANGUAGES = ["english", "roman_urdu", "arabizi", "arabic"]

# Words in product names that carry no search meaning.
_NAME_STOPWORDS = {"with", "and", "in", "of", "the", "for", "no", "al", "el"}


def lookup_key(form: str) -> str:
    """Canonical key for exact lookups: lowercase Latin, normalized Arabic, single spaces."""
    form = " ".join(form.split())
    return normalize_arabic(form) if detect_script(form.replace(" ", "")) == ARABIC else form.lower()


@dataclass
class LexEntry:
    """One surface form. If several lexicons list it, their concepts/languages are merged."""
    form: str
    concepts: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def ambiguous(self) -> bool:
        return len(self.concepts) > 1


@dataclass
class Resources:
    concepts: dict[str, dict]
    catalog: list[dict]
    language_labels: dict[str, str]
    exact: dict[str, LexEntry]                 # single-word key -> entry
    phrases: dict[str, LexEntry]               # "hari mirch" -> entry
    phrase_keys: dict[str, LexEntry]           # phonetic key of each word joined by space
    fillers: dict[str, list[str]]              # "ka" -> ["roman_urdu"]
    phonetic: dict[str, list[LexEntry]]        # Latin phonetic key -> entries
    latin_skel: dict[str, list[LexEntry]]      # Latin consonant skeleton -> entries
    arabic_skel: dict[str, list[LexEntry]]     # Arabic consonant skeleton -> entries
    latin_forms: list[str]                     # for fuzzy matching
    arabic_forms: list[str]
    concept_latin_forms: dict[str, list[str]]  # to report "closest known spelling"
    vocab_en: set[str]                         # words appearing in English product names
    vocab_ar: set[str]                         # normalized Arabic product-name words, article removed
    product_terms: dict[str, set[str]]         # product id -> searchable words (both scripts)


def _name_words(text: str) -> list[str]:
    return [w for w in re.findall(r"[^\W_]+", text.lower()) if w not in _NAME_STOPWORDS]


def _arabic_name_words(text: str) -> set[str]:
    out = set()
    for w in re.findall(r"[^\W_]+", text):
        w = normalize_arabic(w)
        out.update(v for v, _ in arabic_prefix_variants(w))
    return out


def _unique_concept_entries(entries: list[LexEntry]) -> bool:
    return len({tuple(e.concepts) for e in entries}) == 1


def load_resources(data_dir: Path | str = DATA_DIR) -> Resources:
    data_dir = Path(data_dir)
    concepts = json.loads((data_dir / "concepts.json").read_text(encoding="utf-8"))
    catalog = json.loads((data_dir / "catalog.json").read_text(encoding="utf-8"))

    exact: dict[str, LexEntry] = {}
    phrases: dict[str, LexEntry] = {}
    fillers: dict[str, list[str]] = defaultdict(list)
    labels: dict[str, str] = {"unknown": "unknown"}

    for lang in LANGUAGES:
        lex = json.loads((data_dir / "lexicons" / f"{lang}.json").read_text(encoding="utf-8"))
        labels[lang] = lex["label"]
        for f in lex.get("fillers", []):
            fillers[lookup_key(f)].append(lang)
        for e in lex["entries"]:
            entry_concepts = e.get("concepts") or [e["concept"]]
            for c in entry_concepts:
                if c not in concepts:
                    raise ValueError(f"{lang}.json: unknown concept '{c}' for {e['forms']}")
            for form in e["forms"]:
                key = lookup_key(form)
                table = phrases if " " in key else exact
                entry = table.setdefault(key, LexEntry(form=form))
                for c in entry_concepts:
                    if c not in entry.concepts:
                        entry.concepts.append(c)
                if lang not in entry.languages:
                    entry.languages.append(lang)
                if e.get("note") and e["note"] not in entry.notes:
                    entry.notes.append(e["note"])

    phonetic: dict[str, list[LexEntry]] = defaultdict(list)
    latin_skel: dict[str, list[LexEntry]] = defaultdict(list)
    arabic_skel: dict[str, list[LexEntry]] = defaultdict(list)
    concept_latin_forms: dict[str, list[str]] = defaultdict(list)
    latin_forms, arabic_forms = [], []

    for key, entry in exact.items():
        if detect_script(key) == ARABIC:
            arabic_forms.append(key)
            arabic_skel[arabic_skeleton(key)].append(entry)
        else:
            latin_forms.append(key)
            phonetic[phonetic_key(key)].append(entry)
            skel = latin_skeleton(key)
            if skel:
                latin_skel[skel].append(entry)
            for c in entry.concepts:
                concept_latin_forms[c].append(key)

    phrase_keys = {
        " ".join(phonetic_key(w) for w in key.split()): entry
        for key, entry in phrases.items() if detect_script(key.replace(" ", "")) != ARABIC
    }

    # Only keep phonetic/skeleton buckets that point to one meaning. A key shared by
    # different concepts (e.g. skeleton "lbn" = laban AND labna) is too risky to use.
    phonetic = {k: v for k, v in phonetic.items() if _unique_concept_entries(v)}
    latin_skel = {k: v for k, v in latin_skel.items() if _unique_concept_entries(v)}
    # Same minimum as the Latin skeleton: 2 consonants (e.g. كل) match far too many words.
    arabic_skel = {k: v for k, v in arabic_skel.items() if len(k) >= 3 and _unique_concept_entries(v)}

    vocab_en: set[str] = set()
    vocab_ar: set[str] = set()
    product_terms: dict[str, set[str]] = {}
    for p in catalog:
        en = set(_name_words(p["name_en"]))
        ar = _arabic_name_words(p["name_ar"])
        vocab_en |= {w for w in en if len(w) >= 2 and not w.isdigit()}
        vocab_ar |= {w for w in ar if len(w) >= 2}
        product_terms[p["id"]] = en | ar

    return Resources(
        concepts=concepts, catalog=catalog, language_labels=labels,
        exact=exact, phrases=phrases, phrase_keys=phrase_keys, fillers=dict(fillers),
        phonetic=phonetic, latin_skel=latin_skel, arabic_skel=arabic_skel,
        latin_forms=latin_forms, arabic_forms=arabic_forms,
        concept_latin_forms=dict(concept_latin_forms),
        vocab_en=vocab_en, vocab_ar=vocab_ar, product_terms=product_terms,
    )


@lru_cache(maxsize=1)
def default_resources() -> Resources:
    return load_resources(DATA_DIR)
