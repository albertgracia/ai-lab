---
title: "Dependency Risk Analysis"
summary: "Análisis de riesgos estructurales del grafo de dependencias del runtime usando GitNexus."
severity: "medium"
---


## Propósito

Identificar riesgos estructurales en el grafo de dependencias del runtime — high coupling, reverse coupling y authority dependency spread.

## Pasos

### 1. Obtener todos los riesgos estructurales

```bash
curl -s http://192.168.1.30:8008/runtime/codebase/risks | jq '.risks'
```

### 2. Analizar por tipo de riesgo

#### High Coupling

Módulos que importan 5+ otros módulos:

```bash
curl -s http://192.168.1.30:8008/runtime/codebase/risks | jq '.risks[] | select(.risk_type == "high_coupling")'
```

**Implicación**: Estos módulos tienen una superficie amplia y son sensibles a cambios en muchos módulos upstream.

#### High Reverse Coupling

Módulos importados por 5+ otros módulos:

```bash
curl -s http://192.168.1.30:8008/runtime/codebase/risks | jq '.risks[] | select(.risk_type == "high_reverse_coupling")'
```

**Implicación**: Estos módulos son hubs estructurales. Los cambios que rompen compatibilidad se propagan a muchos dependientes.

#### Wide Blast Radius

Módulos que impactan 6+ otros módulos al cambiar:

```bash
curl -s http://192.168.1.30:8008/runtime/codebase/risks | jq '.risks[] | select(.risk_type == "wide_blast_radius")'
```

**Implicación**: Cambios de alto riesgo. Requieren pruebas exhaustivas y despliegue por fases.

### 3. Verificar domain dependency matrix

```bash
curl -s http://192.168.1.30:8008/runtime/codebase/topology | jq '.domain_dependency_matrix'
```

### 4. Calcular risk score

```bash
curl -s http://192.168.1.30:8008/runtime/codebase/score | jq .
```

### 5. Remedición

| Riesgo | Remedición |
|---|---|
| High reverse coupling | Estabilizar interfaces, reducir superficie pública |
| High coupling | Abstraer dependencias, dividir módulo |
| Wide blast radius | Introducir capa de indirección, agregar integration tests |
| Authority spread | Revisar contracts de authority, reducir imports directos |

### 6. Monitorear en el tiempo

Comparar scores entre versiones:

```bash
# Antes del refactor
curl -s http://192.168.1.30:8008/runtime/codebase/score | jq '.score.structural_health_score'

# Después del refactor
curl -s http://192.168.1.30:8008/runtime/codebase/score | jq '.score.structural_health_score'
```

Una mejora sostenida de 10+ puntos valida el refactoring.
