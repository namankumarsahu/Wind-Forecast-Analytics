#!/usr/bin/env sh
# Quick check of a running backend:  scripts/smoke_test.sh [http://localhost:8000]
# Hits every endpoint once and fails on the first non-2xx response.
set -eu
BASE="${1:-http://localhost:8000}"

check() {
  printf '%-52s ' "GET $1"
  code=$(curl -sS -o /tmp/smoke_body.json -w '%{http_code}' --max-time 300 "$BASE$1")
  if [ "$code" -ge 200 ] && [ "$code" -lt 300 ]; then echo "$code ok"; else echo "$code FAILED"; head -c 400 /tmp/smoke_body.json; echo; exit 1; fi
}

check /api/health
check /api/config
check "/api/overview?date=2026-01-15"
check "/api/periods?date=2026-01-15"
check "/api/accuracy?start=2026-01-01&end=2026-01-31"
printf '%-52s ' "GET /api/overview?date=2025-12-01 (expect 422)"
code=$(curl -sS -o /dev/null -w '%{http_code}' "$BASE/api/overview?date=2025-12-01")
[ "$code" = "422" ] && echo "422 ok" || { echo "$code FAILED"; exit 1; }
echo "All smoke checks passed."
