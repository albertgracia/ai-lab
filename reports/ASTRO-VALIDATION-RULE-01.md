# ASTRO-VALIDATION-RULE-01

**Fecha:** 2026-07-06
**Checkpoint:** CP-ASTRO-VALIDATION-RULE-01
**Commit:** (pending)

## Resumen

Implementación de la regla permanente de validación funcional para toda modificación del portal Astro de AI-LAB. Creación de la página pública "Estado del Laboratorio". Actualización de procedimientos documentales.

## Archivos creados

| Archivo | Propósito |
|---------|-----------|
| `docs/governance/ASTRO-VALIDATION-RULE.md` | Regla permanente de validación funcional |
| `apps/ialab-docs/src/pages/status/index.astro` | Página pública "Estado del Laboratorio" |
| `reports/ASTRO-VALIDATION-RULE-01.md` | Este informe |

## Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `apps/ialab-docs/src/pages/index.astro` | Añadido enlace a /status/ |
| `apps/ialab-docs/src/layouts/Layout.astro` | Añadido "Estado del LAB" en sidebar |
| `docs/architecture/ASTRO-DEPLOYMENT-GOVERNANCE.md` | Añadida sección de validación funcional |
| `AGENTS.md` | Añadida regla 11 al Astro Governance |

## Validación

### Build privado: 281 páginas, 0 errores
### Build público: 144 páginas, 0 IPs, 0 errores

### Página Estado del Laboratorio

- ✅ Aparece en Home (`/` → enlace "Estado del Laboratorio")
- ✅ Aparece en Sidebar (Layout.astro → "Estado del LAB")
- ✅ Aparece en búsqueda (Pagefind indexado)
- ✅ Build público PASS (0 errores, 0 IPs)
- ✅ Build privado PASS (0 errores)

### Contenido de la página

- Estado general con 10 componentes (todos 🟢 Operativo)
- Próxima fase: "Hermes E08 — Lifecycle Hooks"
- Último checkpoint, commit y fecha de actualización
- Sección de builds (público 144, privado 281 páginas)

## Regla documentada

La regla ASTRO-VALIDATION-RULE queda incorporada en:

1. `docs/governance/ASTRO-VALIDATION-RULE.md` — documento canónico
2. `docs/architecture/ASTRO-DEPLOYMENT-GOVERNANCE.md` — sección de validación funcional
3. `AGENTS.md` — regla 11 del Astro Governance

## Tags

- `CP-ASTRO-VALIDATION-RULE-01`
