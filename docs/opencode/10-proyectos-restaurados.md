# PROYECTOS RESTAURADOS — AI-LAB
## 13 de mayo de 2026

---

## Puertos y dominios internos (para Cloudflare Tunnel)

| Proyecto | Dominio interno (Traefik) | Puerto interno | Tipo |
|----------|--------------------------|---------------|------|
| **AGITHome** | `agithome.lab` | 80 | Estática (HTML+CSS+JS) |
| **AGITServices** | `agitservices.lab` | 80 | Estática (HTML+CSS+JS) |
| **AlbertSkills** | `albertskills.lab` | 80 | Estática (HTML+CSS+JS) |
| **AlbertSkillsAMDMulti** | `skills.lab` | 80 | React + Vite (estático) |
| **Calavera LAB** | `calavera.lab` | 80 | Node + Express + Stripe |
| **Musquera RAW LAB** | `musquera.lab` | 80 + 3000 | Node + Express + PostgreSQL |

> **Nota:** No hay puertos expuestos al host. Todo el tráfico entra por Traefik (puertos 80/443 del host) y se enruta internamente. Para Cloudflare Tunnel, apunta todos los dominios a `192.168.1.30:80` (HTTP) o `192.168.1.30:443` (HTTPS).

---

## Arquitectura

```
Internet / Cloudflare Tunnel
        │
        ▼
  ┌─────────────┐
  │  Traefik    │  :80 / :443
  │  (proxy)    │
  └──────┬──────┘
         │
         ├── agithome.lab      → nginx → /agithome/
         ├── agitservices.lab  → nginx → /agitservices/
         ├── albertskills.lab  → nginx → /albertskills/
         ├── skills.lab        → nginx → /albertskills-amd-multi/dist/
         ├── calavera.lab      → Node Express → server.js + Stripe API
         └── musquera.lab      → nginx (frontend)
                                  │
                                  └── /api/* → musquera-server:3000
                                                    │
                                                    └── postgres:5432
```

---

## Stack por proyecto

### AGITHome
- **Ruta:** `/opt/ai-lab/stacks/websites/agithome/`
- **Servicio:** `agithome` (nginx:alpine)
- **Dominio sugerido:** `agithome.tudominio.com`

### AGITServices
- **Ruta:** `/opt/ai-lab/stacks/websites/agitservices/`
- **Servicio:** `agitservices` (nginx:alpine)
- **Dominio sugerido:** `agitservices.tudominio.com`

### AlbertSkills
- **Ruta:** `/opt/ai-lab/stacks/websites/albertskills/`
- **Servicio:** `albertskills` (nginx:alpine)
- **Dominio sugerido:** `albertskills.tudominio.com`

### AlbertSkillsAMDMulti (React)
- **Ruta:** `/opt/ai-lab/stacks/websites/albertskills-amd-multi/`
- **Servicio:** `albertskills-amd-multi` (nginx:alpine)
- **Build:** `cd /opt/ai-lab/stacks/websites/albertskills-amd-multi && npm install && npm run build`
- **Dominio sugerido:** `skills.tudominio.com`

### Calavera LAB
- **Ruta:** `/opt/ai-lab/stacks/websites/calavera-lab/`
- **Servicio:** `calavera-lab` (Node 24 + Express + Stripe)
- **Puerto interno:** 80
- **Dependencias:** Stripe API keys (ya en `.env`)
- **⚠️ Claves Stripe expuestas:** Rotar `sk_live_*` y `pk_live_*` antes de producción
- **Dominio sugerido:** `calavera.tudominio.com`

### Musquera RAW LAB
- **Ruta:** `/opt/ai-lab/stacks/websites/musquera-raw/`
- **Servicios:**
  - `musquera-web` (nginx) — frontend estático + proxy reverso a API
  - `musquera-server` (Node 18) — API Express + JWT + PostgreSQL
  - `musquera-db` (PostgreSQL 15) — base de datos
- **Puerto interno:** 80 (web) + 3000 (API) + 5432 (DB interna, no expuesta)
- **DB:** `raw_factory_db`, usuario: `admin_raw`
- **Dominio sugerido:** `musquera.tudominio.com`

---

## Volúmenes Docker

| Volumen | Propósito |
|---------|-----------|
| `musquera-db-data` | Datos persistentes de PostgreSQL |
| `musquera-uploads` | Archivos subidos (imágenes, etc.) |

---

## Comandos de gestión

```bash
# Ver estado
docker ps | grep -E "agithome|agitservices|albertskills|calavera|musquera"

# Logs
docker logs agithome --tail 20
docker logs calavera-lab --tail 50
docker logs musquera-server --tail 50
docker logs musquera-db --tail 20

# Reiniciar un proyecto
docker compose -f /opt/ai-lab/stacks/websites/docker-compose.yml up -d <servicio>
docker compose -f /opt/ai-lab/stacks/websites/docker-compose.backend.yml up -d <servicio>

# Reconstruir (tras cambios en código)
docker compose -f /opt/ai-lab/stacks/websites/docker-compose.backend.yml build
docker compose -f /opt/ai-lab/stacks/websites/docker-compose.backend.yml up -d

# Parar todo
docker compose -f /opt/ai-lab/stacks/websites/docker-compose.yml down
docker compose -f /opt/ai-lab/stacks/websites/docker-compose.backend.yml down

# Backup DB (Musquera)
docker exec musquera-db pg_dump -U admin_raw raw_factory_db > /opt/ai-lab/snapshots/musquera-db-$(date +%Y%m%d).sql
```

---

## Para Cloudflare Tunnel

Cuando tengas los dominios públicos, actualiza las reglas en Traefik editando las labels en los docker-compose:

```yaml
# Cambiar de:
- "traefik.http.routers.agithome.rule=Host(`agithome.lab`)"
# a:
- "traefik.http.routers.agithome.rule=Host(`agithome.tudominio.com`)"
```

O crea archivos en `/opt/ai-lab/data/traefik/dynamic/` con las reglas TLS/SSL si usas HTTPS.
