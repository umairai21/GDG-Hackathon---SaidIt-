from pipeline.language import fill_from_context, refine, tag_initial
from pipeline.lexicon import default_resources

res = default_resources()


def test_arabic_script_is_arabic():
    assert tag_initial("حليب", "arabic", res)[0] == "arabic"


def test_lexicon_hit_gives_language():
    assert tag_initial("dahi", "latin", res)[0] == "roman_urdu"
    assert tag_initial("milk", "latin", res)[0] == "english"


def test_word_in_two_lexicons_reports_both():
    lang, _ = tag_initial("batata", "latin", res)
    assert set(lang.split("+")) == {"roman_urdu", "arabizi"}


def test_arabizi_rule_digits_as_letters():
    lang, reason = tag_initial("mash7oon", "mixed", res)  # not in any lexicon
    assert lang == "arabizi" and "digits" in reason


def test_roman_urdu_suffix_rule():
    assert tag_initial("sabziwala", "latin", res)[0] == "roman_urdu"


def test_unknown_when_no_cue():
    assert tag_initial("qwxz", "latin", res)[0] == "unknown"


def test_refine_latin_matched_via_arabic_is_arabizi():
    assert refine("unknown", "", "latin", ["arabic"], "arabizi_transliteration", None, res)[0] == "arabizi"


def test_context_fill_only_when_query_agrees():
    assert fill_from_context(["roman_urdu", "unknown", "english"]) == "roman_urdu"
    assert fill_from_context(["roman_urdu", "arabizi", "unknown"]) is None
    assert fill_from_context(["english", "unknown"]) is None
