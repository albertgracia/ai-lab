---
title: "Archive Governance"
summary: "Gobernanza de archives históricos: manifests, exclusiones, semántica de integridad y prevención de recursividad en el runtime."
order: 26
---

## Qué gobierna

- manifests JSON
- recursividad
- exclusiones globales
- tiers de archive
- integridad / confidence del archive

## Por qué importa

Un runtime que observa bien pero archiva mal termina contaminando su propia operación.

Por eso `STORAGE-HARDENING` es prerequisito operacional del baseline 30I.
