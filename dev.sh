#!/usr/bin/env bash
# Starts backend (:8000) and frontend (:5173) with auto-reload; Ctrl+C stops both.
set -euo pipefail
cd "$(dirname "$0")"

trap 'kill 0' EXIT

(cd backend && uv run fastapi dev app/main.py) &
(cd frontend && npm run dev) &

wait
