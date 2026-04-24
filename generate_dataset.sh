#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# SchemaGuard — Dataset Generation Launcher
# ─────────────────────────────────────────────────────────────────────────────
# Usage:
#   ./generate_dataset.sh                  # generate both domains
#   ./generate_dataset.sh --domain hc      # healthcare only
#   ./generate_dataset.sh --domain fn      # finance only
#   ./generate_dataset.sh --dry-run        # preview plan, no API calls
#
# Setup (one-time):
#   1. Copy .env.example to .env
#   2. Set ANTHROPIC_API_KEY=sk-ant-... in .env
#   3. chmod +x generate_dataset.sh && ./generate_dataset.sh
# ─────────────────────────────────────────────────────────────────────────────

set -e
cd "$(dirname "$0")"

PYTHON=/opt/homebrew/bin/python3.12

# ── load .env if present ──────────────────────────────────────────────────────
if [ -f .env ]; then
  echo "→ Loading .env"
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

# ── check key ────────────────────────────────────────────────────────────────
if [ -z "$ANTHROPIC_API_KEY" ] && [[ "$*" != *"--dry-run"* ]]; then
  echo ""
  echo "ERROR: ANTHROPIC_API_KEY not set."
  echo ""
  echo "Quick setup:"
  echo "  1. cp .env.example .env"
  echo "  2. Edit .env and set ANTHROPIC_API_KEY=sk-ant-..."
  echo "  3. Re-run this script"
  echo ""
  echo "Or run a dry-run (no API key needed):"
  echo "  ./generate_dataset.sh --dry-run"
  echo ""
  exit 1
fi

# ── check python ──────────────────────────────────────────────────────────────
if [ ! -f "$PYTHON" ]; then
  PYTHON=$(which python3)
fi

echo "→ Python: $PYTHON ($($PYTHON --version 2>&1))"

# ── check dependencies ────────────────────────────────────────────────────────
$PYTHON -c "import anthropic, jsonschema" 2>/dev/null || {
  echo "→ Installing dependencies..."
  $PYTHON -m pip install anthropic jsonschema --break-system-packages --quiet
}

# ── run generator ─────────────────────────────────────────────────────────────
echo "→ Starting generation..."
echo ""
$PYTHON data_gen/generate_full_dataset.py "$@"
