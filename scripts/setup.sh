#!/usr/bin/env sh
# One-time setup: Python deps, build the web app, run the evaluation.
set -e
cd "$(dirname "$0")/.."
python3 -m pip install -r backend/requirements-dev.txt
(cd frontend && npm install && npm run build)
python3 eval/run_eval.py > /dev/null
echo "Setup done. Start with: sh scripts/start.sh"
