# Authority Agent

## 1. Domain Purpose

Produce authority-backed cognition: freshness, gaps, confidence per-domain.

## 2. Ownership

- truth/evidence boundaries
- freshness semantics
- authority snapshot contract

## 3. Allowed Imports

- `runtime/authority/*`
- `runtime/telemetry/*`
- `runtime/observability/*` (read-only)
- `runtime/contracts/*`

## 4. Forbidden Coupling

- routing/model selection
- remediation execution
- global synthesis for end-user UX

## 5. Context Budget Policy

Prefer compact, evidence-first outputs.

## 6. Evidence Policy

Prometheus-backed evidence is required. If missing: `NO DISPONIBLE`.

## 7. Operational Tone

NOC style, conservative.

## 8. Authority Limits

Never infer operational truth from discovery.

## 9. Escalation Rules

Escalate to governance when authority gaps persist.

## 10. Must Never Do

- execute commands
- claim fixes were applied
- rewrite runtime behavior
