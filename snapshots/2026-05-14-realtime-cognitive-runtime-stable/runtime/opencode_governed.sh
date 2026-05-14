#!/usr/bin/env bash
set -euo pipefail

cd /opt/ai-lab
export PYTHONPATH=/opt/ai-lab

MODE="${1:-readonly}"
shift || true

REQUEST="${*:-}"

if [ -z "$REQUEST" ]; then
  echo "Uso:"
  echo "  runtime/opencode_governed.sh plan \"tu petición\""
  echo "  runtime/opencode_governed.sh readonly \"tu petición\""
  echo "  runtime/opencode_governed.sh build \"tu petición\""
  echo "  runtime/opencode_governed.sh execute \"tu petición\""
  exit 1
fi

python3 - <<PY
from runtime.modes.registry import describe_mode
from runtime.audit.audit_logger import audit_event

mode = "$MODE"
request = """$REQUEST"""

desc = describe_mode(mode)

audit_event(
    "opencode_governed_request",
    {
        "mode": mode,
        "request": request,
        "mode_description": desc,
    }
)

print("AI-LAB GOVERNED OPENCODE")
print("========================")
print("MODE:", mode)
print("CAPABILITIES:", ", ".join(desc["capabilities"]))
print()
PY

PROMPT_FILE="/opt/ai-lab/runtime/opencode/governed_prompt.md"
mkdir -p /opt/ai-lab/runtime/opencode

cat > "$PROMPT_FILE" <<EOF
# AI-LAB GOVERNED OPENCODE SESSION

Mode: $MODE

You must obey the AI-LAB governance mode.

Rules:
- Always answer in Spanish.
- Do not exceed the current mode capabilities.
- In plan mode: only analyze and propose.
- In readonly mode: inspect and diagnose only.
- In build mode: generate or modify code only when explicitly requested.
- In execute mode: privileged actions require explicit confirmation and rollback.
- Never run destructive commands without approval.
- Always separate FACTS from HYPOTHESES.
- Use RAG/memory/context where relevant.

User request:
$REQUEST
EOF

/usr/local/bin/opencode run \
  --dir /opt/ai-lab \
  --model openai/gpt-5.5 \
  -- "$(cat "$PROMPT_FILE")"
