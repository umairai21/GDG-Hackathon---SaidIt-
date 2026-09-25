from baselines import fuzzy_search, keyword_search
from pipeline.lexicon import default_resources

catalog = default_resources().catalog


def test_keyword_requires_every_word():
    assert all("basmati" in p["name_en"].lower() for p in keyword_search("basmati rice", catalog))
    assert keyword_search("dahi", catalog) == []  # the problem we're solving


def test_keyword_matches_arabic_names():
    assert keyword_search("حليب", catalog)


def test_fuzzy_returns_closest_even_when_wrong():
    # A misspelling a customer might type; fuzzy search confidently shows something else.
    top = fuzzy_search("onoin", catalog)[0]
    assert "onion" not in top["concepts"]
