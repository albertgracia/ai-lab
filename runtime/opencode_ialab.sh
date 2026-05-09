#!/usr/bin/env bash
set -euo pipefail

cd /opt/ai-lab
export PYTHONPATH=/opt/ai-lab

mkdir -p /opt/ai-lab/runtime/opencode

python3 runtime/state/system_state.py > /dev/null

CONTEXT_FILE="/opt/ai-lab/runtime/opencode/context.md"
PROMPT_FILE="/opt/ai-lab/runtime/opencode/prompt.md"

python3 runtime/opencode_context.py > "$CONTEXT_FILE"

REQUEST="${*:-}"

if [ -z "$REQUEST" ]; then
  echo "Uso: opencode-ialab \"tu petición\""
  exit 1
fi

cat > "$PROMPT_FILE" <<EOF
Lee el contexto operativo del AI-LAB en este archivo:

$CONTEXT_FILE

Después responde a esta petición:
$REQUEST

Reglas:
- No modifiques nada salvo autorización explícita.
- Responde en español.
- Usa el contexto como fuente de verdad.
EOF

/usr/local/bin/opencode run \
  --dir /opt/ai-lab \
  --model lmstudio/qwen3-14b-claude-sonnet-4.5-reasoning-distill \
  -- "$(cat "$PROMPT_FILE")"
