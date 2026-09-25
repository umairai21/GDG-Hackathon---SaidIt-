"""Data integrity: these catch lexicon/catalog mistakes before they become search bugs."""
from pipeline.lexicon import default_resources

res = default_resources()


def test_every_catalog_concept_is_registered():
    for p in res.catalog:
        for c in p["concepts"]:
            assert c in res.concepts, f"{p['id']} uses unregistered concept {c}"


def test_every_concept_has_a_product_and_a_word():
    in_catalog = {c for p in res.catalog for c in p["concepts"]}
    in_lexicon = {c for e in list(res.exact.values()) + list(res.phrases.values()) for c in e.concepts}
    for c in res.concepts:
        assert c in in_catalog, f"concept {c} has no products"
        assert c in in_lexicon, f"concept {c} has no lexicon forms"


def test_product_ids_unique():
    ids = [p["id"] for p in res.catalog]
    assert len(ids) == len(set(ids))


def test_normalization_buckets_are_unambiguous():
    # A phonetic/skeleton key shared by two meanings must have been dropped at load time.
    for index in (res.phonetic, res.latin_skel, res.arabic_skel):
        for key, entries in index.items():
            assert len({tuple(e.concepts) for e in entries}) == 1, key


def test_ambiguous_forms_are_explicit():
    assert set(res.exact["3eish"].concepts) == {"rice", "bread"}
    assert res.exact["3eish"].ambiguous
    assert not res.exact["dahi"].ambiguous
