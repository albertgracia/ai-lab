# Credenciales del Proyecto MUSQUERA RAW FACTORY™ — V2.0

Listado de accesos técnicos para el mantenimiento del ecosistema industrial.

---

## 1. Panel de Administración (Operations Center)
- **URL Local:** `http://localhost:92/admin`
- **URL Producción:** `https://musquera-lab.labrazahome.es/admin/`
- **Usuario:** `admin`
- **Contraseña:** `admin` (Cambie inmediatamente después de la primera auditoría).

---

## 2. Base de Datos (PostgreSQL 15)
- **Nombre de DB:** `raw_factory_db`
- **Usuario Maestro:** `admin_raw`
- **Contraseña:** `TU_PASSWORD_SEGURO`
- **Host (Puerto):** `localhost:5432` / Internal: `raw_db_postgres:5432`

---

## 3. Servidor Host (Homelab Environment)
- **Directorio Raíz:** `d:\DockerContainers\Webs\Musquera RAW LAB`
- **Contenedores Docker:** `raw_factory_app`, `raw_db_postgres`.
- **Nginx Proxy Manager**: Encargado de la resolución SSL y Forwarding al puerto 92.

---
**DOCUMENTO DE PROPIEDAD TÉCNICA — MUSQUERA RAW FACTORY**
