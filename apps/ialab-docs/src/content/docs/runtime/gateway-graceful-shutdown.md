---
title: "Gateway Graceful Shutdown"
summary: "Manejo de apagado limpio del gateway para evitar SIGKILL por timeout de systemd y rechazar peticiones nuevas de forma controlada durante shutdown."
order: 72
---

# Gateway Graceful Shutdown

## Problema detectado

En reinicios previos, `ailab-gateway` recibia SIGTERM pero no cerraba dentro del timeout de systemd, terminando en SIGKILL.

Sintomas observados en logs:

- `Received signal, shutting down gracefully...`
- `State 'stop-sigterm' timed out. Killing.`
- `Killing process ... with signal SIGKILL`
- `Failed with result 'timeout'`

## Causa probable

Uso de `server.shutdown()` desde el mismo hilo del manejador de señal y salida abrupta (`sys.exit`) antes de cerrar el servidor de forma ordenada.

## Comportamiento implementado

Durante shutdown:

1. Se marca `shutting_down=true` en memoria.
2. Se registran logs operativos de cierre.
3. Nuevas solicitudes (excepto `/health`) reciben `503` controlado.
4. `/health` mantiene `200` para probes, con `status=shutting_down` y `shutting_down=true`.
5. El shutdown del servidor se inicia en hilo daemon separado.
6. Al salir de `serve_forever`, se ejecuta `server_close()` y liberacion de PID lock.

## Logs esperados

- `Received signal, shutting down gracefully...`
- `Gateway shutting_down flag set`
- `Gateway shutdown initiated`
- `Gateway server closing...`
- `Gateway PID lock released: <pid>`
- `Gateway server closed`

## Metricas

- `ailab_gateway_shutdown_rejections_total`: requests rechazadas durante ventana de shutdown.
- `ailab_gateway_clean_shutdown_total`: contador de apagados limpios.

## Validacion operativa

Antes y despues del restart:

```bash
curl -s http://127.0.0.1:8008/health | jq .
curl -s http://127.0.0.1:8008/v1/models | jq .
```

Reinicio manual:

```bash
sudo systemctl restart ailab-gateway
```

Verificar ausencia de timeout/SIGKILL:

```bash
journalctl -u ailab-gateway -n 120 --no-pager
```

No deberia aparecer:

- `State 'stop-sigterm' timed out`
- `signal SIGKILL`
- `Failed with result 'timeout'`

## Rollback

Si se detecta regresion:

1. Revertir commit de esta fase.
2. Reiniciar `ailab-gateway`.
3. Revalidar `/health`, `/v1/models`, `/runtime/health/summary` y logs.
