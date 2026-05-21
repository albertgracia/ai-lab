## FASE 30I-C: Sensor Summary Exposure - COMPLETED

### Objetivo
Hacer que las respuestas operacionales cortas y específicas (ej. `estado GPU RX9070`) utilicen directamente los datos vivos del Runtime Sensor Fusion (FASE 30I/30I-B) en vez de limitarse al inventario clásico de `inference_nodes`.

### Cambios realizados
1. **`runtime/context/sensor_fusion.py`**:
   - Añadida función `build_gpu_operational_summary()` que construye resúmenes compactos de GPU con métricas reales de temperatura, potencia, carga, fan y VRAM.
   - Prioriza métricas vivas sobre inventario estático y evita raw metric flood.

2. **`runtime/context/report_runtime_context.py`**:
   - Integrado `gpu_operational_summaries` dentro de `OBSERVED_RUNTIME` y del bloque `sensor_snapshot`.
   - Los resúmenes GPU se exponen como contexto compacto para respuestas operacionales.

3. **`runtime/gateway/tool_request_classifier.py`**:
   - Añadidos `GPU_RUNTIME_INTENT_PATTERNS`.
   - Añadida función `detect_gpu_runtime_intent()` para priorizar sensor fusion en consultas GPU cortas.

4. **`tests/test_runtime_sensor_summary_30ic.py`**:
   - Creada suite de 11 tests para validar resúmenes GPU compactos, grounding, priorización sobre `inference_nodes` y semántica `expected_offline` de RX7900XT.

### Completado
- Compact GPU summaries.
- Live metrics prioritization.
- Short GPU prompt grounding.
- Validación qwen / llama.
- Semántica RX7900XT `inventory/offline` y `expected_offline`.
- Integración con sensor fusion.
- No raw metric flood.
- No silent fallback to `inference_nodes` en consultas GPU cortas.

### Validación
- `tests/test_runtime_sensor_summary_30ic.py`: 11/11 PASS.
- `tests/test_runtime_sensor_fusion_30i.py`: 54/54 PASS.
- Total: 65/65 PASS.

### Validación operativa
- RX9070 grounded con métricas vivas.
- RX7900XT conservado como `inventory/offline`, no activo, no routable, sin métricas inventadas.
- `gpu_summary` operativo presente.
- `domain_confidence` presente.

### Semantic Gaps Conocidos
- `freshness` exposure parcial.
- `source_of_truth` exposure parcial.
- `confidence` propagation no completamente normalizada.
- `/runtime/sensors` no expone todavía todos los campos finos de `gpu_operational_summaries`.

30I-C se considera funcionalmente cerrada.
Los gaps restantes son de normalización semántica y no bloquean el grounding operacional.

### Artefactos generados
- `/tmp/30ic-gpu-summary-samples.json`
- `/tmp/30ic-summary.md`
- `/tmp/30ic-burnin-report.json`

### Checkpoint
- Commit: `da99da92`
- Tag: `CP-30I-C-SENSOR-SUMMARY-EXPOSURE-STABLE`

### Resumen final
- `build_gpu_operational_summary()` implementado.
- `gpu_operational_summaries` integrado en `OBSERVED_RUNTIME`.
- `detect_gpu_runtime_intent()` añadido.
- Consultas GPU cortas priorizan sensor fusion sobre `inference_nodes`.
- RX9070 expone métricas vivas.
- RX7900XT queda como `inventory/offline`.
- `source_of_truth`, `freshness` y `confidence` incorporados en el diseño, con exposición parcial conocida en runtime vivo.
- Checkpoint histórico preservado: `CP-30I-C-SENSOR-SUMMARY-EXPOSURE-STABLE`.
