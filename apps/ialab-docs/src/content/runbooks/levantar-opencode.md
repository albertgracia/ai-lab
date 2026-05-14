---
title: "Levantar OpenCode"
summary: "Cómo iniciar y conectar OpenCode con el gateway."
---

## Requisitos

Gateway corriendo en \`:8008\` (systemd: \`ailab-gateway.service\`).
Router corriendo en \`:8083\` (systemd: \`ailab-router.service\`).
Heartbeat corriendo (systemd: \`ailab-heartbeat.service\`).

## Uso

\`\`\`bash
# Lanzar con contexto completo del AI-LAB
opencode-ialab "describe el estado del cluster"

# O manualmente
opencode run --dir /opt/ai-lab --model lmstudio/qwen3-14b-claude-sonnet-4.5-reasoning-distill -- "tu consulta"
\`\`\`

## Conexión directa al gateway

\`\`\`bash
curl http://localhost:8008/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer lm-studio" \
  -d '{"model": "auto", "messages": [{"role": "user", "content": "Hola"}]}'
\`\`\`
