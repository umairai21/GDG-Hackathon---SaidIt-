#!/usr/bin/env sh
# Wipe the demo database and reseed the two-week history (run before presenting).
cd "$(dirname "$0")/.."
python3 backend/app/seed.py --reset
