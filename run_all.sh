#!/usr/bin/env bash
# Starts the backend (uvicorn) and frontend (Vite) together. Ctrl+C stops both.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -x "$ROOT/.venv/Scripts/python.exe" ]; then
  PY="$ROOT/.venv/Scripts/python.exe"
elif [ -x "$ROOT/.venv/bin/python" ]; then
  PY="$ROOT/.venv/bin/python"
else
  echo "Missing .venv at $ROOT/.venv. Create it with: uv venv && uv pip install -e ." >&2
  exit 1
fi

PIDS=()
cleanup() {
  trap - INT TERM EXIT
  for pid in "${PIDS[@]:-}"; do
    [ -n "$pid" ] && kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

echo "Starting backend on http://localhost:8000"
(cd "$ROOT/backend" && "$PY" -m uvicorn main:app --reload --port 8000) &
PIDS+=($!)

echo "Starting frontend (Vite)"
(
  cd "$ROOT/frontend"
  [ -d node_modules ] || npm install
  npm run dev
) &
PIDS+=($!)

wait -n "${PIDS[@]}"
