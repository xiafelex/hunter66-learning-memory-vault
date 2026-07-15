#!/bin/zsh
set -euo pipefail

APP_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec "$APP_ROOT/.venv/bin/python" "$APP_ROOT/server.py"
