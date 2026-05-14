# Musquera RAW LAB — Documentación del proyecto
## Plataforma B2B de merchandising industrial

---

## 1. Descripción
**Musquera RAW FACTORY** es una plataforma B2B completa para gestión de pedidos de merchandising industrial (serigrafía, DTF, bordado). Incluye panel de administración React, backend Node.js con autenticación JWT, base de datos PostgreSQL y generación de cotizaciones.

## 2. Stack tecnológico

| Componente | Tecnología |
|------------|-----------|
| Frontend público | HTML5 + CSS3 + Vanilla JS |
| Panel admin | React 19 + Vite |
| Backend API | Node 18 + Express 4 |
| Base de datos | PostgreSQL 15 |
| Autenticación | JWT + bcrypt + HttpOnly cookies |
| Archivos | Multer (upload de imágenes) |
| Servidor web | nginx:alpine (proxy inverso) |
| Proxy | Traefik (AI-LAB) |
| SEO | Sitemap dinámico con compresión Gzip |

## 3. Arquitectura
```
Usuario → Cloudflare Tunnel → 192.168.1.30:80 → Traefik
                                                    ↓
                                       Host: musquera.labrazahome.com
                                                    ↓
                                            nginx (musquera-web)
                                           ↙               ↘
                              Sitio público (/admin)     /api/*
                                  (HTML+CSS+JS)          ↓
                                                   Node 18 (musquera-server)
                                                         ↓
                                                  PostgreSQL 15 (musquera-db)
```

## 4. Despliegue

### Servicios
| Servicio | Contenedor | Imagen | Puerto |
|----------|-----------|--------|--------|
| Web (nginx) | `musquera-web` | nginx:alpine | 80 |
| API | `musquera-server` | websites-musquera-server | 3000 |
| Base de datos | `musquera-db` | postgres:15-alpine | 5432 |

### Conexiones
- **Ruta código:** `/opt/ai-lab/stacks/websites/musquera-raw/`
- **Stack:** `stacks/websites/docker-compose.backend.yml`
- **Dominio:** `musquera.labrazahome.com`

## 5. Base de datos

### Esquema principal
| Tabla | Propósito |
|-------|-----------|
| `orders` | Pedidos B2B (tracking_id, cliente, cantidad, precio, estado, logs) |
| `inventory` | Stock (prenda, talla, color, nivel, umbral mínimo) |
| `users` | Operarios (admin, manager, operator) |
| `activity_log` | Trazabilidad forense (acciones, IP, timestamp) |

### Estados de pedido
`received` → `in_print` → `quality_check` → `shipped`

### Credenciales DB
| Campo | Valor |
|-------|-------|
| Host | `musquera-db:5432` |
| DB | `raw_factory_db` |
| Usuario | `admin_raw` |
| Password | `Musquera_2026_Segura` |

### Backup de base de datos
```bash
docker exec musquera-db pg_dump -U admin_raw raw_factory_db > /opt/ai-lab/snapshots/musquera-db-$(date +%Y%m%d).sql
```

## 6. Administración

### Panel de administración
```
https://musquera.labrazahome.com/admin
```

### Credenciales por defecto
| Campo | Valor |
|-------|-------|
| **Usuario** | `admin` |
| **Contraseña** | `Musquera123456` |

### API endpoints
| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/login` | POST | Autenticación admin |
| `/api/setup/admin` | POST | Inicializar superadmin |
| `/api/*` | — | API interna del panel |

## 7. Volúmenes Docker
| Volumen | Propósito | Ruta |
|---------|-----------|------|
| `musquera-db-data` | Datos PostgreSQL | `/var/lib/postgresql/data` |
| `musquera-uploads` | Archivos subidos | `/app/public/uploads` |

## 8. Operación

### Iniciar todo
```bash
docker compose -f /opt/ai-lab/stacks/websites/docker-compose.backend.yml up -d
```

### Ver estado
```bash
docker ps | grep musquera
```

### Logs
```bash
docker logs musquera-web --tail 30
docker logs musquera-server --tail 50
docker logs musquera-db --tail 20
```

### Reconstruir API (tras cambios en server.js)
```bash
docker compose -f /opt/ai-lab/stacks/websites/docker-compose.backend.yml build musquera-server
docker compose -f /opt/ai-lab/stacks/websites/docker-compose.backend.yml up -d musquera-server
```

### Reconstruir admin panel (tras cambios en admin-react/)
```bash
cd /opt/ai-lab/stacks/websites/musquera-raw/admin-react
npm install
npm run build
# El admin se sirve desde nginx, no requiere reinicio de contenedor
```

### Parar servicios
```bash
docker compose -f /opt/ai-lab/stacks/websites/docker-compose.backend.yml down
```
> ⚠️ Esto elimina los contenedores pero conserva los datos en volúmenes.

### Reset completo (pérdida de datos)
```bash
docker compose -f /opt/ai-lab/stacks/websites/docker-compose.backend.yml down -v
```
> ⚠️ Esto elimina **todos los datos** incluyendo la base de datos.

## 9. Archivos
```
musquera-raw/
├── server.js               # API Express (JWT, PostgreSQL, Multer)
├── app.js                  # Lógica de aplicación
├── index.html              # Página principal pública
├── style.css               # Estilos públicos
├── nginx.conf              # Configuración nginx (proxy reverso /api)
├── admin-react/            # Panel de administración React
│   ├── dist/               # Build de producción
│   ├── src/                # Código fuente
│   └── package.json
├── admin_manual.md         # Manual de administración
├── simulate_orders.sql     # Datos de simulación para BD
├── docker-compose.yml      # Docker legacy
├── Dockerfile              # Node 18
└── *.md                    # Documentación técnica
```

## 10. Documentación técnica disponible
Los siguientes documentos de especificación están en el directorio del proyecto:
- `STACK_TECNOLOGICO.md` — Stack completo detallado
- `DATABASE_SCHEMA_BACKUPS.md` — Esquema de BD y backups
- `DEPLOYS_Y_PRODUCCION.md` — Procedimientos de deploy
- `CREDENCIALES_PROYECTO.md` — Credenciales
- `GUIA_DISENO_UI_UX.md` — Guía de diseño
- `admin_manual.md` — Manual de administración

## 11. Origen
- **Ubicación original:** `\\192.168.1.200\e\Webs\Musquera RAW LAB\Musquera RAW LAB`
- **Restaurado el:** 13/05/2026
- **Tamaño:** ~45 MB
