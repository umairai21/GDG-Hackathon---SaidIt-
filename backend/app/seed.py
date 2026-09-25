"""Seed two weeks of realistic search history so the store dashboard has data on first run.

Every seeded event goes through the SAME code path as a live customer (interpret -> log_search
-> record_feedback -> set_status), so the dashboard can't show anything the real system couldn't produce.
Run directly to reset:  python backend/app/seed.py --reset
"""
from __future__ import annotations

import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import store  # noqa: E402
from pipeline import interpret  # noqa: E402
from pipeline.lexicon import default_resources  # noqa: E402

DAYS = 14

# (query, how many searches, [(product clicked, how many of those searches clicked it)], "not what I meant" count,
#  day range (days ago, from -> to))
HISTORY = [
    # everyday searches the pipeline already handles; gives the dashboard realistic totals
    ("milk", 30, [("P001", 12)], 0, (14, 0)),
    ("dahi 1kg", 18, [("P007", 10)], 0, (14, 0)),
    ("karak chai", 22, [("P115", 9)], 0, (14, 0)),
    ("chawal basmati 5 kilo", 12, [("P045", 6)], 0, (14, 0)),
    ("حليب", 15, [("P001", 7)], 0, (14, 0)),
    ("laban", 14, [("P012", 8)], 0, (14, 0)),
    ("eggs 30", 20, [("P030", 11)], 0, (14, 0)),
    ("7aleeb", 9, [("P003", 4)], 0, (14, 0)),
    # 🟡 ambiguous: Gulf shoppers mostly mean rice by 3eish, some mean bread
    ("3eish", 11, [("P045", 4), ("P052", 1)], 0, (13, 1)),
    # 🟡 guessed correctly, confirmed by clicks -> proposed
    ("leban", 7, [("P012", 3)], 0, (12, 2)),
    ("dahee", 6, [("P007", 2)], 0, (10, 1)),            # 2/3 confirmations: still collecting
    # 🟡 guessed WRONG ("classic"); shoppers say so, and teach the right answer via "lassi almarai"
    ("lassi", 9, [], 4, (13, 0)),
    ("lassi almarai", 4, [("P012", 3)], 0, (9, 1)),
    # 🔴 unknown, then learned + approved: qeema = minced meat
    ("qeema al islami", 3, [("P040", 3)], 0, (12, 9)),
    ("qeema", 5, [("P040", 3)], 0, (6, 0)),           # after approval (day 8) these are 🟢
    # 🔴 unknown with zero results: lost sales
    ("keema", 6, [], 0, (11, 0)),                     # same dish, different spelling: not learned yet
    ("nihari", 9, [], 0, (14, 0)),
    ("rooh afza", 7, [], 0, (13, 0)),
    ("shawarma", 6, [], 0, (12, 0)),
    ("kulfi", 4, [], 0, (10, 0)),
    ("samosa", 5, [], 0, (9, 0)),
    # 🟡 wrong guess (paan = betel leaf, read as pani = water); customers push back
    ("paan", 5, [], 3, (8, 0)),
]

# (days ago, word, concept, new status): decisions the store made in the seeded fortnight
STORE_DECISIONS = [(8, "qeema", "meat", store.APPROVED)]


def seed(conn, rng: random.Random | None = None) -> None:
    rng = rng or random.Random(42)  # fixed seed: the demo looks the same every time
    catalog = {p["id"]: p for p in default_resources().catalog}
    start = datetime.now(timezone.utc) - timedelta(days=DAYS)

    events = []  # (timestamp, kind, payload)
    for query, n, clicks, complaints, (from_day, to_day) in HISTORY:
        click_plan = [pid for pid, k in clicks for _ in range(k)]
        for i in range(n):
            days_ago = rng.uniform(to_day, from_day)
            ts = datetime.now(timezone.utc) - timedelta(days=days_ago, minutes=rng.randint(0, 600))
            action = ("click", click_plan[i]) if i < len(click_plan) else (
                ("not_what_i_meant", None) if i - len(click_plan) < complaints else (None, None))
            events.append((max(ts, start), "search", (query, action)))
    for days_ago, word, concept, status in STORE_DECISIONS:
        events.append((datetime.now(timezone.utc) - timedelta(days=days_ago), "decision", (word, concept, status)))
    events.sort(key=lambda e: e[0])

    for ts, kind, payload in events:
        stamp = ts.isoformat(timespec="seconds")
        if kind == "decision":
            word, concept, status = payload
            row = conn.execute("SELECT id FROM mappings WHERE token = ? AND concept = ?", (word, concept)).fetchone()
            if row:
                store.set_status(conn, row["id"], status, stamp)
            continue
        query, (action, pid) = payload
        interp = interpret(query, approved=store.approved_mappings(conn))
        store.log_search(conn, interp, stamp)
        if action:
            store.record_feedback(conn, interp, catalog.get(pid), action, stamp)


if __name__ == "__main__":
    if "--reset" in sys.argv and store.DB_PATH.exists():
        store.DB_PATH.unlink()
    with store.connect() as conn:
        store.init_db(conn)
        if store.is_empty(conn):
            seed(conn)
            print(f"Seeded {store.DB_PATH}")
        else:
            print(f"{store.DB_PATH} already has data; use --reset to start over")
