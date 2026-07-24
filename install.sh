#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "==> Iniciando instalador de Martix..."
python3 "$SCRIPT_DIR/installer.py" "$@"
