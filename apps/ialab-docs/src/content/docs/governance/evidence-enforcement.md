---
title: "Evidence Enforcement (FASE 30H)"
summary: "Runtime Evidence Enforcement: catálogo de evidencia, strict evidence mode, MAX_UNVERIFIED_CLAIMS, denylists, supresión de alucinaciones y métricas."
order: 10
---

## Objetivo

Evitar que los reportes generados por el LLM inventen hardware, modelos, métricas o servicios no observados por el runtime. Ningún informe técnico debe contener afirmaciones sin respaldo en `OBSERVED_RUNTIME`.

## Problema

Antes de FASE 30H, el LLM podía generar reportes que mencionaban:

- GPUs no existentes en el laboratorio (NVIDIA A100, H100)
- Modelos no cargados (GPT-4, Claude)
- Herramientas de seguridad no instaladas (SELinux, AppArmor)
- Plataformas externas no utilizadas (AWS, GCP, Azure)
- Hosts y puertos incorrectos
- Porcentajes y latencias inventadas

## Solución: Evidence Guard

### Arquitectura

```
runtime/context/evidence_guard.py
├── build_evidence_catalog()
├── sanitize_unverified_claims()
├── ReportEvidenceResult
├── STRICT_EVIDENCE_MODE (env AI_LAB_STRICT_EVIDENCE_MODE)
└── MAX_UNVERIFIED_CLAIMS = 5
```

### Catálogo de evidencia

`build_evidence_catalog()` construye un snapshot JSON del runtime con 6 categorías:

| Categoría | Fuente |
|-----------|--------|
| Modelos activos | Model state runtime |
| Nodos de inferencia | Runtime topology / inference_nodes |
| GPUs observadas | runtime_state |
| Hosts observados | runtime_state + topology |
| Métricas disponibles | runtime_state |
| Perfiles activos | profile_manifest |

### Denylists

Seis listas de términos explícitos que el evidence guard escanea:

| Denylist | Ejemplos |
|----------|----------|
| PROHIBITED_MODELS | gpt-4, gpt-4-turbo, claude-3, claude-3.5, gemini-1.5, gemini-2.0, llama-3-70b, llama-4 |
| UNOBSERVED_GPUS | a100, a100-80gb, h100, h200, b200, mi250, mi300x, t4, l4, l40s, v100, p100 |
| SECURITY_TOOLS | selinux, apparmor, falco, tripwire, ossec, aide, rkhunter, chkrootkit, snort, suricata |
| EXTERNAL_PLATFORMS | aws, amazon web services, google cloud, gcp, azure, microsoft azure, oracle cloud, oci, ibm cloud, digitalocean, hetzner, linode, vultr, kubernetes, k8s, docker swarm, openshift, terraform cloud |
| UNKNOWN_MODELS | patrones no observados que contienen "/" o números de versión tipo "v1", "2.0" |
| UNKNOWN_HOSTS | IPs y hostnames que no aparecen en runtime_state o topology |

### Strict Evidence Mode

- `STRICT_EVIDENCE_MODE=true` (default): sanitiza automáticamente las afirmaciones no verificadas
- `STRICT_EVIDENCE_MODE=false`: emite warnings sin sanitizar (para depuración)

Configurable vía env `AI_LAB_STRICT_EVIDENCE_MODE`.

### MAX_UNVERIFIED_CLAIMS

- Límite: 5 afirmaciones no verificadas
- Al superarlo: `hallucination_risk = high`
- Evidence score: `1.0 - (0.15 × unverified_claims)`
- Con 5 claims: score = 0.25 → hallucination_risk = high

### Sanitización post-hoc

El evidence guard NO modifica el prompt del LLM. Actúa como segunda línea de defensa:

1. El LLM genera el reporte con RULE-30H en el system prompt (prevención)
2. Evidence guard analiza la respuesta post-hoc (sanitización)
3. Si detecta afirmaciones no verificadas, añade sección `[EVIDENCE GUARD]` con la lista

### Integración en gateway

```
openai_gateway.py
└── inject_agent_context()
    └── _report_runtime_context (payload)
        → tool_request_classifier.py
            → sanitize_report_output(runtime_context_json)
                → evidence_guard.sanitize_unverified_claims()
```

Solo se activa para route_family `report` o `minimal` cuando `_report_runtime_context` está presente.

## Endpoint: /runtime/reports/evidence

Always-on 200. Devuelve:

```json
{
  "evidence_catalog": {
    "models": ["llama-3.1-8b-instruct", "qwen2.5-coder-14b-instruct", "nomic-embed-text-v1.5"],
    "inference_nodes": [{"host": "192.168.1.50", "port": 1234, "gpu": "RX9070"}],
    "gpus": ["RX9070"],
    "hosts": ["192.168.1.30", "192.168.1.40", "192.168.1.50"],
    "metrics_available": 112,
    "profiles_active": ["minimal", "report", "coding", "chat", "observe", "analysis", "creative", "agent"]
  },
  "strict_evidence_mode": true,
  "max_unverified_claims": 5,
  "phase": "30H"
}
```

## Métricas Prometheus (4 nuevas)

| Métrica | Tipo | Descripción |
|---------|------|-------------|
| ailab_report_evidence_guard_total | Counter | Ejecuciones del evidence guard |
| ailab_report_unverified_claim_total | Counter | Afirmaciones no verificadas detectadas |
| ailab_report_evidence_score | Histogram | Evidence score (0.0-1.0) |
| ailab_report_hallucination_suppressed_total | Counter | Alucinaciones suprimidas |

## Gap conocido

El evidence guard solo se ejecuta para rutas `report`/`minimal`. Las rutas `cognitive` pueden generar alucinaciones no detectadas. Pendiente de expandir a todas las rutas en fase futura.

## Checkpoint

**CP-30H-RUNTIME-EVIDENCE-ENFORCEMENT-STABLE** — implementación completa con 34 tests y burn-in adversarial validado.
