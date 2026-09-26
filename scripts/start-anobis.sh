#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/fraud_detection_system/backend"
FRONTEND_DIR="$ROOT_DIR/fraud_detection_system/frontend"

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8001}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-4321}"
OLLAMA_MODEL="${OLLAMA_MODEL:-gemma-4-31b-it}"
LOG_DIR="${LOG_DIR:-$ROOT_DIR/.anobis-logs}"

mkdir -p "$LOG_DIR"

pids=()

cleanup() {
  local exit_code=$?
  if [ "${#pids[@]}" -gt 0 ]; then
    echo
    echo "Stopping Anobis services..."
    for pid in "${pids[@]}"; do
      if kill -0 "$pid" >/dev/null 2>&1; then
        kill "$pid" >/dev/null 2>&1 || true
      fi
    done
  fi
  exit "$exit_code"
}

trap cleanup EXIT INT TERM

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1"
    exit 1
  fi
}

wait_for_http() {
  local url="$1"
  local label="$2"
  local timeout_seconds="${3:-120}"
  local started_at
  started_at="$(date +%s)"

  while true; do
    if curl -fsS "$url" >/dev/null 2>&1; then
      echo "$label is ready."
      return 0
    fi

    if [ "$(( $(date +%s) - started_at ))" -ge "$timeout_seconds" ]; then
      echo "$label did not become ready in ${timeout_seconds}s: $url"
      return 1
    fi

    sleep 2
  done
}

require_cmd curl
require_cmd ollama
require_cmd npm

if [ ! -x "$BACKEND_DIR/.venv/bin/python" ]; then
  echo "Backend virtualenv not found at $BACKEND_DIR/.venv"
  echo "Create it once with:"
  echo "  cd $BACKEND_DIR && python -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  echo "Frontend dependencies not found at $FRONTEND_DIR/node_modules"
  echo "Install them once with:"
  echo "  cd $FRONTEND_DIR && npm install"
  exit 1
fi

echo "Starting Anobis..."
echo "Logs: $LOG_DIR"

if curl -fsS "http://127.0.0.1:11434/api/tags" >/dev/null 2>&1; then
  echo "Ollama is already running."
else
  echo "Starting Ollama..."
  ollama serve >"$LOG_DIR/ollama.log" 2>&1 &
  pids+=("$!")
  wait_for_http "http://127.0.0.1:11434/api/tags" "Ollama" 60
fi

if ! ollama list | awk '{print $1}' | grep -Fx "$OLLAMA_MODEL" >/dev/null 2>&1; then
  echo "Ollama model '$OLLAMA_MODEL' is not installed."
  echo "Install it once with:"
  echo "  ollama pull $OLLAMA_MODEL"
  exit 1
fi

echo "Starting backend on http://$BACKEND_HOST:$BACKEND_PORT ..."
(
  cd "$BACKEND_DIR"
  OLLAMA_MODEL="$OLLAMA_MODEL" \
    .venv/bin/python -m uvicorn main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT"
) >"$LOG_DIR/backend.log" 2>&1 &
pids+=("$!")

wait_for_http "http://$BACKEND_HOST:$BACKEND_PORT/api/v1/system/health" "Backend" 180

echo "Starting frontend on http://$FRONTEND_HOST:$FRONTEND_PORT ..."
(
  cd "$FRONTEND_DIR"
  PUBLIC_API_URL="http://localhost:$BACKEND_PORT" \
    npm run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT"
) >"$LOG_DIR/frontend.log" 2>&1 &
pids+=("$!")

wait_for_http "http://$FRONTEND_HOST:$FRONTEND_PORT/" "Frontend" 60

echo
echo "Anobis is ready."
echo "  Frontend: http://$FRONTEND_HOST:$FRONTEND_PORT/"
echo "  Backend:  http://$BACKEND_HOST:$BACKEND_PORT"
echo "  Health:   http://$BACKEND_HOST:$BACKEND_PORT/api/v1/system/health"
echo
echo "Press Ctrl+C to stop services started by this launcher."

wait
