# MODEL STRATEGY

Los modelos realmente cargados en cada nodo GPU se listan en el bloque
**HARD FACTS** (sección GPU NODES → Models). Las puntuaciones de
capacidad (0-100) se definen en `runtime/models/model_registry.py`.

## Routing

El router (`runtime/llm/model_router.py`) selecciona modelo según:
1. Nodos online primero.
2. Modelos realmente cargados en LM Studio.
3. Puntuación de capacidad (capability scoring) + rendimiento histórico
   (adaptive scoring).
4. Disponibilidad de VRAM.
5. Fallback al primer modelo disponible del nodo online.

## Router API (:8083)

- ailab-router/auto       → routing automático por capacidad
- ailab-router/fast       → prioriza velocidad (ajuste de temperatura)
- ailab-router/coding     → prioriza generación de código
- ailab-router/reasoning  → prioriza razonamiento profundo

Consulta **HARD FACTS → MODELS PER NODE** para ver qué modelos están
realmente activos en cada GPU.
