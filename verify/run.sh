#!/usr/bin/env bash
# One-shot verification: tests + build + live API smoke. Exits non-zero on
# the first failed stage so the container's exit code reports success.
set -euo pipefail

echo "== [1/3] backend unit tests =="
cd /app/backend
python -m pytest tests/ -q

echo "== [2/3] frontend production build =="
cd /app/frontend
npm run build

echo "== [3/3] live API smoke test against ${BACKEND_URL:-http://backend:8000} =="
cd /app/verify
python smoke.py

echo "== verify: ALL STAGES PASSED =="
