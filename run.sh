#!/bin/bash
# ─── BrightHaven Fast Run Script ─────────────────────────────────────────────
cd "$(dirname "$0")"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║        BrightHaven Launcher          ║"
echo "╚══════════════════════════════════════╝"

# ── 1. Install dependencies only if missing (saves 5-10s every run) ───────────
install_if_missing() {
    python -c "import $1" 2>/dev/null || {
        echo "Installing $2..."
        pip install $2 --break-system-packages -q
    }
}

install_if_missing flask         flask
install_if_missing firebase_admin firebase-admin
install_if_missing requests      requests
install_if_missing gunicorn      gunicorn

echo "✓ Dependencies ready"

# ── 2. Find available port ────────────────────────────────────────────────────
PORT=5000
while lsof -Pi :$PORT -sTCP:LISTEN -t &>/dev/null 2>&1; do
    PORT=$((PORT + 1))
done

# ── 3. Export env vars ────────────────────────────────────────────────────────
export FLASK_SECRET_KEY="brighthaven_2026_mk_secure"
export FLASK_APP=app.py
export BLYNK_TOKEN="oMNgTLLthFy33ccjd-3A9fG4889eXd-_"

# ── 4. Network info ───────────────────────────────────────────────────────────
CURRENT_IP=$(ip addr show wlan0 2>/dev/null | grep 'inet ' | awk '{print $2}' | cut -d/ -f1)
[ -z "$CURRENT_IP" ] && CURRENT_IP=$(hostname -I 2>/dev/null | awk '{print $1}')

echo ""
echo "  Local:   http://127.0.0.1:$PORT"
[ -n "$CURRENT_IP" ] && echo "  Network: http://$CURRENT_IP:$PORT"
echo ""

# ── 5. Open browser after 2s ──────────────────────────────────────────────────
(sleep 2 && (xdg-open "http://127.0.0.1:$PORT" || google-chrome "http://127.0.0.1:$PORT") &>/dev/null &) &

# ── 6. Run with Gunicorn (multi-threaded, much faster than Flask dev server) ──
#    4 workers x 4 threads = handles 16 concurrent requests
#    Falls back to plain Flask if gunicorn not available
if command -v gunicorn &>/dev/null; then
    echo "Starting with Gunicorn (production mode)..."
    exec gunicorn app:app \
        --bind 0.0.0.0:$PORT \
        --workers 2 \
        --threads 4 \
        --worker-class gthread \
        --timeout 30 \
        --keep-alive 5 \
        --access-logfile - \
        --error-logfile flask_error.log \
        --preload \
        2>&1
else
    echo "Starting with Flask (dev mode)..."
    python app.py 2>&1 | tee flask_error.log
fi