# Gestión de Datos (Database Schema & Backups) — V2.0

Este documento detalla la arquitectura de datos industrial de **MUSQUERA RAW FACTORY™** y los procedimientos de salvaguarda de la información.

---

## 🏗️ 1. Arquitectura Relacional (Industrial Schema)

La base de datos `raw_factory_db` ha sido extendida para soportar operaciones B2B complejas y auditoría forense.

### `orders` (Capa de Negocio)
- `id`: SERIAL PRIMARY KEY.
- `tracking_id`: TEXT UNIQUE (ID visible para cliente).
- `client_name`: VARCHAR(100).
- `quantity`: INTEGER (Volumen de producción).
- `total_price`: DECIMAL(10,2) (Valor de venta).
- `cost_price`: DECIMAL(10,2) (Coste de fabricación para cálculo de ROI).
- `status`: ['received', 'in_print', 'quality_check', 'shipped'].
- `transport_agency`: VARCHAR(50).
- `transport_tracking`: TEXT.
- `shipping_address`: TEXT.

### `inventory` (Capa Logística)
- `item_name`: Nombre de la prenda base.
- `size` / `color`: Especificaciones de stock.
- `stock_level`: Cantidad disponible.
- `min_threshold`: Nivel crítico para alertas.

### `activity_log` (Trazabilidad Forense)
- Registra cada acción realizada por los operarios (logs de cambio de estado, accesos, etc.) con IP y timestamp.

---

## 💾 2. Copias de Seguridad (Backups)

### Backup Automatizado (PowerShell)
Se ha implementado un script de backup en la ruta:
`d:\DockerContainers\Webs\Musquera RAW LAB\scripts\backup_db.ps1`

**Instrucciones de uso:**
1. Ejecutar el script desde una consola de PowerShell con permisos.
2. El script generará un archivo `.sql` comprimido en la carpeta `./backups/` con el formato `raw_factory_backup_YYYYMMDD_HHMMSS.sql`.

### Backup Manual (Docker)
Para realizar un volcado rápido desde la línea de comandos:
```bash
docker exec -it raw_db_postgres pg_dump -U admin_raw raw_factory_db > backup_manual.sql
```

---

## 🚑 3. Restauración de Datos
En caso de fallo crítico, restaurar el último backup estable:
```bash
docker exec -i raw_db_postgres psql -U admin_raw raw_factory_db < ruta/al/backup.sql
```

---
**MUSQUERA RAW FACTORY™ — INTEGRIDAD DE DATOS GARANTIZADA**
