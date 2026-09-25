"""Evaluate our pipeline against two baselines on data/eval/queries.csv.

Run:  python eval/run_eval.py
Writes eval/results.md (human) and eval/results.json (served by the API / dashboard).

Metrics (all per query):
  Hit@3              matchable queries only: a product of the expected concept is in the top 3.
  Zero-result rate   matchable queries only: the system returned nothing (the store *does* stock it).
  Silent wrong rate  all queries: results were returned, the top result is the wrong concept
                     (or the query had no correct product at all), and the system showed no
                     uncertainty. Baselines never show uncertainty. Our pipeline counts as having
                     shown it when any meaningful token is 'guessed' or 'unknown'.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from baselines import fuzzy_search, keyword_search  # noqa: E402
from pipeline import interpret  # noqa: E402
from pipeline.lexicon import default_resources  # noqa: E402
from pipeline.pipeline import meaningful_tokens  # noqa: E402

QUERIES = ROOT / "data" / "eval" / "queries.csv"
TYPES = ["english", "roman_urdu", "arabizi", "arabic", "mixed"]
TYPE_LABELS = {"english": "English", "roman_urdu": "Roman Urdu/Hindi", "arabizi": "Arabizi",
               "arabic": "Arabic script", "mixed": "Mixed / code-switched"}
SYSTEMS = ["keyword", "fuzzy", "ours"]
SYSTEM_LABELS = {"keyword": "Baseline 1: keyword", "fuzzy": "Baseline 2: fuzzy (rapidfuzz)",
                 "ours": "Ours: What You Meant"}
# Every change made to the pipeline after the eval set was first run. Kept in the report so the
# numbers can be judged honestly. Rule: general rule fixes are allowed and logged here; adding an
# eval query's exact word to a lexicon is not.
CHANGES_AFTER_FIRST_RUN = [
    ("First run (no changes)", "Hit@3 98.6%, zero-result 0.0%, silent wrong 1.3%"),
    ("Arabic consonant skeleton now needs >= 3 consonants (was 2), matching the Latin rule",
     "fixed #51 `kelay` (had matched كولا via 'كل')"),
    ("Arabizi final '-e' may be ة (Levantine 'lebne' = لبنة)", "fixed #76 `lebne`"),
]
# Rules that are plain lookups; a query resolved only by these was "seen" by the lexicon.
LOOKUP_METHODS = {"lexicon_exact", "lexicon_ambiguous", "phrase", "catalog_word"}


def load_queries() -> list[dict]:
    with QUERIES.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["expected"] = set() if r["expected"] == "NONE" else set(r["expected"].split("|"))
    return rows


def run_system(name: str, query: str, catalog: list[dict]) -> tuple[list[dict], bool, dict | None]:
    """-> (results, showed_uncertainty, interpretation)"""
    if name == "keyword":
        return keyword_search(query, catalog), False, None
    if name == "fuzzy":
        return fuzzy_search(query, catalog), False, None
    out = interpret(query)
    flagged = any(t["confidence"] != "sure" for t in meaningful_tokens(out))
    return out["results"], flagged, out


def is_correct(product: dict, expected: set[str]) -> bool:
    return bool(expected & set(product["concepts"]))


def evaluate() -> dict:
    catalog = default_resources().catalog
    queries = load_queries()
    per_query = []
    for q in queries:
        row = {"id": q["id"], "query": q["query"], "type": q["type"],
               "expected": sorted(q["expected"]) or ["NONE"], "systems": {}}
        for s in SYSTEMS:
            results, flagged, interp = run_system(s, q["query"], catalog)
            top = results[0] if results else None
            wrong_top = top is not None and not is_correct(top, q["expected"])
            row["systems"][s] = {
                "hit3": any(is_correct(p, q["expected"]) for p in results[:3]) if q["expected"] else None,
                "zero": (not results) if q["expected"] else None,
                "silent_wrong": wrong_top and not flagged,
                "flagged": flagged,
                "top": top["name_en"] if top else None,
            }
            if interp is not None:
                toks = meaningful_tokens(interp)
                row["seen"] = bool(toks) and all(t["method"] in LOOKUP_METHODS for t in toks)
                row["chips"] = [f'{t["original"]}:{t["confidence"]}' for t in toks]
        per_query.append(row)
    return {"queries": per_query, "summary": summarize(per_query)}


def _rate(rows: list[dict], system: str, metric: str) -> float | None:
    vals = [r["systems"][system][metric] for r in rows if r["systems"][system][metric] is not None]
    return round(100 * sum(vals) / len(vals), 1) if vals else None


def summarize(rows: list[dict]) -> dict:
    matchable = [r for r in rows if r["expected"] != ["NONE"]]
    nomatch = [r for r in rows if r["expected"] == ["NONE"]]
    summary: dict = {"n_queries": len(rows), "n_matchable": len(matchable), "n_no_match": len(nomatch),
                     "overall": {}, "by_type": {}, "ours_seen_unseen": {}, "no_match": {}}
    for s in SYSTEMS:
        summary["overall"][s] = {"hit3": _rate(matchable, s, "hit3"), "zero": _rate(matchable, s, "zero"),
                                 "silent_wrong": _rate(rows, s, "silent_wrong")}
        summary["no_match"][s] = {
            "returned_nothing": sum(not r["systems"][s]["top"] for r in nomatch),
            "silent_wrong": sum(r["systems"][s]["silent_wrong"] for r in nomatch),
        }
    for t in TYPES:
        sub = [r for r in rows if r["type"] == t]
        sub_m = [r for r in sub if r["expected"] != ["NONE"]]
        summary["by_type"][t] = {"n": len(sub), **{s: {
            "hit3": _rate(sub_m, s, "hit3"), "zero": _rate(sub_m, s, "zero"),
            "silent_wrong": _rate(sub, s, "silent_wrong")} for s in SYSTEMS}}
    for label, pred in (("seen", True), ("unseen", False)):
        sub = [r for r in matchable if r.get("seen") is pred]
        summary["ours_seen_unseen"][label] = {"n": len(sub), "hit3": _rate(sub, "ours", "hit3")}
    return summary


def fmt(v: float | None) -> str:
    return "-" if v is None else f"{v:.1f}%"


def to_markdown(result: dict) -> str:
    s, rows = result["summary"], result["queries"]
    out = [
        "# Evaluation results",
        "",
        f"{s['n_queries']} queries ({s['n_matchable']} where the store stocks the item, "
        f"{s['n_no_match']} where it doesn't). Reproduce with `python eval/run_eval.py`.",
        "",
        "## Overall",
        "",
        "| System | Hit@3 ↑ | Zero-result rate ↓ | Silent wrong-result rate ↓ |",
        "|---|---|---|---|",
    ]
    for sys_ in SYSTEMS:
        o = s["overall"][sys_]
        out.append(f"| {SYSTEM_LABELS[sys_]} | {fmt(o['hit3'])} | {fmt(o['zero'])} | {fmt(o['silent_wrong'])} |")
    out += [
        "",
        "- **Hit@3**: a correct product is in the top 3 (matchable queries).",
        "- **Zero-result**: nothing returned although the store stocks it (matchable queries). This is the lost sale.",
        "- **Silent wrong**: the top result is the wrong product and the system gave no sign of doubt (all queries). "
        "Our results are *not* counted as silent when a token was shown as 🟡 guessed or 🔴 unknown.",
        "",
        "## By query type",
        "",
        "| Type | n | Hit@3 keyword / fuzzy / **ours** | Zero-result keyword / fuzzy / **ours** | Silent wrong keyword / fuzzy / **ours** |",
        "|---|---|---|---|---|",
    ]
    for t in TYPES:
        b = s["by_type"][t]
        cell = lambda m: " / ".join(fmt(b[x][m]) if x != "ours" else f"**{fmt(b[x][m])}**" for x in SYSTEMS)
        out.append(f"| {TYPE_LABELS[t]} | {b['n']} | {cell('hit3')} | {cell('zero')} | {cell('silent_wrong')} |")

    su = s["ours_seen_unseen"]
    out += [
        "",
        "## Is it just memorising its word lists?",
        "",
        "Queries split by whether every word was an exact lexicon/catalog hit (*seen*) or needed "
        "normalization (phonetic key, skeleton, Arabizi transliteration, fuzzy) or was unknown (*unseen*).",
        "",
        "| Split | n | Hit@3 (ours) |",
        "|---|---|---|",
        f"| Seen spellings | {su['seen']['n']} | {fmt(su['seen']['hit3'])} |",
        f"| Unseen spellings | {su['unseen']['n']} | {fmt(su['unseen']['hit3'])} |",
        "",
        "## Queries for items the store doesn't sell",
        "",
        "| System | Returned nothing | Returned a wrong product with no warning |",
        "|---|---|---|",
    ]
    for sys_ in SYSTEMS:
        nm = s["no_match"][sys_]
        out.append(f"| {SYSTEM_LABELS[sys_]} | {nm['returned_nothing']} / {s['n_no_match']} "
                   f"| {nm['silent_wrong']} / {s['n_no_match']} |")

    out += ["", "## Changes made after the first run", "",
            "The eval set was written before the pipeline was run on it. Any change made afterwards is listed here.",
            "", "| Change | Effect |", "|---|---|"]
    out += [f"| {c} | {e} |" for c, e in CHANGES_AFTER_FIRST_RUN]

    misses = [r for r in rows if r["systems"]["ours"]["hit3"] is False or r["systems"]["ours"]["silent_wrong"]]
    out += ["", "## Where our pipeline fails", "",
            "Every miss (Hit@3 false) or silent wrong result, unedited.", "",
            "| # | Query | Type | Expected | Our top result | Chips |", "|---|---|---|---|---|---|"]
    for r in misses:
        o = r["systems"]["ours"]
        out.append(f"| {r['id']} | `{r['query']}` | {r['type']} | {', '.join(r['expected'])} "
                   f"| {o['top'] or '(none)'} | {' '.join(r.get('chips', []))} |")
    if not misses:
        out.append("| - | none | | | | |")
    return "\n".join(out) + "\n"


README_START, README_END = "<!-- EVAL:START -->", "<!-- EVAL:END -->"


def update_readme(md: str) -> None:
    """Copy the Overall and By-type tables into README.md between the EVAL markers,
    so the README can never show numbers the code doesn't produce."""
    readme = ROOT / "README.md"
    if not readme.exists():
        return
    text = readme.read_text(encoding="utf-8")
    if README_START not in text or README_END not in text:
        return
    # everything from "## Overall" up to (not including) the seen/unseen section
    body = md[md.index("## Overall"):md.index("## Is it just")].replace("## ", "#### ")
    head, rest = text.split(README_START, 1)
    _, tail = rest.split(README_END, 1)
    readme.write_text(f"{head}{README_START}\n{body.strip()}\n{README_END}{tail}", encoding="utf-8")


def main() -> None:
    result = evaluate()
    md = to_markdown(result)
    (ROOT / "eval" / "results.md").write_text(md, encoding="utf-8")
    (ROOT / "eval" / "results.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    update_readme(md)
    print(md)


if __name__ == "__main__":
    main()
