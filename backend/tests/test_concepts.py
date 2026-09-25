import pytest

from pipeline.concepts import find_phrases, map_token
from pipeline.lexicon import default_resources
from pipeline.script import detect_script
from pipeline.tokenizer import tokenize

res = default_resources()


def m(word):
    tok = tokenize(word)[0][0]
    return map_token(tok, detect_script(tok.text), res)


def test_exact_hit_is_sure():
    r = m("dahi")
    assert (r.confidence, r.concepts, r.method) == ("sure", ["yogurt"], "lexicon_exact")


def test_arabic_article_removal_is_still_sure():
    r = m("الحليب")
    assert r.confidence == "sure" and r.concepts == ["milk"]


@pytest.mark.parametrize("word,concept,method", [
    ("dahee", "yogurt", "phonetic_key"),
    ("chawwal", "rice", "phonetic_key"),
    ("piyaz", "onion", "consonant_skeleton"),
    ("leban", "laban", "arabizi_transliteration"),
    ("ba9al", "onion", "arabizi_transliteration"),
    ("doodhwala", "milk", "urdu_suffix"),
    ("yougurt", "yogurt", "consonant_skeleton"),
    ("lebne", "labneh", "arabizi_transliteration"),   # final -e = ة
])
def test_normalized_matches_are_guessed_with_score(word, concept, method):
    r = m(word)
    assert r.confidence == "guessed"
    assert r.concepts == [concept]
    assert r.method == method
    assert r.score is not None and 0 < r.score <= 100


def test_two_consonant_arabic_skeleton_is_not_used():
    # "kelay" -> كلي -> skeleton كل would match كولا (cola). Too short to trust.
    assert "soft_drink" not in m("kelay").concepts


def test_ambiguous_word_is_guessed_with_all_meanings():
    r = m("3eish")
    assert r.confidence == "guessed" and set(r.concepts) == {"rice", "bread"}


def test_unknown_is_kept_as_typed():
    r = m("xyzzy")
    assert r.confidence == "unknown"
    assert r.normalized == "xyzzy" and r.concepts == [] and r.keyword is None


def test_catalog_word_becomes_keyword():
    r = m("basmati")
    assert (r.role, r.keyword, r.confidence) == ("keyword", "basmati", "sure")


def test_filler():
    assert m("ka").role == "filler"
    assert m("و").role == "filler"


def test_every_match_records_its_steps():
    assert m("leban").steps  # the UI shows these on hover


def test_phrases_two_and_three_words():
    tokens, _ = tokenize("hari mirch aur zaitoon ka tel")
    found = find_phrases(tokens, res)
    assert found[0].concepts == ["green_chili"] and found[1].concepts == ["green_chili"]
    assert all(found[i].concepts == ["olive_oil"] for i in (3, 4, 5))
    assert 2 not in found  # "aur" is not part of a phrase


def test_arabic_phrase_with_articles():
    tokens, _ = tokenize("الفلفل الأخضر")
    assert find_phrases(tokens, res)[0].concepts == ["green_chili"]
