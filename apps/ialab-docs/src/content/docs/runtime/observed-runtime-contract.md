---
title: "Observed Runtime Contract"
summary: "Contrato cognitivo de OBSERVED_RUNTIME: qué incluye, cómo se construye y por qué es la interfaz entre sensores, governance y respuesta LLM."
order: 15
---

## Qué es

`OBSERVED_RUNTIME` es el contrato cognitivo que resume el estado operativo real del runtime para el LLM.

No es un dump libre. Es una interfaz deliberadamente compacta y evidence-bound.

## Componentes principales

- `runtime_identity`
- `primary_runtime_ip`
- `target_runtime_match`
- `sensor_snapshot`
- `gpu_operational_summaries`
- `runtime_topology`
- `domain_confidence`
- `source_quality`
- `evidence_catalog`
- `data_quality`

## Principio de diseño

El LLM no debería decidir qué creer. El runtime le entrega:

- qué es observado
- qué es derivado
- qué es inventario
- con qué fuente
- con qué frescura
- con qué confianza

## Relación con 30H

30H impone disciplina epistemológica.
30I añade evidencia observada.
30I-D normaliza el contrato.

El resultado es un runtime que no solo sabe más, sino que sabe **cómo sabe**.
