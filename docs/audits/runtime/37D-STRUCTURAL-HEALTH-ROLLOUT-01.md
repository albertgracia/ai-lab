# 37D-STRUCTURAL-HEALTH-ROLLOUT-01

**Fecha:** 2026-06-12
**Modo:** Rollout runtime controlado
**Precedida por:** 37D-STRUCTURAL-HEALTH-GROUNDING-01 (PASS), 37D-RUNTIME-SMOKE-POST-SCORING-01 (PARTIAL — NOT_DEPLOYED)

---

## Resumen

Despliegue en runtime real del scoring grounded de codebase_health
(modificado en untime/codebase/gitnexus_memory.py, commit 60d501c5).

---

## 1. Preflight

| Check | Resultado |
|-------|-----------|
| git status | limpio ✅ |
| HEAD | 62ce126d == origin/main ✅ |
| Servicio que usa gitnexus_memory.py | Gateway (lazy import en do_GET para /runtime/codebase/*) |
| Gateway inicial | 200 ✅ |
| Router inicial | 200 ✅ |
| Runtime health inicial | 79.6 (warning esperado) ✅ |
| Validation inicial | 75.1 (medium) ✅ |
| Structural health inicial | 20.0 (critical) |

## 2. Rollout

**Acción:** restart de ilab-gateway.service (único servicio que importa untime.codebase.gitnexus_memory).

**Motivo:** Python cachea módulos importados en memoria. El Gateway ya había servido requests a /runtime/codebase con el código viejo. Sin restart, el nuevo código no se cargaría.

**Comando:**
`
sudo systemctl restart ailab-gateway
`

**Rollback plan:**
- Si Gateway falla tras restart: sudo systemctl restart ailab-gateway (systemd lo reinicia automáticamente con StartLimitBurst=6)
- Si el scoring nuevo es incorrecto: revertir untime/codebase/gitnexus_memory.py + restart gateway

## 3. Validación Post-Rollout

| Endpoint | Estado |
|----------|--------|
| Gateway /health | 200 ✅ |
| Router /health | 200 ✅ |
| SLO /health | 200 ✅ |

### Scores

| Métrica | Pre-rollout | Post-rollout | Delta | Resultado |
|---------|-------------|--------------|-------|-----------|
| health_score | 79.6 | 79.6 | 0 | ✅ estable |
| validation_score | 75.1 | 75.1 | 0 | ✅ estable |
| structural_health_score | 20.0 | 48.0 | +28.0 | ✅ mejorado |
| classification | critical | degraded | mejorado | ✅ |

### Nuevos campos disponibles en /runtime/codebase/score

- reakdown.operational_risk_points = 40.0
- reakdown.controlled_debt_points = 12.0
- reakdown.noise_points_excluded = 59
- isk_classification.operational_risk_count = 35
- isk_classification.controlled_debt_count = 27
- isk_classification.noise_count = 59

## 4. GitNexus Post-Rollout

| Check | Resultado |
|-------|-----------|
| GitNexus service | active ✅ |
| Index commit | 62ce126d ✅ |
| MCP list_repos | operativo ✅ |
| MCP query | operativo ✅ |
| dist.rollback-/ excluido | ✅ (20507 nodes, -10495 vs pre-cleanup) |

## 5. Observaciones

1. **structural_health_score 48.0**: mejora sustancial sobre el 20.0 artificial,
   pero aún en nivel  degraded debido a los 93 high_risks + 28 medium_risks reales del codebase.
   No es un falso positivo — refleja la complejidad real del monorepo.

2. **Breakdown operativo**: el nuevo grounded scoring separa riesgo operativo real
   (40 puntos) de deuda controlada (12 puntos) y excluye ruido (59 hallazgos).
   Esto permite priorizar remediation con datos reales.

3. **Watchdog reseteado**: tras restart, triggers_total pasó de 65 a 0 (esperado).

## 6. Veredicto

| Criterio | Estado |
|----------|--------|
| Runtime usa scoring grounded | ✅ |
| Gateway/Router OK | ✅ |
| validation_score no regresa | ✅ (75.1 estable) |
| health_score no regresa | ✅ (79.6 estable) |
| codebase_health refleja fórmula nueva | ✅ (20 → 48, con breakdown) |
| Rollback documentado | ✅ |

**PASS** — rollout completado sin regresiones.
