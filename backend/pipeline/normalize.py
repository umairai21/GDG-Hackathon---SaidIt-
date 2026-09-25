"""Stage 4: spelling-by-ear normalization.

Three independent tools, all deterministic and inspectable:
  * normalize_arabic / arabic_prefix_variants / arabic_skeleton : Arabic-script spelling variation
  * phonetic_key / latin_skeleton                               : Latin spellings of the same sound
  * arabizi_to_arabic                                           : Latin+digit chat Arabic -> Arabic script
"""
from __future__ import annotations

import itertools
import re

# ---------------------------------------------------------------- Arabic script

_ARABIC_MARKS = re.compile(r"[ً-ْٰـ]")  # harakat, dagger alef, tatweel


def normalize_arabic(s: str) -> str:
    """Fold spelling differences that Arabic writers treat as the same word."""
    s = _ARABIC_MARKS.sub("", s)
    s = re.sub("[أإآٱ]", "ا", s)  # hamza-on-alef is routinely dropped when typing
    s = s.replace("ة", "ه")        # ta marbuta and ha are interchangeable at word end in casual typing
    s = s.replace("ى", "ي")        # alef maqsura vs ya: same reason
    s = s.replace("ؤ", "و").replace("ئ", "ي")
    return s


# Order matters: try the longest prefix first. Each is a clitic, not part of the word.
_AR_PREFIXES = [
    ("وال", 'and the'), ("بال", 'with the'), ("فال", 'so the'), ("كال", 'like the'),
    ("لل", 'for the'), ("ال", 'the'), ("و", 'and'),
]


def arabic_prefix_variants(s: str) -> list[tuple[str, str | None]]:
    """[(word, removed-prefix-meaning)], original first. Only strips if >=2 letters remain."""
    out: list[tuple[str, str | None]] = [(s, None)]
    for prefix, meaning in _AR_PREFIXES:
        if s.startswith(prefix) and len(s) - len(prefix) >= 2:
            out.append((s[len(prefix):], f'removed "{prefix}" ({meaning})'))
    return out


def arabic_skeleton(s: str) -> str:
    """Drop long-vowel letters and hamza: people spell vowels inconsistently, consonants rarely."""
    return re.sub("[اويىء]", "", normalize_arabic(s))


# ---------------------------------------------------------------- Latin phonetic key

# Arabizi digits folded to the Latin letters people use when they *don't* use digits.
# Why 3 and 2 -> "": ع and ء are usually just dropped in Latin spelling ("asal" for "3asal").
_DIGIT_SOUNDS = {"2": "", "3": "", "5": "kh", "6": "t", "7": "h", "8": "gh", "9": "k"}

_KEY_RULES: list[tuple[str, str]] = [
    (r"(.)\1{2,}", r"\1\1"),                  # emphatic/typo repeats first: "dooodh" -> "doodh"
    (r"ph", "f"), (r"ck", "k"), (r"q", "k"), (r"v", "w"),
    (r"th", "t"), (r"dh", "d"),               # aspiration is inconsistently written ("dhal"/"dal")
    (r"ee|ii", "i"), (r"oo|ou|uu", "u"),      # long vowels spelled English-style ("dahee", "doodh")
    (r"(?:ay|ey|ei)(?![aeiou])", "ai"),       # diphthong spellings: "bayd"/"beid"/"baid"
    (r"y$", "i"),                             # final -y and -i: "zabady"/"zabadi"
    (r"(.)\1+", r"\1"),                       # doubled letters: "chawwal", "makkhan", "aa"
]


def phonetic_key(s: str) -> str:
    """Collapse Latin spelling-by-ear variants to one key. dahi/dahee/dahii -> dahi."""
    s = "".join(_DIGIT_SOUNDS.get(c, c) for c in s.lower())
    for pattern, repl in _KEY_RULES:
        s = re.sub(pattern, repl, s)
    return s


def latin_skeleton(s: str) -> str | None:
    """Consonant skeleton of the phonetic key (first letter kept). laban/leban/labn -> lbn.
    Returns None when too short to be distinctive."""
    key = phonetic_key(s)
    if not key:
        return None
    skel = key[0] + re.sub(r"[aeiou]", "", key[1:])
    skel = re.sub(r"(.)\1+", r"\1", skel)
    return skel if len(skel) >= 3 else None


# ---------------------------------------------------------------- Arabizi -> Arabic

# Primary digit map (first option) follows the common convention. Usage varies by region:
# in the Gulf 9 is often ص rather than ق, and 8 can be ق rather than غ, so both are tried.
ARABIZI_DIGITS: dict[str, list[str]] = {
    "2": ["ء"], "3": ["ع"], "5": ["خ"], "6": ["ط"], "7": ["ح"], "8": ["غ", "ق"], "9": ["ق", "ص"],
}

_DIGRAPHS: dict[str, list[str]] = {
    "sh": ["ش"], "kh": ["خ"], "gh": ["غ"], "th": ["ث", "ذ"], "dh": ["ذ", "ض"], "ch": ["ش", "ك"],
    "aa": ["ا"], "ee": ["ي"], "ii": ["ي"], "ei": ["ي"], "ai": ["ي"], "ay": ["ي"], "ey": ["ي"],
    "oo": ["و"], "ou": ["و"], "uu": ["و"], "aw": ["و"], "ow": ["و"],
}

# Letters with more than one Arabic reading list the most common first.
# h: ح and ه are both written "h"; g: ج in MSA, ق in Gulf/Egyptian speech ("gahwa" = قهوة).
_LETTERS: dict[str, list[str]] = {
    "b": ["ب"], "p": ["ب"], "t": ["ت", "ط"], "j": ["ج"], "g": ["ج", "ق", "غ"], "d": ["د", "ض"],
    "r": ["ر"], "z": ["ز"], "s": ["س", "ص"], "f": ["ف"], "v": ["ف"], "q": ["ق"], "k": ["ك"],
    "c": ["ك"], "l": ["ل"], "m": ["م"], "n": ["ن"], "h": ["ه", "ح"], "w": ["و"], "y": ["ي"],
    "x": ["كس"],
}

_VOWELS = set("aeiou")
MAX_CANDIDATES = 256


def arabizi_to_arabic(token: str) -> list[str]:
    """All plausible Arabic spellings of a Latin/Arabizi token, most likely first.

    Short vowels are dropped (Arabic doesn't write them), long vowels become ا/و/ي,
    a word-initial vowel becomes ا, and a final -a/-ah/-eh can be ة, ا or nothing."""
    s = token.lower()
    slots: list[list[str]] = []
    i = 0
    while i < len(s):
        pair, ch = s[i:i + 2], s[i]
        is_last_char = i == len(s) - 1
        if pair in ("ah", "eh") and i + 2 == len(s):  # "labneh" -> لبنة
            slots.append(["ة", ""])
            i += 2
            continue
        if pair in _DIGRAPHS:
            slots.append(_DIGRAPHS[pair])
            i += 2
            continue
        if ch in ARABIZI_DIGITS:
            slots.append(ARABIZI_DIGITS[ch])
        elif ch in _VOWELS:
            if i == 0:
                slots.append(["ا"])
            elif is_last_char and ch == "a":
                slots.append(["ة", "ا", ""])
            elif is_last_char and ch in "iy":
                slots.append(["ي"])
            elif is_last_char and ch == "e":  # Levantine final -e is ة: "lebne" = لبنة
                slots.append(["ة", ""])
            elif is_last_char and ch in "ou":
                slots.append(["و"])
            else:
                slots.append([""])  # short vowel: not written in Arabic
        elif ch in _LETTERS:
            if s[i - 1:i] == ch:  # doubled consonant = shadda, written once
                i += 1
                continue
            slots.append(_LETTERS[ch])
        # anything else (apostrophes etc.) is ignored
        i += 1

    out: list[str] = []
    seen: set[str] = set()
    for combo in itertools.islice(itertools.product(*slots), MAX_CANDIDATES):
        cand = normalize_arabic("".join(combo))
        if cand and cand not in seen:
            seen.add(cand)
            out.append(cand)
    return out
