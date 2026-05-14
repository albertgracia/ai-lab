#!/usr/bin/env bash
set -euo pipefail

cd /opt/ai-lab
export PYTHONPATH=/opt/ai-lab

python3 runtime/state/system_state.py > /dev/null
mkdir -p runtime/opencode
python3 runtime/opencode_context.py > runtime/opencode/context.md
cp runtime/opencode/context.md OPENCODE.md

export OPENCODE_SERVER_PASSWORD="${OPENCODE_SERVER_PASSWORD:-ailab}"

/usr/local/bin/opencode web \
  --hostname 0.0.0.0 \
  --port 4096
