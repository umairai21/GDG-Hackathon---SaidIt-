import pytest

from pipeline.normalize import (
    arabic_prefix_variants,
    arabic_skeleton,
    arabizi_to_arabic,
    latin_skeleton,
    normalize_arabic,
    phonetic_key,
)


def test_normalize_arabic_folds_spelling_variants():
    assert normalize_arabic("أرز") == normalize_arabic("ارز")
    assert normalize_arabic("لبنة") == normalize_arabic("لبنه")
    assert normalize_arabic("حَلِيب") == "حليب"


def test_arabic_prefix_variants():
    variants = [v for v, _ in arabic_prefix_variants("والحليب")]
    assert "حليب" in variants
    # never strip down to a single letter
    assert [v for v, _ in arabic_prefix_variants("ول")] == ["ول"]


@pytest.mark.parametrize("variants", [
    ["dahi", "dahee", "dahii"],
    ["doodh", "dudh", "dooodh"],
    ["chawal", "chawwal", "chaawal"],
    ["haleeb", "7aleeb", "7alib", "halib"],     # 7 -> h
    ["bayd", "baid", "beid"],                   # diphthong spellings
    ["zabadi", "zabady"],                       # final y/i
    ["qahwa", "kahwa"],                         # q/k
])
def test_phonetic_key_collapses_by_ear_spellings(variants):
    assert len({phonetic_key(v) for v in variants}) == 1


def test_phonetic_key_keeps_different_words_apart():
    assert phonetic_key("dahi") != phonetic_key("doodh")


def test_latin_skeleton():
    assert latin_skeleton("leban") == latin_skeleton("laban") == latin_skeleton("labn") == "lbn"
    assert latin_skeleton("dahi") is None  # too short to be distinctive


def test_arabic_skeleton_ignores_long_vowels():
    assert arabic_skeleton("حليب") == arabic_skeleton("حلب")


@pytest.mark.parametrize("latin,arabic", [
    ("3eish", "عيش"),
    ("khubz", "خبز"),
    ("7aleeb", "حليب"),
    ("labneh", "لبنه"),     # ة normalized to ه
    ("zabda", "زبده"),
    ("ba9al", "بصل"),       # Gulf convention: 9 = ص
    ("gahwa", "قهوه"),      # Gulf g = ق
])
def test_arabizi_to_arabic_candidates(latin, arabic):
    assert arabic in arabizi_to_arabic(latin)


def test_arabizi_primary_candidate_uses_standard_digit_map():
    assert arabizi_to_arabic("3asal")[0] == "عسل"
