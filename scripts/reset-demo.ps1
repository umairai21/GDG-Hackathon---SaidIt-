# Wipe the demo database and reseed the two-week history (run before presenting).
Set-Location (Join-Path $PSScriptRoot "..")
python backend/app/seed.py --reset
