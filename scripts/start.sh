#!/usr/bin/env sh
# Starts the API + web app on http://localhost:8000 (fully offline; no API keys).
cd "$(dirname "$0")/.."
python3 -m uvicorn app.main:app --app-dir backend --port 8000
