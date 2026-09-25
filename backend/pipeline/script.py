"""Stage 2: detect which writing system each token is in."""
from __future__ import annotations

import re

_ARABIC = re.compile(r"[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]")
_LATIN = re.compile(r"[A-Za-zÀ-ɏ]")
_DIGIT = re.compile(r"[0-9]")

LATIN, ARABIC, DIGITS, MIXED = "latin", "arabic", "digits", "mixed"


def detect_script(text: str) -> str:
    """Return latin / arabic / digits / mixed.

    'mixed' covers Latin letters with digits inside (the Arabizi shape, e.g. "3eish")
    and any token mixing Arabic and Latin letters."""
    has_ar = bool(_ARABIC.search(text))
    has_lat = bool(_LATIN.search(text))
    has_dig = bool(_DIGIT.search(text))
    if has_ar and not has_lat and not has_dig:
        return ARABIC
    if has_lat and not has_ar and not has_dig:
        return LATIN
    if has_dig and not has_ar and not has_lat:
        return DIGITS
    return MIXED
