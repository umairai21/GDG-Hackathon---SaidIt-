"""Stage 1: split a raw query into tokens and pull quantities/units into a separate field."""
from __future__ import annotations

import re
from dataclasses import dataclass

# Arabic-Indic (٠-٩) and Persian/Urdu (۰-۹) digits -> ASCII, so "١ كيلو" parses like "1 kilo".
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "0123456789" * 2)

# Arabic diacritics (harakat) and tatweel are not word characters to the regex below,
# so they would split a word in half. Strip them before splitting.
_ARABIC_MARKS = re.compile(r"[ً-ْٰـ]")

# A decimal quantity like "1.5l" or a run of letters/digits. Everything else is a separator.
_TOKEN_RE = re.compile(r"\d+[.,]\d+[^\W\d_]*|[^\W_]+")

# unit spelling -> (base unit, multiplier). Base units: g, ml, pcs.
UNITS: dict[str, tuple[str, float]] = {
    **{u: ("g", 1) for u in ["g", "gm", "gms", "gr", "grm", "gram", "grams", "غرام", "جرام", "جم", "غ"]},
    **{u: ("g", 1000) for u in ["kg", "kgs", "kilo", "kilos", "kilogram", "kilograms", "كيلو", "كغ", "كجم"]},
    **{u: ("ml", 1) for u in ["ml", "mls", "مل"]},
    **{u: ("ml", 1000) for u in ["l", "lt", "ltr", "ltrs", "litre", "litres", "liter", "liters", "لتر"]},
    **{u: ("pcs", 1) for u in ["pc", "pcs", "piece", "pieces", "حبة", "habba"]},
    **{u: ("pcs", 12) for u in ["dozen", "darjan", "درزن"]},  # "darjan" = Urdu for dozen
}

# Spoken numbers that only count as quantities when followed by a unit ("adha kilo" = 500 g).
NUMBER_WORDS: dict[str, float] = {
    "ek": 1, "do": 2, "teen": 3, "char": 4, "chaar": 4, "panch": 5, "paanch": 5,
    "adha": 0.5, "aadha": 0.5,  # Urdu/Hindi "half"
    "nus": 0.5, "nuss": 0.5, "نص": 0.5,  # Gulf Arabic "half"
}

_NUM_UNIT_RE = re.compile(r"^(\d+(?:[.,]\d+)?)([^\W\d_]+)?$")


@dataclass
class Token:
    text: str      # as the user typed it (after diacritic stripping)
    norm: str      # lowercased, ASCII digits
    index: int
    is_quantity: bool = False


@dataclass
class Quantity:
    raw: str             # e.g. "5 kilo"
    value: float | None  # in base units (g / ml / pcs); None if only a unit was given
    unit: str | None     # "g" | "ml" | "pcs" | None (bare number)

    @property
    def display(self) -> str:
        if self.value is None:
            return self.unit or ""
        if self.unit == "g" and self.value >= 1000:
            return f"{self.value / 1000:g} kg"
        if self.unit == "ml" and self.value >= 1000:
            return f"{self.value / 1000:g} L"
        return f"{self.value:g} {self.unit or ''}".strip()


def parse_size(text: str) -> Quantity | None:
    """Parse a catalog size string like '1.5 L' or '30 pcs'. Reuses the query quantity rules."""
    _, qty = tokenize(text)
    return qty


def _number(s: str) -> float:
    return float(s.replace(",", "."))


def tokenize(query: str) -> tuple[list[Token], Quantity | None]:
    """Split a query into tokens. Quantity tokens stay in the list (flagged) so the UI can show them,
    and the first quantity found is also returned as a structured field."""
    cleaned = _ARABIC_MARKS.sub("", query.translate(_DIGITS))
    raw_parts = _TOKEN_RE.findall(cleaned)
    tokens = [Token(text=p, norm=p.lower(), index=i) for i, p in enumerate(raw_parts)]

    quantity: Quantity | None = None
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        nxt = tokens[i + 1] if i + 1 < len(tokens) else None
        found: Quantity | None = None
        span = 1

        m = _NUM_UNIT_RE.match(tok.norm)
        if m and (m.group(2) is None or m.group(2) in UNITS):
            value, unit_word = _number(m.group(1)), m.group(2)
            if unit_word is None and nxt and nxt.norm in UNITS:  # "5 kilo"
                unit_word, span = nxt.norm, 2
            if unit_word:
                base, mult = UNITS[unit_word]
                found = Quantity(" ".join(t.text for t in tokens[i:i + span]), value * mult, base)
            else:  # bare number, e.g. "eggs 30"
                found = Quantity(tok.text, value, None)
        elif tok.norm in NUMBER_WORDS and nxt and nxt.norm in UNITS:  # "adha kilo"
            base, mult = UNITS[nxt.norm]
            found, span = Quantity(f"{tok.text} {nxt.text}", NUMBER_WORDS[tok.norm] * mult, base), 2
        elif tok.norm in UNITS:  # a unit with no number: "kilo chawal"
            base, _ = UNITS[tok.norm]
            found = Quantity(tok.text, None, base)

        if found:
            for t in tokens[i:i + span]:
                t.is_quantity = True
            if quantity is None:
                quantity = found
        i += span

    return tokens, quantity
