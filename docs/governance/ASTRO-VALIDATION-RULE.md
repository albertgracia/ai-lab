# ASTRO VALIDATION RULE

**Estado:** CANONICO — Permanente
**Vigencia:** Desde CP-ASTRO-VALIDATION-RULE-01
**Autoridad:** Operador AI-LAB

---

## OBJETIVO

Toda modificación del portal Astro de AI-LAB debe validarse funcionalmente antes de considerar PASS. Un build correcto y un deploy correcto no son suficientes si el contenido visible sigue mostrando información desactualizada.

## REGLA OFICIAL

Una modificación en Astro **NO** podrá considerarse PASS únicamente porque:

- Build PASS
- Deploy PASS
- Tests PASS

## VALIDACIÓN FUNCIONAL OBLIGATORIA

Siempre deberá comprobarse:

### 1. HOME
Debe reflejar claramente los cambios solicitados. No puede seguir mostrando información antigua.

### 2. ARCHITECTURE
Debe representar el estado actual del laboratorio. No puede contener arquitectura obsoleta.

### 3. DOCUMENTATION LANDING
Debe mostrar la nueva organización documental. Las nuevas secciones deben ser visibles.

### 4. ROADMAP
Debe representar únicamente: Implementado, En progreso, Planificado. Sin mezclar fases cerradas con roadmap futuro.

### 5. BLOG
Si la modificación afecta al estado del laboratorio, debe existir la entrada correspondiente.

### 6. PRODUCCIÓN REAL
Debe verificarse la producción real. No únicamente el build local.

| Superficie | URL |
|------------|-----|
| Público | `https://ai-lab.labrazahome.com` |
| Privado | `https://blog-ai-lab.labrazahome.com` (`:4322`) |

### 7. PUBLIC / PRIVATE SEPARATION
Confirmar que PUBLIC_SAFE y PRIVATE_ONLY siguen correctamente separados. El sitio público no debe contener IPs internas, secretos ni contenido PRIVATE_ONLY.

## CRITERIO DE ACEPTACIÓN

Si cualquiera de los puntos anteriores falla:

**RESULTADO = FAIL**

No aceptar PASS.

## CAUSA RAÍZ HISTÓRICA

Durante AI-LAB-ASTRO-DOCS-REFRESH-01 y AI-LAB-ASTRO-CURRENT-STATE-REBUILD-01 se produjeron varios PASS técnicos mientras el sitio visible seguía mostrando contenido antiguo. El build y deploy eran correctos, pero la Home, Architecture y Blog no reflejaban el estado real.

Causa: el sitio Astro tiene dos render paths — `src/pages/` (custom pages) y `src/content/docs/` (Starlight) — que deben actualizarse por separado.

Ver informe completo en `reports/AI-LAB-ASTRO-PUBLIC-PRIVATE-ACTUALIZATION-02.md`.

## INCORPORACIÓN AL WORKFLOW DOCUMENTAL

1. Esta regla es de obligada lectura antes de modificar `apps/ialab-docs/`.
2. El runbook de publicación Astro (`docs/architecture/ASTRO-DEPLOYMENT-GOVERNANCE.md`) debe referenciar esta regla.
3. El archivo `AGENTS.md` debe mantener referencias a esta regla en su sección de Astro Governance.

## ACTUALIZACIÓN

Cada checkpoint importante del laboratorio deberá ejecutar la validación funcional completa antes de declarar PASS.
