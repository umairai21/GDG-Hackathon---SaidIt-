#!/usr/bin/env sh
# Wipe the demo database and reseed the two-week history (run before presenting).
cd "$(dirname "$0")/.."
python backend/app/seed.py --reset
