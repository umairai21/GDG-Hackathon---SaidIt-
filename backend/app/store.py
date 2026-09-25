"""Search logs, feedback and learned mappings, in SQLite.

The learning rule, which is the whole "interfaces that change silently" answer:
  1. A customer clicks a result for a query that had 🟡 guessed or 🔴 unknown words.
     Each such word gets one *confirmation* for the concept of the product they clicked.
  2. When a (word, concept) pair reaches N confirmations (default 3) it becomes *proposed*.
     A proposed mapping does NOTHING to search yet.
  3. Only when the store clicks Approve on the dashboard does search start using it.
     Remove turns it off again. Every proposal, approval and removal is written to the change log.
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from pipeline.lexicon import lookup_key
from pipeline.pipeline import meaningful_tokens

DB_PATH = Path(os.environ.get("SAIDIT_DB", Path(__file__).resolve().parents[1] / "saidit.db"))
CONFIRMATIONS_NEEDED = int(os.environ.get("SAIDIT_CONFIRMATIONS", "3"))
MAX_EXAMPLES = 5

COLLECTING, PROPOSED, APPROVED, REMOVED = "collecting", "proposed", "approved", "removed"

SCHEMA = """
CREATE TABLE IF NOT EXISTS searches (
    id INTEGER PRIMARY KEY, query TEXT NOT NULL, ts TEXT NOT NULL, n_results INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS search_tokens (
    search_id INTEGER NOT NULL REFERENCES searches(id), token TEXT NOT NULL, original TEXT NOT NULL,
    confidence TEXT NOT NULL, concepts TEXT NOT NULL, keyword TEXT, language TEXT NOT NULL,
    method TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY, query TEXT NOT NULL, product_id TEXT, type TEXT NOT NULL,
    tokens TEXT NOT NULL, ts TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS mappings (
    id INTEGER PRIMARY KEY, token TEXT NOT NULL, concept TEXT NOT NULL, count INTEGER NOT NULL,
    first_seen TEXT NOT NULL, last_seen TEXT NOT NULL, status TEXT NOT NULL, examples TEXT NOT NULL,
    UNIQUE (token, concept));
CREATE TABLE IF NOT EXISTS changelog (
    id INTEGER PRIMARY KEY, ts TEXT NOT NULL, mapping_id INTEGER, token TEXT NOT NULL,
    concept TEXT NOT NULL, action TEXT NOT NULL, actor TEXT NOT NULL, detail TEXT NOT NULL);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def connect(path: Path | str | None = None):
    conn = sqlite3.connect(path or DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


SCHEMA_VERSION = 2  # bump when SCHEMA changes


def init_db(conn: sqlite3.Connection) -> None:
    # Why: a database left over from an older version would crash the demo. It only holds
    # demo/seed data, so rebuilding it is safe; the app then reseeds it.
    if conn.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
        for table in ("search_tokens", "searches", "feedback", "mappings", "changelog"):
            conn.execute(f"DROP TABLE IF EXISTS {table}")
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    conn.executescript(SCHEMA)


def is_empty(conn: sqlite3.Connection) -> bool:
    return conn.execute("SELECT COUNT(*) FROM searches").fetchone()[0] == 0


# ---------------------------------------------------------------- logging

def log_search(conn: sqlite3.Connection, interp: dict, ts: str | None = None) -> int:
    cur = conn.execute("INSERT INTO searches (query, ts, n_results) VALUES (?, ?, ?)",
                       (interp["query"], ts or now(), len(interp["results"])))
    sid = cur.lastrowid
    conn.executemany(
        "INSERT INTO search_tokens VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [(sid, _key(t), t["original"], t["confidence"], json.dumps(t["concepts"]), t["keyword"],
          t["language"], t["method"])
         for t in meaningful_tokens(interp)])
    return sid


def _key(t: dict) -> str:
    """The word as the store sees it: as typed, only lowercased / Arabic-letter-folded (not our guess).
    Same key the pipeline uses to look up approved mappings."""
    return lookup_key(t["original"])


def approved_mappings(conn: sqlite3.Connection) -> dict[str, str]:
    rows = conn.execute("SELECT token, concept FROM mappings WHERE status = ?", (APPROVED,))
    return {r["token"]: r["concept"] for r in rows}


# ---------------------------------------------------------------- feedback + learning

def record_feedback(conn: sqlite3.Connection, interp: dict, product: dict | None, kind: str,
                    ts: str | None = None) -> list[dict]:
    """Store the feedback. For clicks, add confirmations. Returns the confirmations made."""
    ts = ts or now()
    tokens = meaningful_tokens(interp)
    conn.execute("INSERT INTO feedback (query, product_id, type, tokens, ts) VALUES (?, ?, ?, ?, ?)",
                 (interp["query"], product["id"] if product else None, kind,
                  json.dumps([_key(t) for t in tokens], ensure_ascii=False), ts))
    if kind != "click" or product is None:
        return []
    return [_confirm(conn, word, concept, interp["query"], ts)
            for word, concept in confirmations_from_click(tokens, product)]


def confirmations_from_click(tokens: list[dict], product: dict) -> list[tuple[str, str]]:
    """Which (word, concept) pairs does this click confirm?

    Only 🟡/🔴 words learn anything; 🟢 words were already certain. A guessed word confirms its
    guess if the clicked product has that concept. Otherwise the word is credited with the
    product's concept that no certain word in the query already explains.
    ("keema fresh" + click on Beef Mince -> keema = meat.)"""
    explained = {c for t in tokens if t["confidence"] == "sure" for c in t["concepts"]}
    out = []
    for t in tokens:
        if t["confidence"] == "sure":
            continue
        agreed = [c for c in t["concepts"] if c in product["concepts"]]
        if agreed:
            out.append((_key(t), agreed[0]))
            continue
        unexplained = [c for c in product["concepts"] if c not in explained]
        if unexplained:
            out.append((_key(t), unexplained[0]))
    return out


def _confirm(conn: sqlite3.Connection, word: str, concept: str, query: str, ts: str) -> dict:
    row = conn.execute("SELECT * FROM mappings WHERE token = ? AND concept = ?", (word, concept)).fetchone()
    if row is None:
        conn.execute("INSERT INTO mappings (token, concept, count, first_seen, last_seen, status, examples) "
                     "VALUES (?, ?, 1, ?, ?, ?, ?)",
                     (word, concept, ts, ts, COLLECTING, json.dumps([query], ensure_ascii=False)))
        row = conn.execute("SELECT * FROM mappings WHERE token = ? AND concept = ?", (word, concept)).fetchone()
    else:
        examples = json.loads(row["examples"])
        if query not in examples:
            examples = (examples + [query])[-MAX_EXAMPLES:]
        conn.execute("UPDATE mappings SET count = count + 1, last_seen = ?, examples = ? WHERE id = ?",
                     (ts, json.dumps(examples, ensure_ascii=False), row["id"]))
        row = conn.execute("SELECT * FROM mappings WHERE id = ?", (row["id"],)).fetchone()

    if row["status"] == COLLECTING and row["count"] >= CONFIRMATIONS_NEEDED:
        conn.execute("UPDATE mappings SET status = ? WHERE id = ?", (PROPOSED, row["id"]))
        _log_change(conn, row["id"], word, concept, PROPOSED, "system",
                    f"{row['count']} shoppers confirmed it; waiting for store approval (not used in search yet)", ts)
    return {"token": word, "concept": concept, "count": row["count"]}


def set_status(conn: sqlite3.Connection, mapping_id: int, status: str, ts: str | None = None) -> dict | None:
    row = conn.execute("SELECT * FROM mappings WHERE id = ?", (mapping_id,)).fetchone()
    if row is None:
        return None
    ts = ts or now()
    conn.execute("UPDATE mappings SET status = ? WHERE id = ?", (status, mapping_id))
    if status == APPROVED:
        # One word, one approved meaning: approving a new meaning retires the previous one, visibly.
        for other in conn.execute("SELECT * FROM mappings WHERE token = ? AND id != ? AND status = ?",
                                  (row["token"], mapping_id, APPROVED)).fetchall():
            conn.execute("UPDATE mappings SET status = ? WHERE id = ?", (REMOVED, other["id"]))
            _log_change(conn, other["id"], other["token"], other["concept"], REMOVED, "store",
                        f"replaced by {row['concept']}", ts)
    detail = {APPROVED: "search now uses this mapping", REMOVED: "search no longer uses this mapping"}[status]
    _log_change(conn, mapping_id, row["token"], row["concept"], status, "store", detail, ts)
    return mapping_row(conn.execute("SELECT * FROM mappings WHERE id = ?", (mapping_id,)).fetchone())


def _log_change(conn, mapping_id, token, concept, action, actor, detail, ts) -> None:
    conn.execute("INSERT INTO changelog (ts, mapping_id, token, concept, action, actor, detail) "
                 "VALUES (?, ?, ?, ?, ?, ?, ?)", (ts, mapping_id, token, concept, action, actor, detail))


# ---------------------------------------------------------------- dashboard queries

def mapping_row(r: sqlite3.Row) -> dict:
    return {"id": r["id"], "token": r["token"], "concept": r["concept"], "count": r["count"],
            "needed": CONFIRMATIONS_NEEDED, "first_seen": r["first_seen"], "last_seen": r["last_seen"],
            "status": r["status"], "examples": json.loads(r["examples"])}


def mappings(conn: sqlite3.Connection) -> list[dict]:
    order = "CASE status WHEN 'proposed' THEN 0 WHEN 'approved' THEN 1 WHEN 'collecting' THEN 2 ELSE 3 END"
    return [mapping_row(r) for r in conn.execute(f"SELECT * FROM mappings ORDER BY {order}, count DESC")]


def unfamiliar_words(conn: sqlite3.Connection, lost_sale_min: int = 2) -> list[dict]:
    """Every word that was ever 🟡 guessed, 🔴 unknown or store-approved, with how often
    customers typed it and how often it ended in zero results (a likely lost sale)."""
    rows = conn.execute(
        "SELECT st.*, s.n_results, s.ts FROM search_tokens st JOIN searches s ON s.id = st.search_id "
        "ORDER BY st.search_id").fetchall()
    words: dict[str, dict] = {}
    for r in rows:
        w = words.get(r["token"])
        if w is None:
            w = words[r["token"]] = {"token": r["token"], "searches": 0, "zero_result_searches": 0,
                                     "first_seen": r["ts"], "corrections": 0, "ever_unfamiliar": False}
        w["searches"] += 1
        w["zero_result_searches"] += r["n_results"] == 0
        w["ever_unfamiliar"] |= r["confidence"] != "sure" or r["method"] == "store_approved"
        # the latest search decides how the word is read *today*
        w.update(confidence=r["confidence"], concepts=json.loads(r["concepts"]), keyword=r["keyword"],
                 language=r["language"],
                 method=r["method"], last_seen=r["ts"])

    for f in conn.execute("SELECT tokens FROM feedback WHERE type = 'not_what_i_meant'"):
        for tok in json.loads(f["tokens"]):
            if tok in words:
                words[tok]["corrections"] += 1

    maps: dict[str, list[dict]] = {}
    for m in mappings(conn):
        maps.setdefault(m["token"], []).append(m)

    out = []
    for w in words.values():
        if not w.pop("ever_unfamiliar"):
            continue
        w["mappings"] = maps.get(w["token"], [])
        w["lost_sale"] = w["confidence"] == "unknown" and w["zero_result_searches"] >= lost_sale_min
        out.append(w)
    out.sort(key=lambda w: (-w["lost_sale"], -w["zero_result_searches"], -w["searches"]))
    return out


def changelog(conn: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM changelog ORDER BY ts DESC, id DESC")]


def search_stats(conn: sqlite3.Connection) -> dict:
    total, zero = conn.execute("SELECT COUNT(*), COALESCE(SUM(n_results = 0), 0) FROM searches").fetchone()
    return {"searches": total, "zero_result_searches": zero}
