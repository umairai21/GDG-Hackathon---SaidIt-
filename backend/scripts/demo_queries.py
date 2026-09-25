"""Print the pipeline's interpretation of sample queries.  Run: python backend/scripts/demo_queries.py [query ...]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252

from pipeline import interpret  # noqa: E402

SAMPLES = [
    "dahi 1kg",
    "3eish",
    "karak chai",
    "chawal basmati 5 kilo",
    "leban",
    "dahee",
    "7aleeb almarai",
    "الحليب ٢ لتر",
    "hari mirch aur adrak",
    "bebsi xyzzy",
]

ICON = {"sure": "[sure]   ", "guessed": "[guessed]", "unknown": "[UNKNOWN]"}


def show(query: str) -> None:
    out = interpret(query, top_k=3)
    print(f"\n=== {query!r}" + (f"   quantity: {out['quantity']['display']}" if out["quantity"] else ""))
    for t in out["tokens"]:
        meaning = ", ".join(t["concept_labels"]) or t["keyword"] or "-"
        score = f" {t['score']}%" if t["score"] is not None else ""
        print(f"  {ICON[t['confidence']]} {t['original']:<10} -> {t['normalized']:<10} -> {meaning:<22}"
              f" lang={t['language_label']:<12} rule={t['method']}{score}")
    for line in out["summary"]:
        print(f"  > {line}")
    for r in out["results"]:
        print(f"    {r['id']}  {r['name_en']:<42} {r['size']:<8} score={r['score']}")
    if not out["results"]:
        print("    (no results)")


if __name__ == "__main__":
    for q in sys.argv[1:] or SAMPLES:
        show(q)
