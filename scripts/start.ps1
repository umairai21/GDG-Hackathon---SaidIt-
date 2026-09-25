# Starts the API + web app on http://localhost:8000 (fully offline; no API keys).
Set-Location (Join-Path $PSScriptRoot "..")
python -m uvicorn app.main:app --app-dir backend --port 8000
