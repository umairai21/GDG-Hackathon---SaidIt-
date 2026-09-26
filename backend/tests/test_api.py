"""End-to-end API tests on a throwaway database (no seed data)."""

import pytest


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SAIDIT_NO_SEED", "1")
    from app import store
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "test.db")
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        # store endpoints need the manager signed in; the customer ones don't care
        assert c.post("/auth/login", json={"password": "store123"}).status_code == 200
        yield c


def search(client, q):
    return client.post("/search", json={"query": q}).json()


def click(client, q, pid):
    return client.post("/feedback", json={"query": q, "product_id": pid, "type": "click"}).json()


def test_search_returns_interpretation_and_baseline(client):
    out = search(client, "dahi 1kg")
    assert out["tokens"][0]["concepts"] == ["yogurt"]
    assert out["quantity"]["unit"] == "g"
    assert out["results"][0]["id"] == "P007"
    assert "baseline_results" in out


def test_learning_is_proposed_not_applied_until_approved(client):
    # "keema" is unknown; with "islami" (a catalog word) the shopper finds Beef Mince and clicks it.
    for _ in range(3):
        search(client, "keema islami")
        click(client, "keema islami", "P040")

    words = client.get("/store/words").json()
    [m] = [m for m in words["mappings"] if m["token"] == "keema"]
    assert (m["concept"], m["count"], m["status"]) == ("meat", 3, "proposed")

    # proposed does NOT change search
    assert search(client, "keema")["tokens"][0]["confidence"] == "unknown"

    client.post(f"/store/mappings/{m['id']}/approve")
    t = search(client, "keema")["tokens"][0]
    assert (t["confidence"], t["concepts"], t["method"]) == ("sure", ["meat"], "store_approved")

    client.post(f"/store/mappings/{m['id']}/remove")
    assert search(client, "keema")["tokens"][0]["confidence"] == "unknown"

    actions = [c["action"] for c in client.get("/store/changelog").json()]
    assert actions == ["removed", "approved", "proposed"]  # newest first; nothing hidden


def test_click_on_certain_query_learns_nothing(client):
    assert click(client, "milk", "P001")["confirmations"] == []


def test_not_what_i_meant_counts_as_correction(client):
    search(client, "paan")
    client.post("/feedback", json={"query": "paan", "type": "not_what_i_meant"})
    [w] = [w for w in client.get("/store/words").json()["words"] if w["token"] == "paan"]
    assert w["corrections"] == 1


def test_unknown_zero_result_word_is_lost_sale(client):
    for _ in range(2):
        search(client, "nihari")
    [w] = [w for w in client.get("/store/words").json()["words"] if w["token"] == "nihari"]
    assert w["lost_sale"] and w["zero_result_searches"] == 2


def test_bad_requests(client):
    assert client.post("/feedback", json={"query": "x", "product_id": "NOPE", "type": "click"}).status_code == 404
    assert client.post("/store/mappings/999/approve").status_code == 404
    assert client.post("/feedback", json={"query": "x", "type": "hack"}).status_code == 422


def test_customer_cannot_use_store_api(client):
    client.post("/auth/logout")
    assert client.get("/auth/me").json() == {"manager": False}
    assert client.get("/store/words").status_code == 401
    assert client.get("/store/changelog").status_code == 401
    assert client.post("/store/mappings/1/approve").status_code == 401
    assert client.post("/store/mappings/1/remove").status_code == 401
    # customer features keep working without signing in
    assert client.post("/search", json={"query": "dahi"}).status_code == 200


def test_wrong_password_is_rejected(client):
    client.post("/auth/logout")
    assert client.post("/auth/login", json={"password": "guess"}).status_code == 401
    assert client.get("/store/words").status_code == 401


def test_manager_session_cookie_is_httponly(client):
    client.post("/auth/logout")
    r = client.post("/auth/login", json={"password": "store123"})
    assert "httponly" in r.headers["set-cookie"].lower()
    assert client.get("/auth/me").json() == {"manager": True}


def test_app_page_is_never_cached(client):
    # a stale cached page would run the old app against the new API
    from app.main import FRONTEND_DIST
    if not FRONTEND_DIST.exists():
        pytest.skip("frontend not built")
    for path in ("/", "/shop", "/store"):
        r = client.get(path)
        assert r.status_code == 200 and r.headers["cache-control"] == "no-cache"
