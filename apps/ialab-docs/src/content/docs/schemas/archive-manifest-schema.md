---
title: "Archive Manifest Schema"
summary: "Contrato del manifest de archive histórico introducido por STORAGE-HARDENING: trazabilidad, tamaños, exclusiones e integridad."
order: 33
---

## Campos

- `archive_id`
- `source_paths`
- `destination`
- `excluded_paths`
- `recursive_detected`
- `size_before`
- `size_after`
- `confidence`
- `manifest_created_at`

## Propósito

Evitar archive corruption silenciosa y dejar trazabilidad operativa explícita de cada movimiento hacia NAS.
