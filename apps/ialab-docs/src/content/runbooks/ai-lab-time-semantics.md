---
title: "AI-LAB Time Semantics"
summary: "Doctrina temporal: UTC canónico interno + Europe/Madrid para presentación operativa. Riesgos del drift y validación NTP."
---


## Doctrina

RUNTIME (canónico):

- **UTC** para timestamps internos.

PRESENTACIÓN (operador):

- **Europe/Madrid** para UI y comunicación humana.

## Reglas

- Logs: UTC.
- Telemetry (Prometheus): UTC.
- Grafana: TZ local en UI.
- Incidents: UTC canónico + rendering localizado.
- `runtime/state/*`: UTC (estado vivo; nunca se commitea).

## Riesgos del drift

- Corrupción de freshness (authority/precision): `fresh` vs `stale` incorrecto.
- Cronología de incidentes inválida.
- Correlación burn-in falsa.
- Paneles Grafana desfasados.

## Validación (host)

```bash
timedatectl status
date
```

Esperado:

- `Time zone: Europe/Madrid`
- `System clock synchronized: yes`
- `NTP service: active`

## Backend NTP

En este host el servicio NTP puede ser `chrony` (systemd-timesyncd no siempre está instalado):

```bash
systemctl status chrony --no-pager
```
