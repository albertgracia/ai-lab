---
title: "Evidence-Bound Reporting: cómo AI-LAB evita inventar su propio estado"
description: "Cuando un LLM genera informes sobre su propio runtime, la tentación de rellenar con datos plausibles es máxima. Así implementamos un evidence guard para evitarlo."
summary: "AI-LAB implementó un evidence guard que impide que los reportes del LLM contengan afirmaciones no verificadas sobre GPUs, modelos, hosts o plataformas externas."
date: "2026-05-21"
tags:
  - ai-lab
  - evidence
  - hallucination
  - reporting
  - governance
---

# Evidence-Bound Reporting: cómo AI-LAB evita inventar su propio estado

## El informe que inventó una NVIDIA A100

Un usuario pidió un informe operacional del laboratorio. El LLM, con acceso al estado del runtime, respondió impecablemente... y añadió de su cosecha:

> "La GPU NVIDIA A100-80GB gestiona cargas de inferencia..."

El problema: el laboratorio no tiene ninguna NVIDIA. Tiene una AMD RX9070. Y otra AMD RX7900XT apagada.

El LLM no mintió deliberadamente. Simplemente hizo lo que mejor sabe hacer: completar el patrón. "GPU + informe operacional = NVIDIA A100". Es un sesgo de training data, no una intención maliciosa.

Pero para un runtime que debe reportar su estado con precisión, eso es un fallo grave.

## El problema de los informes LLM

Los generadores de lenguaje son máquinas estadísticas. Cuando falta información, la "rellenan" con lo más probable. En el contexto de GPUs, lo más probable en el training data es NVIDIA. En el contexto de modelos, GPT-4 o Claude. En el contexto de cloud, AWS.

Para un informe operacional, esto produce:

- GPUs inexistentes (A100, H100, H200)
- Modelos no cargados (GPT-4, Claude, Gemini)
- Herramientas de seguridad no instaladas (SELinux, AppArmor, Falco)
- Plataformas externas no utilizadas (AWS, GCP, Azure)
- Porcentajes y latencias inventadas
- Versiones de software incorrectas
- Nombres de host y puertos equivocados

## La solución: evidencia observada vs. LLM generado

AI-LAB construye un **catálogo de evidencia** en tiempo real. Antes de que el LLM genere un reporte, el runtime inyecta `OBSERVED_RUNTIME`: un snapshot JSON con TODO lo que el runtime sabe de sí mismo.

Luego, después de que el LLM genere el reporte, un **evidence guard** post-hoc escanea el texto en busca de afirmaciones no verificadas.

### Capa 1: Prevención (prompt)

El system prompt del reporte incluye RULE-30H:

```
- No inventes GPUs, modelos, hosts, puertos, versiones ni servicios
- Si un dato no aparece en OBSERVED_RUNTIME, responde NO DISPONIBLE
- No menciones herramientas de seguridad o plataformas externas no observadas
```

### Capa 2: Sanitización (código)

El evidence guard analiza la respuesta del LLM contra el catálogo de evidencia:

```python
def sanitize_unverified_claims(text, evidence_catalog):
    claims = find_unverified_claims(text, evidence_catalog)
    if claims:
        text += "\n\n[EVIDENCE GUARD]\n" + \
                "Afirmaciones no verificadas detectadas:\n" + \
                "\n".join(f"- {c}" for c in claims)
    return text
```

### Capa 3: Hallucination risk score

Cada afirmación no verificada reduce el score:

```
evidence_score = 1.0 - (0.15 × unverified_claims)
```

Con 0 claims: score = 1.0 (confiable)
Con 3 claims: score = 0.55 (dudoso)
Con 5+ claims: score ≤ 0.25 (hallucination_risk = HIGH)

## Las denylists

No usamos NLP ni regex complejos. Usamos 6 listas explícitas de términos:

| Denylist | Ejemplos | Razón |
|----------|----------|-------|
| PROHIBITED_MODELS | gpt-4, claude-3, gemini-1.5 | Modelos cloud no disponibles |
| UNOBSERVED_GPUS | a100, h100, mi300x | GPUs que no existen en el laboratorio |
| SECURITY_TOOLS | selinux, apparmor, falco | Herramientas no instaladas |
| EXTERNAL_PLATFORMS | aws, gcp, azure | Plataformas cloud no utilizadas |
| UNKNOWN_MODELS | patrones "v1", "2.0" | Modelos no observados en runtime |
| UNKNOWN_HOSTS | IPs fuera de 192.168.1.x | Hosts que no están en topología |

## Por qué esto importa para operaciones reales

Un informe operacional que afirma tener una A100 cuando tiene una RX9070 no es un error menor. Es un fallo de confianza. Si el runtime no puede reportar su propio hardware correctamente, ¿cómo va a gestionar:

- Decisiones de enrutamiento entre nodos?
- Asignación de carga según capacidad GPU?
- Diagnóstico de fallos?
- Planificación de capacidad?

La evidencia observada es la base de cualquier operación confiable.

## Lo que logramos

- 34 tests de evidence guard
- Burn-in adversarial con 10 escenarios de alucinación
- 4 de 4 refusals en report routes cuando faltaba evidencia
- El evidence guard se activa correctamente y marca las afirmaciones no verificadas
- Gap detectado: cognitive routes no están protegidas (pendiente de expandir)

## La lección

No le preguntes a un LLM qué GPU tienes. Pregúntale a tu runtime. Y si el LLM insiste en responder, asegúrate de que tu runtime tenga un guard que le corrija la respuesta.

En AI-LAB, el runtime no alucina. El LLM puede intentarlo, pero el evidence guard no le deja.
