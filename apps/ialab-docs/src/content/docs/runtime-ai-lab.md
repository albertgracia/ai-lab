---
title: "Runtime AI-LAB"
summary: "Arquitectura runtime real: gateway entrypoint, routing determinista, profiles, fastpath, authority, precision y truth layers."
order: 5
---

El runtime constituye el núcleo operativo del laboratorio.

Gestiona:

- inferencia (vía gateway)
- routing determinista (route family + reasons)
- perfiles cognitivos (apply_profile)
- fastpath operacional
- autoridad y precisión (safety semántico)
- observabilidad (métricas + sensor fusion)
- truth layers (Prometheus / OperationalTruth / GitNexus)

Arquitectura clave (separación explícita):

- **LM Studio**: backend de inferencia (sirve `/v1/*` y gestiona modelos en VRAM). No aplica governance.
- **AI-LAB Gateway**: control plane cognitivo y plano de gobernanza (routing, perfiles, evidence/precision, federation guards, métricas, APIs runtime).
- **GitNexus**: inteligencia topológica del codebase (estructura, hotspots, blast radius, gravity centers) usada como señal de razonamiento bounded.
- **Prometheus/Grafana**: autoridad observacional (métricas, alertas, dashboards). No “razonan”; miden.

---

# Componentes principales

| Componente | Puerto | Función |
|---|---:|---|
| `openai_gateway.py` (ailab-gateway) | 8008 | Entry point OpenAI-compatible: inyección de contexto, routing, perfiles, streaming relay, sanitización |
| `router_api.py` (ailab-router) | 8083 | API interna (status/perfiles/replay). No es entrypoint de chat en producción |
| `live_api.py` (ailab-live-api) | 8084 | Estado vivo, embeddings y endpoints internos |
| LM Studio (RX9070) | 1234 | Inferencia de modelos activos |
| Prometheus / Grafana | 9090 / 3000 | Autoridad de métricas + visualización |
| GitNexus | 4747 | Cognición estructural (codebase truth), solo lectura |

---

# Flujo operativo

```mermaid
flowchart TD
  U[Usuario / Cliente] --> G[Gateway :8008\nOpenAI-compatible]
  G --> R[Route family + reasons\n(det.)]
  R --> P[Apply profile\n(model/tokens/temp/tools/memory)]
  P --> LM[LM Studio :1234\nRX9070]
  LM --> G
  G --> U

  subgraph Truth[Truth Layers]
    PROM[Prometheus (Authority)] --> OT[OperationalTruth\n(sensor fusion, maturity, topology)]
    GN[GitNexus (Structural)] --> OT
  end

  PROM --> G
  OT --> G
```

Notas:

- La selección de modelo/ruta es determinista. El LLM no decide el routing.
- Discovery no implica operational: active/loaded/discoverable/disabled se mantienen separados.
- Fastpath es compacto y evidence-bound.
