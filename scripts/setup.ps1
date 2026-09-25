# One-time setup: Python deps, build the web app, run the evaluation.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
pip install -r backend/requirements-dev.txt
Push-Location frontend; npm install; npm run build; Pop-Location
python eval/run_eval.py | Out-Null
Write-Host "Setup done. Start with: .\scripts\start.ps1"
