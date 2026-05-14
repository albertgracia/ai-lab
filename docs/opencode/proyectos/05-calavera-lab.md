# Calavera LAB — Documentación del proyecto
## Ecommerce de coleccionismo de lujo

---

## 1. Descripción
Tienda online de coleccionismo de lujo con checkout integrado vía Stripe. Catálogo de productos exclusivos (Ritual Core Tee, Serpent Hoodie, Collector Pack, etc.) con panel de configuración local para Stripe Payment Links y GA4.

## 2. Stack tecnológico
| Componente | Tecnología |
|------------|-----------|
| Frontend | React 19 + Vite |
| UI/UX | Framer Motion, Lenis (scroll suave) |
| Backend | Node 24 + Express 5 |
| Pagos | Stripe API (checkout sessions) |
| Checkout alternativo | WhatsApp (fallback) |
| Contenedor | Docker (multi-stage build) |
| Proxy | Traefik (AI-LAB) |

## 3. Arquitectura
```
Usuario → Cloudflare Tunnel → 192.168.1.30:80 → Traefik
                                                    ↓
                                       Host: calavera.labrazahome.com
                                                    ↓
                                          Node 24 Express
                                        (server.js + React SPA)
                                                    ↓
                                       Stripe API / WhatsApp API
```

## 4. Despliegue
- **Ruta código:** `/opt/ai-lab/stacks/websites/calavera-lab/`
- **Contenedor:** `calavera-lab`
- **Imagen:** `websites-calavera-lab` (build local)
- **Puerto interno:** 80
- **Red:** `proxy`
- **Stack:** `stacks/websites/docker-compose.backend.yml`
- **Dominio:** `calavera.labrazahome.com`

## 5. Administración

### Panel de configuración local
Acceder con parámetro `?admin=1`:
```
https://calavera.labrazahome.com/?admin=1
```
Aparece botón **"Config Local"** abajo a la izquierda. Permite:
- Configurar **GA4 Measurement ID**
- Asignar **Stripe Payment Links** a cada producto
- Importar/exportar configuración en JSON
- Guardar en localStorage del navegador

### Catálogo de productos
| ID Producto | Nombre | Precio (€) |
|-------------|--------|-----------|
| ritual-core-tee | Ritual Core Tee | 69,00 |
| serpent-hoodie | Serpent Hoodie | 129,00 |
| collector-pack | Collector Pack | 149,00 |
| fiesta-negra-tee | Fiesta Negra Tee | 100,00 |
| corazon-ritual-tee | Corazón Ritual Tee | 100,00 |
| calavera-floral-tee | Calavera Floral Tee | 100,00 |
| corazon-nocturno-tee | Corazón Nocturno Tee | 100,00 |

### Productos de indumentaria (apparel catalog)
Ver `server/apparel-catalog.js` para productos adicionales.

## 6. Operación

### Iniciar / Reiniciar
```bash
docker compose -f /opt/ai-lab/stacks/websites/docker-compose.backend.yml up -d calavera-lab
```

### Reconstruir (tras cambios)
```bash
docker compose -f /opt/ai-lab/stacks/websites/docker-compose.backend.yml build calavera-lab
docker compose -f /opt/ai-lab/stacks/websites/docker-compose.backend.yml up -d calavera-lab
```

### Logs
```bash
docker logs calavera-lab --tail 50
```

### API endpoints
| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/config` | GET | Configuración pública |
| `/api/artifacts-carousel` | GET | Carrusel de imágenes |
| `/api/create-checkout-session` | POST | Crear sesión Stripe |

## 7. ⚠️ Seguridad
Las claves de Stripe están en `.env`:
- `STRIPE_SECRET_KEY=sk_live_...`
- `STRIPE_PUBLISHABLE_KEY=pk_live_...`

**Rotar estas claves inmediatamente si se sospecha exposición.** Considerar mover a secretos Docker o variables de entorno seguras.

## 8. Archivos
```
calavera-lab/
├── src/                    # Frontend React
│   ├── components/         # Componentes (AdminConfigPanel, CheckoutModal, etc.)
│   ├── data/               # Catálogos (content.js, apparelCatalog.js)
│   ├── lib/                # Utilidades (checkout.js, whatsapp.js, local-config.js)
│   └── App.jsx             # App principal
├── server/                 # Backend
│   ├── product-catalog.js  # Catálogo de precios Stripe
│   └── apparel-catalog.js  # Catálogo de indumentaria
├── server.js               # Express server
├── public/                 # Assets públicos
├── Dockerfile              # Multi-stage build
├── .env                    # Stripe keys + config
└── package.json            # Dependencias
```

## 9. Origen
- **Ubicación original:** `\\192.168.1.200\e\Webs\Calavera LAB\Calavera LAB`
- **Restaurado el:** 13/05/2026
- **Tamaño:** ~447 MB
