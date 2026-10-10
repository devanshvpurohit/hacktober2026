#!/usr/bin/env bash
# ==============================================================================
# CircuitForge AI — One-Command Startup Script
# Starts FastAPI backend (port 8000) and Vite frontend (port 5173 if installed)
# Handles graceful shutdown on SIGINT/SIGTERM
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${SCRIPT_DIR}/apps/backend"
FRONTEND_DIR="${SCRIPT_DIR}/apps/frontend"

echo "=================================================================="
echo "          CircuitForge AI — Local IoT Development Studio          "
echo "=================================================================="
echo ""

# 1. Environment Detection
echo "[1/4] Checking local development toolchain..."
if command -v python3 &>/dev/null; then
    echo "  ✓ Python: $(python3 --version)"
else
    echo "  ✗ Python 3 not found! Please install Python 3.11+."
    exit 1
fi

if command -v arduino-cli &>/dev/null; then
    echo "  ✓ Arduino CLI: installed"
else
    echo "  ! Arduino CLI not found in PATH (compilation will be unavailable)."
    echo "    Install via: brew install arduino-cli"
fi

if command -v ollama &>/dev/null; then
    echo "  ✓ Ollama: installed"
else
    echo "  ! Ollama not found. Local AI will fall back to verified catalog rules."
    echo "    Install via: brew install ollama && ollama serve"
fi

if command -v wokwi-cli &>/dev/null; then
    echo "  ✓ Wokwi CLI: installed (automated simulation available)"
else
    echo "  ℹ Wokwi CLI not found. Manual browser simulation via wokwi.com is ready."
fi

# 2. Database & Data Setup
echo ""
echo "[2/4] Initializing local database and storage..."
mkdir -p "${SCRIPT_DIR}/workspace/projects"
mkdir -p "${SCRIPT_DIR}/.arduino15"

export ARDUINO_DIRECTORIES_DATA="${SCRIPT_DIR}/.arduino15"
export ARDUINO_DIRECTORIES_USER="${SCRIPT_DIR}/.arduino15/user"
export ARDUINO_DIRECTORIES_DOWNLOADS="${SCRIPT_DIR}/.arduino15/staging"

python3 -c "
import sys, os
sys.path.insert(0, '${BACKEND_DIR}')
import asyncio
from storage.db import init_db
asyncio.run(init_db())
print('  ✓ SQLite database ready at ${SCRIPT_DIR}/workspace/circuitforge.db')
"

# 3. Process Management Setup
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
    echo ""
    echo "Shutting down CircuitForge AI..."
    if [ -n "${BACKEND_PID}" ] && kill -0 "${BACKEND_PID}" 2>/dev/null; then
        kill "${BACKEND_PID}" 2>/dev/null || true
    fi
    if [ -n "${FRONTEND_PID}" ] && kill -0 "${FRONTEND_PID}" 2>/dev/null; then
        kill "${FRONTEND_PID}" 2>/dev/null || true
    fi
    echo "All processes stopped cleanly. Goodbye!"
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# 4. Start Backend
echo ""
echo "[3/4] Starting FastAPI backend on http://127.0.0.1:8000..."
cd "${BACKEND_DIR}"
python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 --log-level info &
BACKEND_PID=$!

# Wait for backend to be healthy
for i in {1..15}; do
    if curl -s http://127.0.0.1:8000/api/health &>/dev/null; then
        echo "  ✓ Backend is live and healthy on http://127.0.0.1:8000"
        break
    fi
    sleep 0.5
done

# 5. Start Frontend (if node_modules present)
echo ""
echo "[4/4] Checking React frontend..."
if [ -d "${FRONTEND_DIR}/node_modules" ]; then
    echo "Starting Vite dev server on http://localhost:5173..."
    cd "${FRONTEND_DIR}"
    npm run dev &
    FRONTEND_PID=$!
else
    echo "  ℹ Note: apps/frontend/node_modules not yet installed."
    echo "    -> The full dashboard is actively served directly by FastAPI at:"
    echo "       http://127.0.0.1:8000"
    echo ""
    echo "    To run Vite React hot-reloading dev server: cd apps/frontend && npm install && npm run dev"
fi

echo ""
echo "=================================================================="
echo "  CircuitForge AI is running!"
echo "  Web Dashboard:  http://127.0.0.1:8000"
echo "  API Docs:       http://127.0.0.1:8000/docs"
echo "  Press Ctrl+C to stop all services."
echo "=================================================================="

# Keep alive
wait "${BACKEND_PID}"
