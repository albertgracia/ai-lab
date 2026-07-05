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

| Componente | Función |
|---:|---|
| `openai_gateway.py` (ailab-gateway) | Entry point OpenAI-compatible: inyección de contexto, routing, perfiles, streaming relay, sanitización |
| `router_api.py` (ailab-router) | API interna (status/perfiles/replay). No es entrypoint de chat en producción |
| `live_api.py` (ailab-live-api) | Estado vivo, embeddings y endpoints internos |
| LM Studio | Inferencia de modelos activos |
| Prometheus / Grafana | Autoridad de métricas + visualización |
| GitNexus | Cognición estructural (codebase truth), solo lectura |

---

# Flujo operativo

```mermaid
flowchart TD
  U[Usuario / Cliente] --> G[Gateway\nOpenAI-compatible]
  G --> R[Route family + reasons\n(det.)]
  R --> P[Apply profile\n(model/tokens/temp/tools/memory)]
  P --> LM[LM Studio\nInferencia]
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
