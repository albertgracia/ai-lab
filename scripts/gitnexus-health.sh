#!/usr/bin/env bash
set -euo pipefail

HOST="${GITNEXUS_HOST:-127.0.0.1}"
PORT="${GITNEXUS_PORT:-4747}"
BASE="http://${HOST}:${PORT}"

fail() {
  printf 'gitnexus-health: FAIL: %s\n' "$1" >&2
  exit 1
}

json_get() {
  # curl only; keep deps minimal.
  curl -sS -m 3 "$1" || return 1
}

# 1) Health endpoint
health="$(json_get "${BASE}/api/health")" || fail "cannot reach ${BASE}/api/health"
printf '%s\n' "$health" | python3 -c 'import sys,json; d=json.load(sys.stdin); assert d.get("status")=="ok"' \
  || fail "health status != ok"

# 2) Repo stats (nodes/edges > 0)
repos="$(json_get "${BASE}/api/repos")" || fail "cannot reach ${BASE}/api/repos"
python3 - <<'PY' "$repos" || exit 1
import json,sys
data=json.loads(sys.argv[1])
if not isinstance(data,list) or not data:
  raise SystemExit('repos empty')
repo=data[0]
stats=repo.get('stats') or {}
nodes=int(stats.get('nodes') or 0)
edges=int(stats.get('edges') or 0)
if nodes <= 0 or edges <= 0:
  raise SystemExit(f'bad stats nodes={nodes} edges={edges}')
print(f"OK repos=1 nodes={nodes} edges={edges}")
PY

exit 0
