# INFORME COMPLETO: RIOJA MARKETPLACE
## Estado, Arquitectura y Plan de Mejora
### Fecha: 13 de mayo de 2026

---

## 1. DATOS DEL SERVIDOR

| Campo | Valor |
|-------|-------|
| **VM** | Serv2025-market |
| **IP** | 192.168.1.150 |
| **OS** | Windows Server 2025 Standard |
| **Virtualización** | Hyper-V (NAS-N5 .250) |
| **Dominio** | `marketplace.labrazahome.com` |
| **CDN** | Cloudflare Tunnel |
| **Usuario Admin** | Administrador |

---

## 2. ARQUITECTURA DEL SISTEMA

```
Cloudflare Tunnel
      │
      ▼
┌───────────────────────────────────────────────────────────────┐
│  Windows Server 2025 (192.168.1.150)                           │
│                                                                │
│  ┌─────────────────────────┐    ┌──────────────────────────┐   │
│  │  Next.js (puerto 80)    │    │  Go Fiber API (:8080)    │   │
│  │  standalone export      │    │  api.exe (compilado)     │   │
│  │  C:\rioja-marketplace\  │◄──►│  /api/v1/*               │   │
│  │  frontend\              │    │                          │   │
│  └──────────┬──────────────┘    └───────────┬──────────────┘   │
│             │                               │                  │
│             │                               ▼                  │
│             │                    ┌──────────────────────────┐   │
│             │                    │  PostgreSQL 17            │   │
│             │                    │  localhost:5432           │   │
│             │                    │  DB: rioja_db             │   │
│             │                    │  User: rioja_user         │   │
│             │                    │  Data: D:\rioja-data\     │   │
│             │                    └──────────────────────────┘   │
│             │                               │                  │
│             ▼                               ▼                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  LM Studio (NAS-N5 .250) → http://192.168.1.250:1234     │  │
│  │  (Sommelier IA + Embeddings + Visión)                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## 3. STACK TECNOLÓGICO DETALLADO

### 3.1. Backend — Go + Fiber v2

| Componente | Tecnología | Archivo |
|-----------|-----------|---------|
| Framework | Fiber v2.52.13 | `go.mod` |
| ORM | GORM v1.31.1 | `internal/database/db.go` |
| Base de datos | PostgreSQL 17 | `D:\rioja-data\postgres\` |
| Pagos | Stripe v82 | `internal/handlers/stripe_handlers.go` |
| Email | Gomail + Gmail SMTP | `internal/services/email_service.go` |
| PDF | go-pdf/fpdf | `internal/services/invoice_service.go` |
| IA | HTTP a LM Studio | `internal/services/ai_service.go` |
| Auth | JWT + bcrypt | `internal/handlers/auth_handlers.go` |
| Binario | `api.exe` | `C:\rioja-marketplace\api.exe` |

### 3.2. Frontend — Next.js 15

| Componente | Tecnología |
|-----------|-----------|
| Framework | Next.js 15 (React 19 RC) |
| Estilos | Tailwind CSS + Framer Motion |
| Iconos | Lucide React |
| HTTP | Axios |
| Build | `next build` con `output: standalone` |
| Proxy API | Next.js rewrites → `localhost:8080/api/v1` |

### 3.3. Base de Datos

| Parámetro | Valor |
|-----------|-------|
| Host | localhost:5432 |
| DB | rioja_db |
| Usuario | rioja_user |
| Password | rioja_pass |
| Datos | `D:\rioja-data\postgres\` |

### 3.4. IA — LM Studio

| Parámetro | Actual → **Corregido** |
|-----------|----------------------|
| Backend URL | `localhost:1234` → **`192.168.1.250:1234`** |
| Frontend URL | `localhost:1234/v1` → **`192.168.1.250:1234/v1`** |

---

## 4. ESTADO POR COMPONENTE

### ✅ Funcionando
- **Go API**: `/api/v1/wines` → 200 OK (~24ms)
- **PostgreSQL**: Conexión estable, esquemas sincronizados
- **Auth**: `/api/v1/auth/me` → 401 (correcto, requiere token)
- **Frontend build**: `.next/BUILD_ID` + `standalone/` ✅
- **Cloudflare**: HTTPS resolviendo correctamente
- **Fotos**: 22 archivos en `frontend/public/photos/`
- **Catálogos**: `/vinos`, `/aceites`, `/mieles` → 200 OK

### ⚠️ Parcial
| Problema | Detalle |
|----------|---------|
| **Rutas 404** | `/checkout`, `/client-portal`, `/admin/*` no resuelven |
| **Frontend runtime** | Puede estar en `dev` en vez de `start` |
| **LM Studio** | Apunta a `localhost` en vez de NAS-N5 |
| **Fotos en D:** | `D:\rioja-data\photos\` vacío (20 fotos sin copiar) |

### ❌ Ausente
- Backend no está como servicio Windows
- Frontend no está como servicio Windows
- Stripe keys expuestas en `.env`

---

## 5. PLAN DE REPARACIÓN PRIORIZADO

### 🔴 Urgente (día 1)

| # | Tarea | Comando / Acción |
|---|-------|-----------------|
| 1 | Copiar fotos | `Copy-Item "D:\Market Place Labrazahome.com\rioja-data\photos\*" "D:\rioja-data\photos\"` |
| 2 | Cambiar LM Studio → NAS | Editar `C:\rioja-marketplace\.env` y `.env.frontend` |
| 3 | Arrancar frontend en producción | `cd C:\rioja-marketplace\frontend && npm run build && npm run start -p 80` |
| 4 | Verificar rutas 404 | Revisar si Next.js corre en standalone o dev |

### 🟡 Importante (día 2)

| # | Tarea | Acción |
|---|-------|--------|
| 5 | Servicio Windows para API | `nssm install RiojaAPI "C:\rioja-marketplace\api.exe"` |
| 6 | Servicio Windows para Next.js | `nssm install RiojaWeb "node" "C:\rioja-marketplace\frontend\node_modules\.bin\next start"` |
| 7 | Stripe keys a Environment | `setx STRIPE_SECRET_KEY "sk_live_..." /M` y limpiar `.env` |
| 8 | Backup automático DB | Script PowerShell + tarea programada |

### 🟢 Mejora continua
| # | Tarea |
|---|-------|
| 9 | Revisar y completar migración desde `D:\Market Place Labrazahome.com\` |
| 10 | Configurar logs rotativos |
| 11 | Dashboard Grafana para el marketplace |
| 12 | Monitoring con Prometheus (ya hay `prometheus.yml` en el proyecto) |

---

## 6. COMANDOS RÁPIDOS (PowerShell Admin)

```powershell
# Servicios
Get-Service -Name *postgres*, *rioja*
Get-Process -Name *api*, *node*

# Puertos
netstat -ano | findstr ":8080 :5432 :80"

# Logs
Get-Content "C:\rioja-marketplace\api_stderr.log" -Tail 30

# Backup DB
pg_dump -U rioja_user -h localhost rioja_db > C:\backup\rioja_$(Get-Date -Format yyyyMMdd).sql

# Rebuild frontend
cd C:\rioja-marketplace\frontend
npm run build
npm run start -p 80
```

---

## 7. RUTAS DEL FRONTEND (Next.js App Router)

| Ruta | Archivo | Estado actual |
|------|---------|--------------|
| `/` | `src/app/page.tsx` | ✅ 200 |
| `/vinos` | `src/app/vinos/` | ✅ 200 |
| `/aceites` | `src/app/aceites/` | ✅ 200 |
| `/mieles` | `src/app/mieles/` | ✅ 200 |
| `/login` | `src/app/login/` | ✅ 200 |
| `/register` | `src/app/register/` | ✅ 200 |
| `/b2b` | `src/app/b2b/page.tsx` | ✅ 200 |
| `/sommelier` | `src/app/sommelier/` | ✅ 200 |
| `/tracking` | `src/app/tracking/` | ✅ 200 |
| `/admin` | `src/app/admin/page.tsx` | ❌ 404 (no build?) |
| `/admin/clientes` | `src/app/admin/clientes/` | ❌ 404 |
| `/admin/config` | `src/app/admin/config/` | ❌ 404 |
| `/admin/facturacion` | `src/app/admin/facturacion/` | ❌ 404 |
| `/admin/inventario` | `src/app/admin/inventario/` | ❌ 404 |
| `/admin/logistica` | `src/app/admin/logistica/` | ❌ 404 |
| `/checkout` | `src/app/checkout/` | ❌ 404 |
| `/client-portal` | `src/app/client-portal/` | ❌ 404 |
| `/product/[id]` | `src/app/product/` | — |
| `/mapa-suelos` | `src/app/mapa-suelos/` | — |
| `/municipios` | `src/app/municipios/` | — |
| `/terminos-b2b` | `src/app/terminos-b2b/` | — |

---

## 8. HANDLERS DEL BACKEND (Go)

| Handler | Archivo | Endpoints |
|---------|---------|-----------|
| Auth | `auth_handlers.go` | Login, registro, JWT |
| Wine | `wine_handlers.go` | CRUD vinos, catálogo |
| B2B | `b2b_handlers.go` | Registro corporativo, tarifas |
| Stripe | `stripe_handlers.go` | Pagos, webhooks |
| AI | `ai_handlers.go` | Sommelier, embeddings |
| Logistics | `logistics_handlers.go` | Envíos, tracking |
| Config | `config_handlers.go` | Configuración |
| Analytics | `analytics_handlers.go` | Estadísticas |
