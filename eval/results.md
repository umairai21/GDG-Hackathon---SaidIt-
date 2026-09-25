# Evaluation results

150 queries (140 where the store stocks the item, 10 where it doesn't). Reproduce with `python eval/run_eval.py`.

## Overall

| System | Hit@3 ↑ | Zero-result rate ↓ | Silent wrong-result rate ↓ |
|---|---|---|---|
| Baseline 1: keyword | 17.1% | 82.1% | 2.0% |
| Baseline 2: fuzzy (rapidfuzz) | 44.3% | 17.1% | 44.0% |
| Ours: What You Meant | 100.0% | 0.0% | 1.3% |

- **Hit@3**: a correct product is in the top 3 (matchable queries).
- **Zero-result**: nothing returned although the store stocks it (matchable queries). This is the lost sale.
- **Silent wrong**: the top result is the wrong product and the system gave no sign of doubt (all queries). Our results are *not* counted as silent when a token was shown as 🟡 guessed or 🔴 unknown.

## By query type

| Type | n | Hit@3 keyword / fuzzy / **ours** | Zero-result keyword / fuzzy / **ours** | Silent wrong keyword / fuzzy / **ours** |
|---|---|---|---|---|
| English | 28 | 36.0% / 88.0% / **100.0%** | 64.0% / 4.0% / **0.0%** | 0.0% / 21.4% / **0.0%** |
| Roman Urdu/Hindi | 45 | 2.4% / 14.3% / **100.0%** | 97.6% / 28.6% / **0.0%** | 0.0% / 57.8% / **2.2%** |
| Arabizi | 35 | 0.0% / 9.1% / **100.0%** | 97.0% / 21.2% / **0.0%** | 2.9% / 68.6% / **2.9%** |
| Arabic script | 23 | 52.4% / 85.7% / **100.0%** | 47.6% / 0.0% / **0.0%** | 8.7% / 26.1% / **0.0%** |
| Mixed / code-switched | 19 | 15.8% / 68.4% / **100.0%** | 84.2% / 21.1% / **0.0%** | 0.0% / 21.1% / **0.0%** |

## Is it just memorising its word lists?

Queries split by whether every word was an exact lexicon/catalog hit (*seen*) or needed normalization (phonetic key, skeleton, Arabizi transliteration, fuzzy) or was unknown (*unseen*).

| Split | n | Hit@3 (ours) |
|---|---|---|
| Seen spellings | 102 | 100.0% |
| Unseen spellings | 38 | 100.0% |

## Queries for items the store doesn't sell

| System | Returned nothing | Returned a wrong product with no warning |
|---|---|---|
| Baseline 1: keyword | 10 / 10 | 0 / 10 |
| Baseline 2: fuzzy (rapidfuzz) | 4 / 10 | 6 / 10 |
| Ours: What You Meant | 9 / 10 | 0 / 10 |

## Changes made after the first run

The eval set was written before the pipeline was run on it. Any change made afterwards is listed here.

| Change | Effect |
|---|---|
| First run (no changes) | Hit@3 98.6%, zero-result 0.0%, silent wrong 1.3% |
| Arabic consonant skeleton now needs >= 3 consonants (was 2), matching the Latin rule | fixed #51 `kelay` (had matched كولا via 'كل') |
| Arabizi final '-e' may be ة (Levantine 'lebne' = لبنة) | fixed #76 `lebne` |

## Where our pipeline fails

Every miss (Hit@3 false) or silent wrong result, unedited.

| # | Query | Type | Expected | Our top result | Chips |
|---|---|---|---|---|---|
| 62 | `doodh patti` | roman_urdu | tea | Almarai Full Fat Fresh Milk | doodh:sure patti:sure |
| 98 | `3aseer burtuqal` | arabizi | juice | Valencia Oranges Egypt | 3aseer:sure burtuqal:sure |
