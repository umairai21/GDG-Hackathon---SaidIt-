import pytest

from pipeline.tokenizer import parse_size, tokenize


def words(q):
    return [t.norm for t in tokenize(q)[0]]


def test_splits_on_space_and_punctuation():
    assert words("Dahi, 1kg!") == ["dahi", "1kg"]
    assert words("el-7aleeb") == ["el", "7aleeb"]


@pytest.mark.parametrize("query,value,unit", [
    ("dahi 1kg", 1000, "g"),
    ("chawal 5 kilo", 5000, "g"),
    ("milk 1.5L", 1500, "ml"),
    ("milk 1,5 ltr", 1500, "ml"),
    ("laban 250ml", 250, "ml"),
    ("eggs 1 dozen", 12, "pcs"),
    ("adha kilo pyaz", 500, "g"),          # Urdu "half kilo"
    ("حليب ٢ لتر", 2000, "ml"),             # Arabic-Indic digit + Arabic unit
])
def test_quantities(query, value, unit):
    _, qty = tokenize(query)
    assert qty is not None
    assert (qty.value, qty.unit) == (value, unit)


def test_quantity_tokens_are_flagged_not_dropped():
    tokens, _ = tokenize("chawal 5 kilo")
    assert [t.is_quantity for t in tokens] == [False, True, True]


@pytest.mark.parametrize("query", ["3eish", "7up", "na3na3", "5ubz"])
def test_arabizi_digits_are_not_quantities(query):
    tokens, qty = tokenize(query)
    assert qty is None and not tokens[0].is_quantity


def test_number_word_without_unit_is_not_a_quantity():
    # "do" is Urdu for 2 but also a common word; only counts before a unit.
    _, qty = tokenize("do chai")
    assert qty is None


def test_arabic_diacritics_do_not_split_words():
    assert words("حَلِيب") == ["حليب"]


def test_parse_size_display():
    assert parse_size("1.5 L").display == "1.5 L"
    assert parse_size("500 g").display == "500 g"
    assert parse_size("30 pcs").value == 30
