from pipeline import interpret


def ids(query, k=3):
    return [r["id"] for r in interpret(query, top_k=k)["results"]]


def concepts_of(query, k=3):
    return [r["concepts"] for r in interpret(query, top_k=k)["results"]]


def test_quantity_prefers_matching_pack_size():
    assert ids("dahi 1kg")[0] == "P007"  # the 1 kg yogurt


def test_keyword_narrows_within_concept():
    top = interpret("chawal basmati", top_k=3)["results"]
    assert all("basmati" in r["name_en"].lower() for r in top)


def test_ambiguous_query_shows_both_meanings_in_top_3():
    seen = {c for cs in concepts_of("3eish") for c in cs}
    assert {"rice", "bread"} <= seen


def test_multi_concept_query_prefers_product_matching_both():
    assert concepts_of("karak chai", 1)[0] == ["karak_tea", "tea"]


def test_all_unknown_query_returns_nothing_but_explains():
    out = interpret("xyzzy qwrt")
    assert out["results"] == []
    assert all(t["confidence"] == "unknown" for t in out["tokens"])
    assert len(out["summary"]) == 2


def test_results_never_match_nothing():
    for r in interpret("bebsi xyzzy", top_k=20)["results"]:
        assert r["matched_concepts"] or r["matched_keywords"]


def test_explanation_has_every_field_the_ui_needs():
    t = interpret("leban")["tokens"][0]
    for key in ("original", "normalized", "language_label", "concept_labels",
                "confidence", "score", "method", "why", "steps"):
        assert key in t
    assert t["original"] == "leban" and t["confidence"] == "guessed"


def test_summary_sentence():
    assert interpret("dahi")["summary"] == ['We read "dahi" as yogurt (Urdu/Hindi).']


def test_code_switched_query():
    out = interpret("zaitoon ka tel 1L")
    assert out["quantity"]["display"] == "1 L"
    assert out["results"][0]["id"] == "P074"  # olive oil, 1 L
