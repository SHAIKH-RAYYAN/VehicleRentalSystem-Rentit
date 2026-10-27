#!/bin/bash
# One-command setup + launch. Always run this with: bash run.sh  (or ./run.sh)
# Do NOT run with "sh run.sh" - sh doesn't support "source", it will fail.

cd "$(dirname "$0")" || exit 1

PYTHON=python3
command -v python3 >/dev/null 2>&1 || PYTHON=python

if [ ! -d ".venv" ]; then
    echo "[1/3] Creating virtual environment..."
    "$PYTHON" -m venv .venv || { echo "ERROR: venv creation failed. Is python3-venv installed? Try: sudo apt install python3-venv"; exit 1; }
fi

. .venv/bin/activate

echo "[2/3] Installing dependencies..."
pip install -q -r requirements.txt || { echo "ERROR: pip install failed."; exit 1; }

if [ ! -f "vehicle_rental.db" ]; then
    echo "[3/3] Seeding database..."
    python seed.py || { echo "ERROR: seeding failed."; exit 1; }
fi

echo ""
echo "=========================================="
echo " RentIt running at http://127.0.0.1:5000"
echo " Admin login:    admin@rental.com / admin123"
echo " Customer login: rayyan@example.com / pass123"
echo "=========================================="
echo ""

# Open the browser automatically once the server is up
( sleep 2 && command -v xdg-open >/dev/null 2>&1 && xdg-open http://127.0.0.1:5000 ) &

python app.py
