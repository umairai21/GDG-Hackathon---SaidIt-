"""FastAPI server.  Run from the repo root:  uvicorn app.main:app --app-dir backend --port 8000

Serves the API and, if it has been built (frontend/dist), the web app on the same port.
"""
from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import store
from app.seed import seed
from baselines import fuzzy_search
from pipeline import interpret
from pipeline.lexicon import default_resources

ROOT = Path(__file__).resolve().parents[2]
EVAL_RESULTS = ROOT / "eval" / "results.json"
FRONTEND_DIST = ROOT / "frontend" / "dist"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    with store.connect() as conn:
        store.init_db(conn)
        if store.is_empty(conn) and os.environ.get("SAIDIT_NO_SEED") != "1":
            seed(conn)
    yield


app = FastAPI(title="What You Meant", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class SearchIn(BaseModel):
    query: str = Field(max_length=200)


class FeedbackIn(BaseModel):
    query: str = Field(max_length=200)
    product_id: str | None = None
    type: Literal["click", "not_what_i_meant"]


def _products() -> dict[str, dict]:
    return {p["id"]: p for p in default_resources().catalog}


@app.post("/search")
def search(body: SearchIn) -> dict:
    query = body.query.strip()
    with store.connect() as conn:
        interp = interpret(query, approved=store.approved_mappings(conn))
        if query:
            store.log_search(conn, interp)
    return {**interp, "baseline_results": fuzzy_search(query, default_resources().catalog)}


@app.post("/feedback")
def feedback(body: FeedbackIn) -> dict:
    product = _products().get(body.product_id) if body.product_id else None
    if body.type == "click" and product is None:
        raise HTTPException(404, "unknown product_id")
    with store.connect() as conn:
        interp = interpret(body.query, approved=store.approved_mappings(conn))
        confirmations = store.record_feedback(conn, interp, product, body.type)
    return {"ok": True, "confirmations": confirmations}


@app.get("/store/words")
def store_words() -> dict:
    concepts = default_resources().concepts
    with store.connect() as conn:
        return {
            "words": store.unfamiliar_words(conn),
            "mappings": store.mappings(conn),
            "stats": store.search_stats(conn),
            "confirmations_needed": store.CONFIRMATIONS_NEEDED,
            "concept_labels": {k: v["en"] for k, v in concepts.items()},
        }


def _set(mapping_id: int, status: str) -> dict:
    with store.connect() as conn:
        row = store.set_status(conn, mapping_id, status)
    if row is None:
        raise HTTPException(404, "unknown mapping")
    return row


@app.post("/store/mappings/{mapping_id}/approve")
def approve(mapping_id: int) -> dict:
    return _set(mapping_id, store.APPROVED)


@app.post("/store/mappings/{mapping_id}/remove")
def remove(mapping_id: int) -> dict:
    return _set(mapping_id, store.REMOVED)


@app.get("/store/changelog")
def changelog() -> list[dict]:
    with store.connect() as conn:
        return store.changelog(conn)


@app.get("/eval/summary")
def eval_summary() -> dict:
    if not EVAL_RESULTS.exists():
        raise HTTPException(404, "run `python eval/run_eval.py` first")
    return json.loads(EVAL_RESULTS.read_text(encoding="utf-8"))["summary"]


# ---------------------------------------------------------------- built web app (optional)
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        file = FRONTEND_DIST / path
        return FileResponse(file if path and file.is_file() else FRONTEND_DIST / "index.html")
