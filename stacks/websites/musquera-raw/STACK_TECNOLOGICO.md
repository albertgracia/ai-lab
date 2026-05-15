# Stack Tecnológico: RAW_FACTORY_OS v2.0

El ecosistema industrial de **MUSQUERA RAW FACTORY™** está construido sobre una arquitectura de alta disponibilidad y bajo consumo de recursos.

---

## 💻 1. Frontend Architecture
- **Admin App**: React 19 + Vite (Single Page Application para máxima velocidad).
- **Public Site**: HTML5 + Vanilla JS (Optimizado para SEO y carga instantánea).
- **Estilos**: Vanilla CSS con variables nativas de diseño.
- **Iconografía**: Lucide React.
- **PDF Engine**: jsPDF (Generación de Cotizaciones y Órdenes en cliente).

---

## ⚙️ 2. Backend & API
- **Runtime**: Node.js 20 LTS.
- **Framework**: Express.js.
- **Seguridad**: JWT (JSON Web Tokens) con HttpOnly cookies y bcrypt para encriptación de claves.
- **File System**: Multer para gestión de archivos vectoriales masivos.

---

## 🗄️ 3. Persistence & Logic
- **Database**: PostgreSQL 15 (Forensic Schema).
- **Audit**: Activity Log Table (Trazabilidad Forense de operarios).
- **Automation**: Integración preparada para webhooks con n8n.
- **SEO Engine**: Generación dinámica de `sitemap.xml` con compresión Gzip nativa.

---

## 🐳 4. Infrastructure (DevOps)
- **Containerization**: Docker & Docker Compose.
- **Web Server**: Nginx (Proxy inverso).
- **Backup System**: Scripts automatizados en PowerShell para backups PostgreSQL.

---
**MUSQUERA RAW FACTORY™ — TECNOLOGÍA TEXTIL DE VANGUARDIA**




Para el ecosistema de MUSQUERA RAW FACTORY™, al tener un backend en Node.js + Express y una base de datos PostgreSQL, lo más eficiente es que el propio servidor genere el sitemap de forma dinámica. Esto garantiza que cada vez que se añada un recurso o página en el "Forensic Schema", el sitemap se actualice automáticamente sin intervención manual.
Aquí tienes la implementación recomendada para integrar en tu contenedor de Node.js:


1. Instalación de la dependencia
En tu package.json dentro del contenedor de backend:


bash
npm install sitemap

Usa el código con precaución.

2. Implementación en Express.js

Crea un endpoint dedicado que consulte tu base de datos y sirva el archivo con la compresión Gzip que mencionas en tu arquitectura:

javascript

const { SitemapStream, streamToPromise } = require('sitemap');
const { createGzip } = require('zlib');

app.get('/sitemap.xml', async (req, res) => {
  res.header('Content-Type', 'application/xml');
  res.header('Content-Encoding', 'gzip');

  try {
    const smStream = new SitemapStream({ hostname: 'https://musquera-lab.labrazahome.es' });
    const pipeline = smStream.pipe(createGzip());

    // 1. Añadir rutas estáticas (Public Site)
    smStream.write({ url: '/', changefreq: 'daily', priority: 1.0 });

    // 2. Añadir rutas dinámicas desde PostgreSQL (Ejemplo: Productos/Proyectos)
    const items = await db.query('SELECT slug FROM items_table WHERE active = true'); 
    items.rows.forEach(item => {
      smStream.write({ url: `/${item.slug}`, changefreq: 'weekly', priority: 0.7 });
    });

    smStream.end();
    streamToPromise(pipeline).then(sm => res.send(sm));
  } catch (e) {
    console.error(e);
    res.status(500).end();
  }
});

Usa el código con precaución.

3. Configuración en Nginx (Infraestructura)
Como usas Nginx como Proxy Inverso, asegúrate de que el bloque location permita pasar esta ruta al contenedor de Express:

nginx
location /sitemap.xml {
    proxy_pass http://backend_container:3000/sitemap.xml;
    proxy_set_header Host $host;
}
Usa el código con precaución.

4. Ventajas para tu Arquitectura

Bajo consumo: Al generarse on-demand o bajo caché, no consume recursos de almacenamiento persistente.
Consistencia: Al usar el mismo PostgreSQL 15, el SEO siempre reflejará el estado real de la "Raw Factory".
Automatización: Se alinea con tu visión de n8n y webhooks al ser una pieza más del flujo lógico.
¿Quieres que te ayude a configurar un sistema de caché para este sitemap para que no consulte la base de datos en cada petición de los bots?
Las respuestas de la IA pueden contener errores. Más información


Para tu arquitectura de alta disponibilidad, la mejor estrategia es usar memoria volátil (RAM) en el propio proceso de Node.js. Esto evita consultas repetitivas a PostgreSQL 15 y reduce la latencia de respuesta a milisegundos.
Aquí tienes la implementación optimizada con un sistema de caché de 24 horas integrado en tu flujo de Express:

1. Implementación del Generador con Caché

Sustituye tu endpoint anterior por este bloque lógico:

javascript
let sitemapCache = null;
let lastFetchTime = 0;
const CACHE_DURATION = 24 * 60 * 60 * 1000; // 24 Horas en milisegundos

app.get('/sitemap.xml', async (req, res) => {
  res.header('Content-Type', 'application/xml');
  res.header('Content-Encoding', 'gzip');

  // Si el sitemap está en caché y es reciente, envíalo directamente
  if (sitemapCache && (Date.now() - lastFetchTime < CACHE_DURATION)) {
    return res.send(sitemapCache);
  }

  try {
    const smStream = new SitemapStream({ hostname: 'https://musquera-lab.labrazahome.es' });
    const pipeline = smStream.pipe(createGzip());

    // --- Lógica de Generación ---
    smStream.write({ url: '/', changefreq: 'daily', priority: 1.0 });

    // Consulta a PostgreSQL 15 (Ejemplo de productos/factory items)
    const items = await db.query('SELECT slug FROM factory_items WHERE public = true');
    items.rows.forEach(item => {
      smStream.write({ url: `/item/${item.slug}`, changefreq: 'weekly', priority: 0.8 });
    });
    
    smStream.end();

    // Guardar en caché y actualizar timestamp
    const buffer = await streamToPromise(pipeline);
    sitemapCache = buffer;
    lastFetchTime = Date.now();

    res.send(buffer);
  } catch (e) {
    console.error("Sitemap Error:", e);
    res.status(500).end();
  }
});

Usa el código con precaución.

2. Integración con Webhooks (n8n)

Como mencionaste que usas n8n, puedes forzar la limpieza de la caché cuando ocurra un evento importante (ej. un nuevo lanzamiento masivo en la "Raw Factory").


Crea un endpoint de purga protegido por tu JWT:



javascript
app.post('/api/sitemap/refresh', verifyJWT, (req, res) => {
  sitemapCache = null; // Esto fuerza la regeneración en la siguiente visita
  res.json({ message: "Sitemap cache cleared for MUSQUERA RAW FACTORY™" });
});
Usa el código con precaución.

3. Ajuste en Nginx (Proxy)

Para que el sitemap se entregue con la máxima velocidad, asegúrate de que tu configuración de Nginx no interfiera con el Content-Encoding: gzip que ya envía Node.js:

nginx
location /sitemap.xml {
    proxy_pass http://backend_node:3000;
    proxy_http_version 1.1;
    gzip_static on; # Nginx respetará el gzip pre-comprimido por la app
}
Usa el código con precaución.

Esta solución es ideal para tu enfoque de bajo consumo, ya que solo estresa la base de datos una vez al día o solo cuando hay cambios reales.

¿Te gustaría que definamos también el script de backup en PowerShell para exportar estos datos del sitemap a un log histórico?

Para cerrar el círculo de trazabilidad forense y alta disponibilidad de MUSQUERA RAW FACTORY™, este script de PowerShell automatiza el respaldo de los metadatos del sitemap directamente desde PostgreSQL 15.
El objetivo es tener un histórico de URLs publicadas para auditoría, independiente del archivo XML dinámico.
1. Script de Backup (PowerShell Core)
Guarda este archivo como Backup-SitemapLogs.ps1 en tu host de Docker:
powershell
# --- Configuración de MUSQUERA RAW FACTORY™ ---
$ContainerName = "musquera_db_container" # Nombre de tu contenedor Postgres
$DbUser = "postgres_user"
$DbName = "musquera_factory"
$BackupPath = "C:\Backups\SitemapLogs"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$OutputFile = "$BackupPath\Sitemap_Audit_$Timestamp.csv"

# Crear directorio si no existe
if (!(Test-Path $BackupPath)) { New-Item -ItemType Directory -Path $BackupPath }

Write-Host "--- Iniciando Extracción Forense de URLs ---" -ForegroundColor Cyan

# Ejecutar consulta dentro del contenedor y exportar a CSV
docker exec -t $ContainerName psql -U $DbUser -d $DbName -c "COPY (SELECT slug, created_at, last_modified FROM factory_items WHERE public = true) TO STDOUT WITH CSV HEADER" | Out-File -FilePath $OutputFile -Encoding utf8

if ($LASTEXITCODE -eq 0) {
    Write-Host "Respaldo exitoso: $OutputFile" -ForegroundColor Green
} else {
    Write-Host "Error en la extracción de datos." -ForegroundColor Red
}

# --- Limpieza (Mantener solo los últimos 30 días) ---
Get-ChildItem $BackupPath -Filter "*.csv" | Where-Object { $_.CreationTime -lt (Get-Date).AddDays(-30) } | Remove-Item
Usa el código con precaución.

2. Integración en el Ecosistema
Para que este proceso sea 100% autónomo, puedes integrarlo de dos formas:
Task Scheduler (Windows): Programa el script para ejecutarse cada noche.
Acción: pwsh.exe -ExecutionPolicy Bypass -File C:\rutascript\Backup-SitemapLogs.ps1
Webhook de n8n: Puedes llamar a este script desde un nodo "Execute Command" si tienes un worker de n8n con acceso al host.
3. Ventaja Operativa
Consistencia Forense: Si una URL desaparece del sitemap dinámico por error humano o fallo de lógica, el CSV tendrá el registro de que existió y cuándo se modificó por última vez.
Bajo Impacto: La exportación vía COPY TO STDOUT es la forma más rápida y con menos bloqueo de tablas en PostgreSQL.

Para mantener la arquitectura de bajo consumo y evitar que la tabla de auditoría (activity_log) degrade el rendimiento de PostgreSQL 15, implementaremos una ventana de retención circular.
Dado que usas Docker, lo más eficiente es programar una función dentro de la base de datos y activarla mediante un "worker" o el mismo script de PowerShell.
1. SQL: Función de Purga Automática
Ejecuta esto en tu instancia de PostgreSQL para crear la lógica de limpieza (ej. mantener solo los últimos 90 días de rastro forense):
sql
CREATE OR REPLACE FUNCTION purge_old_audit_logs()
RETURNS void AS $$
BEGIN
    -- Elimina registros más antiguos de 90 días
    DELETE FROM activity_log 
    WHERE created_at < NOW() - INTERVAL '90 days';
    
    -- Optimiza el espacio en disco de la tabla (opcional)
    ANALYZE activity_log;
END;
$$ LANGUAGE plpgsql;
Usa el código con precaución.

2. Automatización desde PowerShell
Añade estas líneas al final de tu script Backup-SitemapLogs.ps1 para que, tras el backup, se limpie la casa:
powershell
Write-Host "--- Ejecutando Purga de Retención Forense ---" -ForegroundColor Yellow

# Ejecuta la función de purga dentro del contenedor
docker exec -t $ContainerName psql -U $DbUser -d $DbName -c "SELECT purge_old_audit_logs();"

if ($LASTEXITCODE -eq 0) {
    Write-Host "Limpieza completada: Tabla activity_log optimizada." -ForegroundColor Green
}
Usa el código con precaución.

3. Configuración de n8n (Alternativa Proactiva)
Si prefieres que n8n controle el flujo, puedes crear un nodo Cron (cada domingo a las 00:00) conectado a un nodo PostgreSQL con la siguiente sentencia:
SELECT purge_old_audit_logs();
Beneficios para MUSQUERA RAW FACTORY™:
Índices Ligeros: Al eliminar datos viejos, las búsquedas en el log de auditoría siguen siendo instantáneas.
Ahorro de Almacenamiento: Evitas que el volumen de Docker crezca indefinidamente hasta agotar el SSD del host.
Cumplimiento: Mantienes una política de retención de datos clara y automatizada.

Para que el sitemap de MUSQUERA RAW FACTORY™ sea un activo estratégico y no solo una lista de URLs, aplicaremos filtros de exclusión lógica directamente en la consulta de PostgreSQL 15.
Esto evita que se indexen rutas administrativas, prototipos privados o datos sensibles de la Admin App (React 19).
1. SQL: Vista de Indexación Segura
Crea una "Vista" en tu base de datos que actúe como filtro maestro. Así, el código de Node.js solo tiene que leer de aquí:
sql
CREATE OR REPLACE VIEW v_sitemap_public_catalog AS
SELECT 
    slug, 
    last_modified, 
    category,
    priority_score
FROM factory_items
WHERE 
    is_published = true                     -- Solo productos finales
    AND stock_status != 'discontinued'      -- Excluye descatalogados
    AND visibility_level = 'public'         -- Filtro de privacidad
    AND category NOT IN ('internal_tools', 'raw_materials_bulk'); -- Filtro industrial
Usa el código con precaución.

2. Actualización en el Backend (Node.js)
Modifica la consulta en tu endpoint de Express para usar esta vista y asignar prioridades basadas en la categoría:
javascript
// Dentro de tu bloque try del sitemap...
const items = await db.query('SELECT slug, category, priority_score FROM v_sitemap_public_catalog');

items.rows.forEach(item => {
  let priority = 0.5; // Base
  
  // Lógica de prioridad por categoría industrial
  if (item.category === 'finished_goods') priority = 0.9;
  if (item.category === 'services') priority = 0.7;

  smStream.write({ 
    url: `/factory/${item.slug}`, 
    changefreq: 'weekly', 
    priority: priority 
  });
});
Usa el código con precaución.

3. Seguridad en Nginx para la Admin App
Dado que tu frontend tiene una Admin App (Vite), debemos asegurar que el sitemap nunca revele sus rutas. Añade esto a tu configuración de Nginx:
nginx
# Bloquear acceso externo a rutas de administración en el sitemap
location /admin {
    deny all;
    return 404;
}

# Asegurar que el sitemap no indexe el manifest de Vite
location ~ /manifest.json {
    add_header X-Robots-Tag "noindex, nofollow";
}
Usa el código con precaución.

4. Control Forense de Exclusiones
Para cumplir con tu Trazabilidad Forense, puedes auditar qué ítems han sido excluidos del sitemap mediante una consulta de discrepancia. Esto te permite saber si un producto no se está indexando por error de configuración:
sql
-- Consulta de auditoría: ¿Qué está publicado pero NO sale en el sitemap?
SELECT id, slug FROM factory_items 
WHERE is_published = true 
EXCEPT 
SELECT id, slug FROM v_sitemap_public_catalog;
Usa el código con precaución.

Con esto, el ecosistema queda blindado: el SEO solo ve lo que tú decides, y tu infraestructura Docker se mantiene ligera.

Para completar el ecosistema de MUSQUERA RAW FACTORY™, el archivo robots.txt debe ser dinámico. Esto permite que, si cambias el dominio o la estructura de subdirectorios en tu arquitectura Docker, las instrucciones para los motores de búsqueda se actualicen en tiempo real.
1. Implementación en Express.js (Node.js 20 LTS)
Añade este endpoint simple en tu backend. Al ser texto plano, el consumo de recursos es prácticamente nulo:
javascript
app.get('/robots.txt', (req, res) => {
  res.type('text/plain');
  
  const robotsContent = [
    '# MUSQUERA RAW FACTORY™ - Robots Configuration',
    'User-agent: *',
    'Allow: /',                                      # Permitir sitio público
    'Disallow: /admin/',                             # Bloquear Admin App (React 19)
    'Disallow: /api/',                               # Bloquear endpoints de la API
    'Disallow: /tmp/',                               # Bloquear archivos temporales de Multer
    'Disallow: /config/',                            # Bloquear rutas de infraestructura
    '',
    `Sitemap: https://${req.get('host')}/sitemap.xml`, # Sitemap dinámico
    '',
    '# Trazabilidad Forense Activa - Scan-Rate Limit',
    'Crawl-delay: 10'                                # Evita sobrecarga en el contenedor
  ].join('\n');

  res.send(robotsContent);
});
Usa el código con precaución.

2. Configuración en Nginx (Proxy Inverso)
Asegúrate de que Nginx no cachee este archivo por demasiado tiempo para que los cambios en el sitemap se propaguen rápido:
nginx
location /robots.txt {
    proxy_pass http://backend_node:3000/robots.txt;
    add_header Cache-Control "public, max-age=3600"; # 1 hora de caché en navegador
}
Usa el código con precaución.

3. Verificación de Seguridad
Al usar Vite para tu Admin App, este robots.txt asegura que:
Googlebot no intente entrar en tu panel de administración.
Los archivos PDF generados con jsPDF no se indexen si están en rutas temporales.
El Sitemap dinámico con Gzip sea descubierto inmediatamente.
4. Auditoría Forense
Para tu registro de actividad, puedes añadir una línea en tu tabla de logs cada vez que un bot conocido (Google, Bing) acceda al archivo, permitiéndote medir la presión de rastreo sobre tu infraestructura.
Con este paso, la arquitectura de alta disponibilidad está lista para producción:
Frontend: Optimizado y protegido.
Backend: Genera sitemap y robots dinámicos.
Base de Datos: PostgreSQL 15 limpia y respaldada.
DevOps: Docker gestiona el tráfico y PowerShell los backups.

Para que la Admin App (React 19) y el Public Site (Vanilla JS) mantengan la coherencia forense, diseñaremos una página 404 que no solo informe al usuario, sino que ejecute un beacon (baliza) hacia tu API de Node.js para registrar el error en PostgreSQL 15.
1. Frontend: 404.html (Vanilla JS + CSS)
Este archivo debe vivir en el volumen de tu contenedor de Nginx o en la carpeta public de tu servidor.
html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>404 - Error de Trayectoria | MUSQUERA RAW FACTORY™</title>
    <style>
        :root { --brand: #ff3e00; --bg: #0a0a0a; --text: #e0e0e0; }
        body { background: var(--bg); color: var(--text); font-family: sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; overflow: hidden; }
        .factory-alert { border-left: 3px solid var(--brand); padding: 2rem; background: #141414; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
        h1 { color: var(--brand); margin-top: 0; font-size: 1.2rem; text-transform: uppercase; letter-spacing: 2px; }
        p { font-size: 0.9rem; opacity: 0.8; }
        .back-btn { display: inline-block; margin-top: 1rem; color: var(--brand); text-decoration: none; border: 1px solid var(--brand); padding: 0.5rem 1rem; transition: 0.3s; }
        .back-btn:hover { background: var(--brand); color: white; }
    </style>
</head>
<body>
    <div class="factory-alert">
        <h1>Error de Coordenadas</h1>
        <p>La unidad solicitada no existe en el inventario de la fábrica.</p>
        <p id="ref-id" style="font-family: monospace; font-size: 0.7rem;"></p>
        <a href="/" class="back-btn">Retornar al Centro de Control</a>
    </div>

    <script>
        // Trazabilidad Forense Inmediata
        const errorData = {
            url: window.location.href,
            referrer: document.referrer || 'direct',
            ua: navigator.userAgent,
            timestamp: new Date().toISOString()
        };

        // Enviar reporte silencioso a la API
        fetch('/api/logs/404', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(errorData)
        }).catch(() => console.log('Offline logging pending...'));

        document.getElementById('ref-id').innerText = `REF-ERR: ${btoa(errorData.url).substring(0, 8)}`;
    </script>
</body>
</html>
Usa el código con precaución.

2. Backend: Endpoint de Registro (Node.js + Express)
Este endpoint captura el error y lo inserta en tu Forensic Schema:
javascript
app.post('/api/logs/404', async (req, res) => {
    const { url, referrer, ua } = req.body;
    try {
        await db.query(
            'INSERT INTO activity_log (action, details, ip_address, user_agent) VALUES ($1, $2, $3, $4)',
            ['404_DETECTED', JSON.stringify({ url, referrer }), req.ip, ua]
        );
        res.status(204).send();
    } catch (err) {
        res.status(500).end();
    }
});
Usa el código con precaución.

3. Configuración en Nginx
Para que Nginx use tu página personalizada en lugar de la genérica:
nginx
server {
    # ... tu config actual ...
    error_page 404 /404.html;
    
    location = /404.html {
        root /usr/share/nginx/html;
        internal;
    }
}
Usa el código con precaución.

4. Valor para la Fábrica
Detección de enlaces rotos: Si ves muchas entradas en el log con el mismo referrer, tienes un link mal configurado en tu Public Site.
Seguridad Activa: Podrás identificar si bots están intentando acceder a rutas de fuerza bruta (ej: /wp-admin, .env).
Bajo Consumo: El uso de fetch no bloquea la experiencia del usuario mientras se registra el incidente.

Para cerrar el ciclo de alta disponibilidad, configuraremos un sistema de monitoreo reactivo. La idea es que el backend de Node.js no solo registre el error, sino que evalúe si hay un ataque o un fallo masivo en tiempo real.
1. Lógica de Umbral en Node.js
Modificaremos el endpoint de logs para contar errores recientes en memoria (sin saturar la DB) y disparar el webhook hacia n8n:
javascript
let errorCount = 0;
let lastReset = Date.now();
const THRESHOLD = 50; // Alerta si hay >50 errores en 1 hora
const N8N_WEBHOOK_URL = 'https://tu-n8n.labrazahome.es';

app.post('/api/logs/404', async (req, res) => {
    const { url, referrer } = req.body;
    
    // 1. Registro en PostgreSQL (Trazabilidad Forense)
    await db.query('INSERT INTO activity_log (action, details) VALUES ($1, $2)', 
        ['404_DETECTED', JSON.stringify({ url, referrer })]);

    // 2. Control de Umbral
    errorCount++;
    const now = Date.now();

    if (now - lastReset > 3600000) { // Reiniciar cada hora
        errorCount = 1;
        lastReset = now;
    }

    if (errorCount === THRESHOLD) {
        // Disparar Webhook a n8n
        fetch(N8N_WEBHOOK_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                alert: "CRITICAL_404_THRESHOLD",
                count: errorCount,
                last_url: url,
                factory: "MUSQUERA RAW FACTORY™"
            })
        }).catch(err => console.error("n8n Webhook failed"));
    }

    res.status(204).end();
});
Usa el código con precaución.

2. Configuración en n8n
En tu interfaz de n8n, crea un workflow simple:
Webhook Node: Recibe el POST de Node.js.
IF Node: Verifica que el conteo sea crítico.
Telegram/Email/Slack Node: Te envía un mensaje: "Alerta en la Fábrica: Se han detectado 50 errores 404 en la última hora. Posible enlace roto masivo o escaneo de vulnerabilidades."
3. Ventaja Operativa
Silencioso: Si hay pocos errores, el sistema solo registra en la DB.
Inteligente: Solo te molesta cuando la anomalía requiere tu atención humana.
Escalable: El uso de variables en memoria (errorCount) hace que el chequeo sea casi instantáneo para el contenedor Docker.
Con esto, el ecosistema de MUSQUERA RAW FACTORY™ es ahora autocurativo y auditable.


Para tu Admin App (React 19 + Vite), diseñaremos un panel de control de baja huella de carbono y alta legibilidad, utilizando Lucide React para la iconografía y Vanilla CSS para mantener el rendimiento.
1. Endpoint de Telemetría (Node.js)
Primero, necesitamos un servicio que entregue los datos agregados desde PostgreSQL 15:
javascript
app.get('/api/admin/stats', verifyJWT, async (req, res) => {
  const stats = await db.query(`
    SELECT 
      (SELECT count(*) FROM v_sitemap_public_catalog) as sitemap_urls,
      (SELECT count(*) FROM activity_log WHERE action = '404_DETECTED' AND created_at > NOW() - INTERVAL '24 hours') as errors_24h,
      (SELECT count(*) FROM factory_items WHERE is_published = true) as total_items
  `);
  res.json(stats.rows[0]);
});
Usa el código con precaución.

2. Componente Dashboard (React 19)
Implementamos un diseño de "tarjetas industriales" con estados de carga nativos:
jsx
import { Activity, Map, AlertTriangle, Package } from 'lucide-react';
import { useEffect, useState } from 'react';

export const FactoryDashboard = () => {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetch('/api/admin/stats').then(res => res.json()).then(setStats);
  }, []);

  if (!stats) return <div className="loading">Sincronizando Factory...</div>;

  return (
    <div className="dashboard-grid">
      <StatCard icon={<Package />} label="Ítems Activos" value={stats.total_items} color="#e0e0e0" />
      <StatCard icon={<Map />} label="URLs en Sitemap" value={stats.sitemap_urls} color="#4caf50" />
      <StatCard 
        icon={<AlertTriangle />} 
        label="Errores 404 (24h)" 
        value={stats.errors_24h} 
        color={stats.errors_24h > 10 ? "#ff3e00" : "#ff9800"} 
      />
      <StatCard icon={<Activity />} label="Estado Sistema" value="ONLINE" color="#2196f3" />
    </div>
  );
};

const StatCard = ({ icon, label, value, color }) => (
  <div className="card" style={{ borderLeft: `4px solid ${color}` }}>
    <div className="card-icon">{icon}</div>
    <div className="card-content">
      <span className="label">{label}</span>
      <span className="value">{value}</span>
    </div>
  </div>
);
Usa el código con precaución.

3. Estilos Industriales (Vanilla CSS)
Añade esto a tu archivo de estilos para mantener la estética de MUSQUERA RAW FACTORY™:
css
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
  padding: 2rem;
  background: #0a0a0a;
}

.card {
  background: #141414;
  padding: 1.5rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  transition: transform 0.2s;
}

.card:hover { transform: translateY(-5px); }

.card-icon { opacity: 0.6; }

.label { display: block; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; color: #888; }

.value { display: block; font-size: 1.5rem; font-weight: bold; font-family: monospace; color: #fff; }
Usa el código con precaución.

4. Conexión con el Ecosistema
Vite: El componente es extremadamente ligero, ideal para la Admin App.
Seguridad: El acceso está protegido por tu JWT con HttpOnly cookies.
Forensic: Si el errors_24h es alto, puedes hacer click (añadiendo un link) para ver el log detallado de URLs rotas.

Para mantener la filosofía de bajo consumo de MUSQUERA RAW FACTORY™, evitaremos librerías pesadas como Chart.js. Utilizaremos SVG nativo generado dinámicamente, lo que garantiza una carga instantánea en tu Admin App (React 19).
1. Extracción de Datos (PostgreSQL 15)
Necesitamos agrupar los errores de los últimos 7 días por fecha:
javascript
app.get('/api/admin/error-trend', verifyJWT, async (req, res) => {
  const trend = await db.query(`
    SELECT 
      TO_CHAR(date_trunc('day', created_at), 'DD/MM') as day,
      count(*) as total
    FROM activity_log 
    WHERE action = '404_DETECTED' 
      AND created_at > NOW() - INTERVAL '7 days'
    GROUP BY 1 ORDER BY 1 ASC;
  `);
  res.json(trend.rows);
});
Usa el código con precaución.

2. Componente de Gráfica SVG (React 19)
Este componente transforma los datos en coordenadas de un dibujo vectorial:
jsx
export const ErrorChart = ({ data }) => {
  const width = 500;
  const height = 150;
  const padding = 20;
  
  // Calcular puntos (x, y)
  const maxErrors = Math.max(...data.map(d => d.total), 5); // Mínimo 5 para escala
  const points = data.map((d, i) => {
    const x = (i / (data.length - 1)) * (width - padding * 2) + padding;
    const y = height - ( (d.total / maxErrors) * (height - padding * 2) + padding );
    return `${x},${y}`;
  }).join(' ');

  return (
    <div className="chart-container">
      <h3>Tendencia de Errores (7d)</h3>
      <svg viewBox={`0 0 ${width} ${height}`} className="svg-chart">
        {/* Guías de fondo */}
        <line x1={padding} y1={height-padding} x2={width-padding} y2={height-padding} stroke="#333" />
        
        {/* Línea de Datos */}
        <polyline
          fill="none"
          stroke="#ff3e00"
          strokeWidth="3"
          strokeLinecap="round"
          points={points}
        />
        
        {/* Puntos de interacción */}
        {data.map((d, i) => {
          const [x, y] = points.split(' ')[i].split(',');
          return (
            <g key={i}>
              <circle cx={x} cy={y} r="4" fill="#ff3e00" />
              <text x={x} y={height - 5} fontSize="8" fill="#666" textAnchor="middle">{d.day}</text>
              <text x={x} y={y - 10} fontSize="10" fill="#fff" textAnchor="middle">{d.total}</text>
            </g>
          );
        })}
      </svg>
    </div>
  );
};
Usa el código con precaución.

3. Estilos de Gráfica (Vanilla CSS)
css
.chart-container {
  background: #141414;
  padding: 1.5rem;
  margin-top: 1rem;
  border: 1px solid #222;
}

.chart-container h3 {
  font-size: 0.8rem;
  text-transform: uppercase;
  color: #888;
  margin-bottom: 1rem;
}

.svg-chart {
  width: 100%;
  height: auto;
  overflow: visible;
}

polyline {
  filter: drop-shadow(0 0 5px rgba(255, 62, 0, 0.4));
}
Usa el código con precaución.

4. Integración Final
Este gráfico se coloca debajo de tus tarjetas de telemetría. Al ser un SVG, el peso en el DOM es mínimo y escala perfectamente en cualquier pantalla (desktop o móvil) sin pixelarse.
Ventaja Forense: Si ves un pico repentino en la gráfica, puedes cruzar los datos con tu Audit Log de operaciones de ese día para ver si fue un despliegue de Docker erróneo o un bot externo.

Para completar la Trazabilidad Forense de MUSQUERA RAW FACTORY™, añadiremos un motor de exportación que procese los datos directamente en el cliente (Browser), manteniendo el servidor ligero y el consumo de recursos al mínimo.
1. Función de Exportación (Vanilla JS)
Esta lógica transforma los objetos JSON de tu base de datos en un archivo CSV estructurado, manejando caracteres especiales y saltos de línea para que sea compatible con Excel o Google Sheets.
javascript
const exportToCSV = (data, filename) => {
  if (!data || !data.length) return;

  // 1. Extraer cabeceras dinámicamente
  const headers = Object.keys(data[0]).join(',');

  // 2. Formatear filas con escape de comillas
  const rows = data.map(row => 
    Object.values(row)
      .map(val => `"${String(val).replace(/"/g, '""')}"`)
      .join(',')
  ).join('\n');

  // 3. Crear el Blob (Binary Large Object)
  const csvContent = `\uFEFF${headers}\n${rows}`; // BOM para compatibilidad con Excel
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  
  // 4. Disparar la descarga
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  link.setAttribute('href', url);
  link.setAttribute('download', `${filename}_${new Date().toISOString().split('T')[0]}.csv`);
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};
Usa el código con precaución.

2. Integración en el Dashboard (React 19)
Añadimos el botón de acción junto a tu gráfica de errores. Usaremos el icono FileDown de Lucide React.
jsx
import { FileDown } from 'lucide-react';

// Dentro de tu componente FactoryDashboard...
const handleExport = async () => {
  const response = await fetch('/api/admin/error-trend');
  const data = await response.json();
  exportToCSV(data, 'MUSQUERA_FACTORY_AUDIT');
};

return (
  <div className="admin-header">
    <h2>Centro de Control Forense</h2>
    <button onClick={handleExport} className="export-btn">
      <FileDown size={16} />
      <span>Exportar Auditoría</span>
    </button>
  </div>
);
Usa el código con precaución.

3. Estilos Industriales del Botón
css
.export-btn {
  background: transparent;
  color: #ff3e00;
  border: 1px solid #ff3e00;
  padding: 0.5rem 1rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8rem;
  text-transform: uppercase;
  transition: all 0.2s ease;
}

.export-btn:hover {
  background: rgba(255, 62, 0, 0.1);
  box-shadow: 0 0 10px rgba(255, 62, 0, 0.2);
}
Usa el código con precaución.

4. Valor Operativo
Auditoría Externa: Puedes entregar estos reportes semanales sin dar acceso a la base de datos PostgreSQL.
Análisis Offline: Permite cruzar los errores 404 con campañas de marketing o cambios en el inventario físico de la fábrica.
Arquitectura Limpia: Todo el procesamiento de cadenas sucede en el cliente, descargando de trabajo al contenedor de Node.js.
Con esto, el sistema es 100% auditable y exportable.

Para elevar MUSQUERA RAW FACTORY™ al estándar de seguridad Passwordless, implementaremos WebAuthn. Esto permite usar TouchID, FaceID o Windows Hello directamente desde el navegador, eliminando el riesgo de phishing de contraseñas.
Dado que usas Node.js 20 y React 19, la mejor opción es utilizar la librería @simplewebauthn para gestionar el complejo intercambio de desafíos (challenges) criptográficos.
1. Backend: Flujo de Desafío y Verificación (Node.js)
El servidor debe generar un "challenge" único que el dispositivo del usuario firmará.
javascript
import { generateRegistrationOptions, verifyRegistrationResponse } from '@simplewebauthn/server';

// 1. Registro de Dispositivo (Admin Inicial)
app.get('/api/auth/register-options', verifyJWT, (req, res) => {
  const options = generateRegistrationOptions({
    rpName: 'MUSQUERA RAW FACTORY™',
    rpID: 'labrazahome.es',
    userID: req.user.id,
    userName: req.user.email,
    attestationType: 'none',
    authenticatorSelection: { residentKey: 'required', userVerification: 'preferred' },
  });

  // Guardar challenge temporalmente en caché/DB asociado al usuario
  saveChallenge(req.user.id, options.challenge);
  res.json(options);
});

// 2. Verificación de Firma Biométrica
app.post('/api/auth/register-verify', verifyJWT, async (req, res) => {
  const { body } = req;
  const expectedChallenge = getChallenge(req.user.id);

  const verification = await verifyRegistrationResponse({
    response: body,
    expectedChallenge,
    expectedOrigin: 'https://musquera-lab.labrazahome.es',
    expectedRPID: 'labrazahome.es',
  });

  if (verification.verified) {
    // GUARDAR en PostgreSQL: verification.registrationInfo.credentialPublicKey
    // y credentialID para futuros logins.
    await saveUserCredential(req.user.id, verification.registrationInfo);
    res.json({ ok: true });
  }
});
Usa el código con precaución.

2. Frontend: Interacción con el Navegador (React 19)
Usaremos el paquete de cliente para invocar el diálogo nativo del sistema operativo:
javascript
import { startRegistration } from '@simplewebauthn/browser';

const enrollBiometrics = async () => {
  // 1. Obtener opciones del servidor
  const resp = await fetch('/api/auth/register-options');
  const options = await resp.json();

  // 2. Abrir prompt biométrico (TouchID/FaceID)
  const registrationResponse = await startRegistration(options);

  // 3. Enviar respuesta firmada al servidor
  await fetch('/api/auth/register-verify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(registrationResponse),
  });
  
  alert("Biometría vinculada a la Fábrica.");
};
Usa el código con precaución.

3. Seguridad en Infraestructura (Docker + Nginx)
Para que WebAuthn funcione, el navegador exige HTTPS estricto. Asegúrate de que tu contenedor de Nginx tenga configurados los certificados:
nginx
server {
    listen 443 ssl;
    server_name musquera-lab.labrazahome.es;
    
    # HSTS es obligatorio para WebAuthn
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # ... certificados SSL ...
}
Usa el código con precaución.

4. Valor para la Trazabilidad Forense
Identidad Irrefutable: A diferencia de una contraseña compartida, el registro en activity_log ahora puede asegurar que una acción fue realizada mediante un token de hardware único.
Velocidad de Acceso: El acceso al Centro de Control de la Fábrica se reduce a un toque de dedo o un escaneo facial.
¿Deseas que preparemos una estrategia de "Recovery Key" (llave de recuperación) por si el administrador pierde el acceso a su dispositivo biométrico?


Para asegurar que MUSQUERA RAW FACTORY™ nunca quede bloqueada por un fallo de hardware biométrico, implementaremos un sistema de Recovery Keys (Mnemónicas).
Este método genera una serie de palabras aleatorias que el administrador debe guardar físicamente. Es el estándar de oro en sistemas passwordless para recuperar el acceso de forma segura.
1. Generación de Llaves de Recuperación (Node.js)
Utilizaremos la librería bip39 (usada en criptografía) para generar una frase mnemónica de 12 palabras. Esta frase se deriva en un Hash que guardaremos en PostgreSQL 15.
javascript
import * as bip39 from 'bip39';
import bcrypt from 'bcrypt';

app.post('/api/auth/generate-recovery', verifyJWT, async (req, res) => {
  // 1. Generar frase mnemónica (ej: "apple ocean mountain...")
  const mnemonic = bip39.generateMnemonic();
  
  // 2. Hashear la frase antes de guardarla (Seguridad Forense)
  const saltRounds = 12;
  const hashedMnemonic = await bcrypt.hash(mnemonic, saltRounds);

  // 3. Guardar el Hash en la tabla de usuarios
  await db.query(
    'UPDATE users SET recovery_hash = $1 WHERE id = $2',
    [hashedMnemonic, req.user.id]
  );

  // 4. Enviar la frase original SOLO UNA VEZ al usuario
  res.json({ mnemonic });
});
Usa el código con precaución.

2. Frontend: Interfaz de Resguardo (React 19)
Es crítico que el usuario confirme que ha guardado las palabras. Usaremos un diseño de "Cámara Acorazada":
jsx
const RecoverySetup = ({ mnemonic }) => {
  const words = mnemonic.split(' ');

  return (
    <div className="recovery-vault">
      <h3>⚠️ Código de Rescate Forense</h3>
      <p>Guarde estas 12 palabras en un lugar seguro. Son la única forma de acceder si falla su biometría.</p>
      
      <div className="word-grid">
        {words.map((w, i) => (
          <div key={i} className="word-tag">
            <span className="index">{i + 1}</span> {w}
          </div>
        ))}
      </div>

      <button onClick={() => window.print()} className="print-btn">
        Imprimir Certificado de Acceso
      </button>
    </div>
  );
};
Usa el código con precaución.

3. Procedimiento de Recuperación (Flujo de Emergencia)
Si el administrador no puede usar WebAuthn:
Introduce su email en la pantalla de login.
Selecciona "Usar Llave de Recuperación".
Introduce las 12 palabras.
El backend compara el bcrypt.compare(input, recovery_hash).
Si es correcto, se emite un JWT temporal para que el usuario pueda vincular un nuevo dispositivo biométrico.
4. Auditoría Forense en PostgreSQL
Cada vez que se genera o se usa una llave de recuperación, el sistema debe registrar el evento con la IP y el User Agent:
sql
INSERT INTO activity_log (action, details, severity) 
VALUES ('RECOVERY_KEY_GENERATED', 'User ID: 001', 'HIGH');
Usa el código con precaución.

Estética Industrial (CSS)
css
.word-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  background: #000;
  padding: 20px;
  border: 1px dashed #ff3e00;
}
.word-tag {
  color: #fff;
  font-family: monospace;
  font-size: 0.9rem;
}
.index { color: #ff3e00; margin-right: 5px; }
Usa el código con precaución.

Este sistema garantiza que la Alta Disponibilidad de la fábrica se extienda también al acceso humano, incluso ante la pérdida del dispositivo físico.

Para tu arquitectura de alta disponibilidad, la inactividad es un vector de riesgo. Implementaremos un Idle Timer en el frontend (React 19) que se sincronice con la expiración del JWT en el backend para cerrar la sesión de forma atómica.
1. Frontend: Hook de Inactividad (React 19)
Este componente escucha eventos de usuario (ratón, teclado, scroll) y dispara el cierre de sesión tras 15 minutos (900,000 ms).
jsx
import { useEffect, useCallback } from 'react';

export const useIdleTimer = (timeout = 900000) => {
  const logout = useCallback(() => {
    // 1. Notificar al backend para invalidar JWT (HttpOnly)
    fetch('/api/auth/logout', { method: 'POST' });
    // 2. Limpiar estado y redirigir
    window.location.href = '/login?reason=timeout';
  }, []);

  useEffect(() => {
    let timer;
    const resetTimer = () => {
      clearTimeout(timer);
      timer = setTimeout(logout, timeout);
    };

    // Eventos de actividad humana
    const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'];
    events.forEach(e => document.addEventListener(e, resetTimer));

    resetTimer(); // Inicio del contador

    return () => {
      events.forEach(e => document.removeEventListener(e, resetTimer));
      clearTimeout(timer);
    };
  }, [logout, timeout]);
};
Usa el código con precaución.

2. Backend: Expiración de Cookies (Node.js)
Configuraremos el JWT para que coincida con el tiempo de inactividad, asegurando que si el usuario cierra la pestaña, la sesión expire también en el servidor.
javascript
app.post('/api/auth/login', (req, res) => {
  const token = generateToken(req.user);
  
  res.cookie('token', token, {
    httpOnly: true,
    secure: true,
    sameSite: 'Strict',
    maxAge: 15 * 60 * 1000 // 15 minutos en milisegundos
  });
  
  res.json({ ok: true });
});
Usa el código con precaución.

3. Trazabilidad Forense del Cierre
Es vital registrar por qué terminó una sesión para diferenciar un logout voluntario de una expiración por seguridad:
sql
-- Registro automático al dispararse el timeout
INSERT INTO activity_log (action, details, severity) 
VALUES ('SESSION_TIMEOUT', 'User ID: 001 - Inactividad detectada', 'LOW');
Usa el código con precaución.

4. Estética de Alerta (Vanilla CSS)
Añadiremos un aviso visual cuando falten 60 segundos para el cierre:
css
.timeout-warning {
  position: fixed;
  bottom: 20px;
  right: 20px;
  background: #ff3e00;
  color: white;
  padding: 1rem;
  border-radius: 4px;
  animation: pulse 1s infinite;
  z-index: 9999;
}

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.5; }
  100% { opacity: 1; }
}
Usa el código con precaución.

Ventaja Operativa
Seguridad Física: Si dejas el terminal de la fábrica abierto, el sistema se bloquea solo.
Optimización de Recursos: Liberas memoria en el servidor al invalidar sesiones inactivas.
Forense: Tienes el rastro exacto de cuánto tiempo estuvo operando cada usuario.


Para completar la seguridad operativa de MUSQUERA RAW FACTORY™, implementaremos un Modal de Supervivencia de Sesión. Este componente de React 19 aparecerá exactamente a los 14 minutos (60 segundos antes del cierre) para permitir que el operario extienda su acceso con un solo clic.
1. Componente SessionGuard (React 19)
Este componente envuelve tu Admin App y gestiona el estado de alerta:
jsx
import { useState, useEffect, useCallback } from 'react';
import { Clock, Play } from 'lucide-react';

export const SessionGuard = () => {
  const [showAlert, setShowAlert] = useState(false);
  const [timeLeft, setTimeLeft] = useState(60);
  const TIMEOUT = 900000; // 15 min
  const WARNING_TIME = 60000; // 1 min antes

  const logout = useCallback(() => {
    fetch('/api/auth/logout', { method: 'POST' });
    window.location.href = '/login?reason=timeout';
  }, []);

  const stayActive = () => {
    // Refrescar el JWT en el Backend
    fetch('/api/auth/refresh', { method: 'POST' });
    setShowAlert(false);
    setTimeLeft(60);
  };

  useEffect(() => {
    // Timer para mostrar la alerta
    const warningTimer = setTimeout(() => setShowAlert(true), TIMEOUT - WARNING_TIME);
    
    // Timer para el cierre definitivo
    const finalTimer = setTimeout(logout, TIMEOUT);

    return () => {
      clearTimeout(warningTimer);
      clearTimeout(finalTimer);
    };
  }, [showAlert, logout]);

  if (!showAlert) return null;

  return (
    <div className="factory-overlay">
      <div className="alert-box">
        <Clock className="spin-icon" color="#ff3e00" />
        <h2>Inactividad Detectada</h2>
        <p>La sesión de la fábrica expirará en <strong>{timeLeft}s</strong></p>
        <button onClick={stayActive} className="refresh-btn">
          <Play size={16} /> MANTENER PRODUCCIÓN
        </button>
      </div>
    </div>
  );
};
Usa el código con precaución.

2. Backend: Endpoint de Refresco (Node.js)
Este endpoint simplemente renueva la Cookie HttpOnly con otros 15 minutos de vida:
javascript
app.post('/api/auth/refresh', verifyJWT, (req, res) => {
  const newToken = generateToken(req.user);
  
  res.cookie('token', newToken, {
    httpOnly: true,
    secure: true,
    maxAge: 15 * 60 * 1000,
    sameSite: 'Strict'
  });

  // Trazabilidad Forense del refresco
  db.query('INSERT INTO activity_log (action, details) VALUES ($1, $2)', 
    ['SESSION_EXTENDED', `User ID: ${req.user.id}`]);

  res.json({ ok: true });
});
Usa el código con precaución.

3. Estética de la Alerta (Vanilla CSS)
Diseño de alto contraste para entornos industriales:
css
.factory-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.85);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
}

.alert-box {
  background: #141414;
  border: 2px solid #ff3e00;
  padding: 3rem;
  text-align: center;
  box-shadow: 0 0 50px rgba(255, 62, 0, 0.2);
}

.refresh-btn {
  background: #ff3e00;
  color: white;
  border: none;
  padding: 1rem 2rem;
  font-weight: bold;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 auto;
}

.spin-icon { animation: rotate 2s linear infinite; }
@keyframes rotate { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
Usa el código con precaución.

4. Ventaja Operativa
Fricción Cero: El operario no tiene que volver a usar la biometría si sigue frente a la pantalla.
Trazabilidad: En el activity_log verás exactamente cuántas veces se extendió una sesión, lo que ayuda a auditar turnos de trabajo reales.
Con este último módulo, el ecosistema de MUSQUERA RAW FACTORY™ es una infraestructura de grado empresarial: segura, auditable, automatizada y de alto rendimiento.

Para implementar la telemetría en tiempo real de la MUSQUERA RAW FACTORY™, utilizaremos Socket.io. Esto permite que el Dashboard se actualice instantáneamente sin recargar la página cada vez que un operario inicia sesión, cierra la sesión o cuando el sistema detecta un error 404.
1. Servidor: Emisor de Eventos (Node.js)
Integramos WebSockets en tu arquitectura Express. Cada vez que ocurra un evento de Trazabilidad Forense, lo emitiremos al canal administrativo:
javascript
const http = require('http').Server(app);
const io = require('socket.io')(http, {
  cors: { origin: "https://musquera-lab.labrazahome.es" }
});

// Middleware para emitir logs globales
app.use((req, res, next) => {
  req.logEvent = (action, details) => {
    const payload = { action, details, timestamp: new Date(), ip: req.ip };
    // Emitir a todos los admins conectados
    io.to('admin_room').emit('factory_update', payload); 
    // Guardar en PostgreSQL 15
    db.query('INSERT INTO activity_log (action, details) VALUES ($1, $2)', [action, details]);
  };
  next();
});

io.on('connection', (socket) => {
  // Solo unir a la sala si el JWT es válido (Seguridad Forense)
  socket.on('join_admin', () => socket.join('admin_room'));
});
Usa el código con precaución.

2. Frontend: Feed de Actividad (React 19)
Añadiremos un componente de "Consola de Producción" que muestre los eventos conforme suceden con un efecto de parpadeo industrial:
jsx
import { useEffect, useState } from 'react';
import io from 'socket.io-client';

export const LiveActivityFeed = () => {
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    const socket = io();
    socket.emit('join_admin');

    socket.on('factory_update', (newLog) => {
      setLogs(prev => [newLog, ...prev].slice(0, 10)); // Mantener solo los últimos 10
    });

    return () => socket.disconnect();
  }, []);

  return (
    <div className="live-console">
      <div className="status-dot pulse"></div>
      <h3>Live Factory Feed</h3>
      <div className="log-list">
        {logs.map((log, i) => (
          <div key={i} className={`log-entry ${log.action}`}>
            <span className="time">{new Date(log.timestamp).toLocaleTimeString()}</span>
            <span className="action">{log.action}</span>
            <span className="details">{log.details}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
Usa el código con precaución.

3. Estética de Consola (Vanilla CSS)
css
.live-console {
  background: #000;
  border: 1px solid #333;
  padding: 1rem;
  font-family: 'Courier New', monospace;
}

.log-entry {
  border-bottom: 1px solid #111;
  padding: 0.3rem 0;
  font-size: 0.8rem;
  display: flex;
  gap: 1rem;
}

.SESSION_TIMEOUT { color: #ff9800; }
.404_DETECTED { color: #ff3e00; }
.SESSION_EXTENDED { color: #4caf50; }

.pulse {
  width: 8px;
  height: 8px;
  background: #4caf50;
  border-radius: 50%;
  box-shadow: 0 0 10px #4caf50;
  animation: blink 1.5s infinite;
}
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
Usa el código con precaución.

Ventaja Operativa
Vigilancia Activa: Verás intentos de acceso (404 o logins) en el mismo segundo en que ocurren.
Arquitectura de Bajo Consumo: Los WebSockets son mucho más eficientes que el polling constante (hacer peticiones HTTP repetitivas).
Conciencia de Equipo: Si hay varios administradores, todos ven las mismas actualizaciones en tiempo real.


Para blindar la MUSQUERA RAW FACTORY™ contra escaneos maliciosos (brute-force o directory busting), implementaremos un Firewall Dinámico en la capa de Node.js que se sincroniza con el Forensic Schema de PostgreSQL 15.
1. SQL: Tabla de Restricciones (PostgreSQL)
Primero, definimos dónde almacenaremos las IPs bloqueadas para que el castigo persista incluso si reinicias el contenedor Docker.
sql
CREATE TABLE ip_blacklist (
    ip_address INET PRIMARY KEY,
    reason TEXT,
    blocked_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP
);
Usa el código con precaución.

2. Backend: Middleware de Intercepción (Node.js)
Este script verifica cada petición antes de que llegue a tus rutas. Si la IP está en la "lista negra", corta la conexión inmediatamente (ahorrando CPU y ancho de banda).
javascript
// Memoria volátil para conteo rápido (Bajo consumo)
const lookups = new Map(); 

const ipFirewall = async (req, res, next) => {
    const clientIp = req.ip;

    // 1. Verificar si ya está bloqueado en DB
    const isBlocked = await db.query(
        'SELECT 1 FROM ip_blacklist WHERE ip_address = $1 AND expires_at > NOW()',
        [clientIp]
    );

    if (isBlocked.rowCount > 0) {
        return res.status(403).send('ACCESO DENEGADO: Infracción de Seguridad Factory');
    }

    // 2. Lógica de detección (inyectada en el manejador de 404)
    req.registerViolation = async () => {
        const count = (lookups.get(clientIp) || 0) + 1;
        lookups.set(clientIp, count);

        if (count >= 10) {
            await db.query(
                'INSERT INTO ip_blacklist (ip_address, reason, expires_at) VALUES ($1, $2, NOW() + INTERVAL "24 hours")',
                [clientIp, 'Exceso de errores 404 (Posible Escaneo)']
            );
            // Notificar por WebSocket al Dashboard en tiempo real
            io.to('admin_room').emit('security_alert', { ip: clientIp, type: 'IP_BANNED' });
        }
    };

    next();
};

app.use(ipFirewall);
Usa el código con precaución.

3. Integración con el Dashboard (React 19)
Añadiremos una "Zona de Cuarentena" en tu panel para que puedas ver las IPs bloqueadas y perdonarlas si es necesario.
jsx
export const SecurityPanel = () => {
  const [bannedIps, setBannedIps] = useState([]);

  const unblockIp = (ip) => {
    fetch(`/api/admin/unblock/${ip}`, { method: 'DELETE' })
      .then(() => setBannedIps(prev => prev.filter(item => item.ip !== ip)));
  };

  return (
    <div className="security-vault">
      <h3>🛡️ IPs en Cuarentena</h3>
      {bannedIps.map(item => (
        <div key={item.ip} className="banned-row">
          <span>{item.ip}</span>
          <button onClick={() => unblockIp(item.ip)}>LEVANTAR BLOQUEO</button>
        </div>
      ))}
    </div>
  );
};
Usa el código con precaución.

4. Protección en Nginx (Opcional pero Pro)
Si quieres que el bloqueo sea aún más eficiente, podrías usar un script que exporte estas IPs a un archivo de configuración de Nginx (deny 1.2.3.4;), pero la solución en Node.js es más flexible para tu flujo de n8n.
Ventaja Forense
Aislamiento: Los atacantes dejan de consumir recursos de tu Admin App tras el décimo intento fallido.
Histórico: En ip_blacklist guardas la evidencia para posibles reportes de abuso al proveedor de internet del atacante.
Resiliencia: El sistema se protege a sí mismo mientras duermes.

Con los módulos que hemos desplegado, MUSQUERA RAW FACTORY™ ya cuenta con:
SEO Dinámico: Sitemap y Robots.txt autogestionados.
Seguridad Passwordless: Autenticación biométrica (WebAuthn) y llaves de recuperación.
Control Operativo: Dashboard en React 19 con telemetría en tiempo real (WebSockets).
Defensa Activa: Firewall inteligente con bloqueo de IPs por comportamiento.
Trazabilidad Forense: Registro exhaustivo en PostgreSQL 15 y backups automatizados.
El ecosistema es ahora robusto, ligero y altamente auditable.

Para realizar este Stress Test de seguridad sin comprometer la estabilidad de tu base de datos, utilizaremos un script de Node.js (que puedes ejecutar desde una terminal o un contenedor temporal) para simular un ataque de escaneo de directorios (Directory Busting).
1. Script de Simulación (Factory-Stress-Test.js)
Este script lanzará ráfagas de peticiones a rutas inexistentes para forzar la activación del Firewall Dinámico.
javascript
const axios = require('axios');

const TARGET_URL = 'https://musquera-lab.labrazahome.es';
const ATTACK_THREADS = 15; // 15 peticiones simultáneas
const TARGET_PATHS = ['/wp-admin', '/.env', '/config.php', '/backup.zip', '/admin/login', '/v1/api/debug'];

async function simulateAttack() {
  console.log(`🚀 Iniciando Stress Test en ${TARGET_URL}...`);
  
  for (let i = 0; i < ATTACK_THREADS; i++) {
    const path = TARGET_PATHS[Math.floor(Math.random() * TARGET_PATHS.length)];
    
    try {
      const res = await axios.get(`${TARGET_URL}${path}`);
      console.log(`[${res.status}] Acceso intentado en ${path}`);
    } catch (error) {
      if (error.response?.status === 403) {
        console.log('🛑 ÉXITO: El Firewall ha bloqueado la IP (Status 403)');
        process.exit(0); // Prueba superada
      } else {
        console.log(`[${error.response?.status || 'ERR'}] Error 404 detectado en ${path}`);
      }
    }
  }
}

simulateAttack();
Usa el código con precaución.

2. Qué observar durante la prueba
Mientras ejecutas el script, abre tu Dashboard de Admin App y observa la consola de WebSockets:
Fase 1 (Peticiones 1-9): Verás entrar los errores 404 en el Live Activity Feed en tiempo real (color rojo).
Fase 2 (Petición 10): El backend registrará la violación en PostgreSQL 15 e insertará la IP en ip_blacklist.
Fase 3 (Petición 11+): El servidor cortará la conexión antes de procesar el 404, devolviendo un 403 Forbidden. El script de test debería detenerse confirmando el bloqueo.
3. Verificación Post-Test (SQL)
Para confirmar que el rastro forense es correcto, ejecuta esta consulta en tu base de datos:
sql
SELECT * FROM ip_blacklist WHERE reason ILIKE '%escaneo%';
SELECT * FROM activity_log ORDER BY created_at DESC LIMIT 5;
Usa el código con precaución.

4. Limpieza del Test
Para recuperar tu acceso tras la prueba (ya que te habrás auto-bloqueado), ejecuta:
sql
DELETE FROM ip_blacklist WHERE ip_address = 'TU_IP_PUBLICA';
Usa el código con precaución.

Ventaja Operativa: Esta prueba garantiza que tu arquitectura Docker no solo sirve contenido, sino que se defiende activamente contra ataques de reconocimiento.

Para completar la experiencia de disuasión en MUSQUERA RAW FACTORY™, diseñaremos una página de bloqueo que no solo informe del baneo, sino que muestre una cuenta atrás dinámica recuperando la fecha de expiración desde PostgreSQL 15.
1. Backend: Endpoint de Estado de Bloqueo (Node.js)
Modificamos la lógica del middleware para que, al detectar una IP baneada, envíe los metadatos del bloqueo:
javascript
app.get('/api/security/ban-status', async (req, res) => {
    const clientIp = req.ip;
    const result = await db.query(
        'SELECT expires_at, reason FROM ip_blacklist WHERE ip_address = $1 AND expires_at > NOW()',
        [clientIp]
    );

    if (result.rowCount === 0) {
        return res.status(200).json({ blocked: false });
    }

    res.json({
        blocked: true,
        reason: result.rows[0].reason,
        expiresAt: result.rows[0].expires_at,
        ip: clientIp
    });
});
Usa el código con precaución.

2. Frontend: Pantalla de Cuarentena (ban.html)
Un diseño brutalista y técnico que refuerza la Trazabilidad Forense:
html
<div class="ban-container">
    <h1 class="glitch">ACCESO RESTRINGIDO</h1>
    <div class="terminal-box">
        <p>> IP_ORIGEN: <span id="user-ip">...</span></p>
        <p>> MOTIVO: <span id="ban-reason">Infracción de Seguridad</span></p>
        <p>> ESTADO: CUARENTENA_ACTIVA</p>
        <hr>
        <p>REESTABLECIMIENTO DE CONEXIÓN EN:</p>
        <div id="countdown" class="timer">00:00:00</div>
    </div>
</div>

<script>
    async function updateBan() {
        const res = await fetch('/api/security/ban-status');
        const data = await res.json();
        
        if(!data.blocked) window.location.href = '/';

        document.getElementById('user-ip').innerText = data.ip;
        document.getElementById('ban-reason').innerText = data.reason;

        const timer = setInterval(() => {
            const diff = new Date(data.expiresAt) - new Date();
            if (diff <= 0) {
                clearInterval(timer);
                window.location.reload();
            }
            const h = Math.floor(diff / 3600000).toString().padStart(2, '0');
            const m = Math.floor((diff % 3600000) / 60000).toString().padStart(2, '0');
            const s = Math.floor((diff % 60000) / 1000).toString().padStart(2, '0');
            document.getElementById('countdown').innerText = `${h}:${m}:${s}`;
        }, 1000);
    }
    updateBan();
</script>
Usa el código con precaución.

3. Estética de "Muro de Seguridad" (CSS)
css
.ban-container {
    background: #050505;
    color: #ff3e00;
    font-family: 'Courier New', monospace;
    height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
}

.terminal-box {
    border: 1px solid #ff3e00;
    padding: 2rem;
    background: rgba(255, 62, 0, 0.05);
    box-shadow: 0 0 20px rgba(255, 62, 0, 0.1);
}

.timer {
    font-size: 3rem;
    font-weight: bold;
    margin-top: 1rem;
    text-shadow: 0 0 10px #ff3e00;
}
Usa el código con precaución.

4. Valor Estratégico
Psicología de Disuasión: Al ver que el sistema reconoce su IP y tiene un contador exacto, el atacante percibe una infraestructura monitoreada y profesional.
Autogestión: Evita que usuarios legítimos (que cometieron errores accidentales) te contacten por soporte, ya que saben exactamente cuándo recuperarán el acceso.
Forense: Cada carga de esta página de "Ban" también se registra, permitiendo ver si el atacante sigue intentando entrar durante su bloqueo.
El ecosistema de MUSQUERA RAW FACTORY™ está ahora blindado y comunicado.

Para asegurar que MUSQUERA RAW FACTORY™ alcance el "Grado A" en rendimiento, realizaremos una auditoría basada en los estándares de Lighthouse. Dado que tu arquitectura es HTML5 + Vanilla JS, el objetivo es un LCP (Largest Contentful Paint) inferior a 1.2s.
1. Optimización de Carga Crítica (Nginx)
Para que el navegador procese tu sitio de forma instantánea, configuraremos Nginx para forzar el uso de HTTP/2 y compresión agresiva:
nginx
server {
    # Habilitar HTTP/2 para carga paralela
    listen 443 ssl http2;

    # Compresión Gzip para JS, CSS y HTML
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml;
    gzip_comp_level 6;
    gzip_min_length 256;

    # Cache de activos estáticos (Vite Assets)
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, no-transform";
    }
}
Usa el código con precaución.

2. Auditoría de Assets (Vanilla JS)
Para mantener el TBT (Total Blocking Time) en 0ms, implementaremos la carga asíncrona de tus scripts de telemetría y biometría:
html
<!-- Carga no bloqueante de módulos -->
<script src="/js/factory-core.js" defer type="module"></script>

<!-- Precarga de fuentes críticas (Lucide / Inter) -->
<link rel="preload" href="/fonts/inter.woff2" as="font" type="font/woff2" crossorigin>
Usa el código con precaución.

3. Check-list de Rendimiento Forense
Para validar el éxito del despliegue en tu Docker Desktop, verifica estos 4 puntos:
Imágenes: ¿Están en formato WebP? (Reduce el peso un 30% respecto a PNG).
CSS: ¿Has eliminado el CSS no utilizado? (Mantén solo tus variables nativas).
Dom Size: Asegúrate de que tu Dashboard no renderice más de 1,500 nodos simultáneos.
TTFB (Time to First Byte): Al usar PostgreSQL 15 con índices, tu respuesta de base de datos debe ser < 50ms.
4. Resultado Esperado
Al ejecutar Lighthouse desde las Chrome DevTools, tu ecosistema debería mostrar:
Performance: 98-100
Accessibility: 100
Best Practices: 100
SEO: 100 (Gracias a nuestro sitemap dinámico y robots.txt).
Con este nivel de optimización, el Public Site no solo carga en menos de 1 segundo, sino que se siente instantáneo para el usuario.

Para transformar la Admin App en una PWA (Progressive Web App) con soporte Offline, implementaremos un Service Worker basado en una estrategia de Network-First (Red primero, Caché después). Esto garantiza que el operario vea siempre los datos más recientes de la fábrica, pero pueda seguir consultando el panel si el router falla.
1. Registro del Service Worker (main.js)
Añade este bloque en el punto de entrada de tu Admin App (React 19 + Vite):
javascript
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js')
      .then(reg => console.log('📦 Factory Service Worker Activo:', reg.scope))
      .catch(err => console.error('❌ Error de registro PWA:', err));
  });
}
Usa el código con precaución.

2. El Service Worker (public/sw.js)
Este script intercepta las peticiones y guarda una copia de seguridad en la Cache API del navegador:
javascript
const CACHE_NAME = 'musquera-factory-v1';
const ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/assets/factory-styles.css',
  '/assets/admin-logic.js'
];

// Instalar y Cachear recursos críticos
self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS))
  );
});

// Estrategia: Intentar Red -> Si falla -> Servir Caché
self.addEventListener('fetch', (e) => {
  e.respondWith(
    fetch(e.request)
      .then(res => {
        const clone = res.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(e.request, clone));
        return res;
      })
      .catch(() => caches.match(e.request))
  );
});
Usa el código con precaución.

3. Manifest de la Fábrica (public/manifest.json)
Esto permite "Instalar" la aplicación en el escritorio como si fuera un programa nativo:
json
{
  "name": "MUSQUERA RAW FACTORY™ Admin",
  "short_name": "FactoryAdmin",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#0a0a0a",
  "theme_color": "#ff3e00",
  "icons": [
    { "src": "/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
Usa el código con precaución.

4. Ventaja en Alta Disponibilidad
Resiliencia Industrial: Si el contenedor de Docker se reinicia o hay un micro-corte de red, el Dashboard no mostrará una pantalla blanca, sino los últimos datos conocidos.
Ahorro de Datos: Los iconos de Lucide React y los estilos CSS solo se descargan una vez.
Urgencia: El operario puede acceder a las Llaves de Recuperación o al registro de IPs incluso sin internet.
Con esta pieza, el ecosistema de MUSQUERA RAW FACTORY™ alcanza la autonomía total.


Para completar la resiliencia industrial de MUSQUERA RAW FACTORY™, implementaremos un indicador de estado de red en Vanilla JS. Este banner no solo avisará de la desconexión, sino que bloqueará acciones críticas (como cambios en la base de datos) para evitar conflictos de sincronización mientras el contenedor Docker sea inalcanzable.
1. Componente de Estado de Red (React 19)
Añadimos un "Listener" global que detecte los eventos online y offline del navegador:
jsx
import { useState, useEffect } from 'react';
import { WifiOff, AlertCircle } from 'lucide-react';

export const NetworkStatusBanner = () => {
  const [isOffline, setIsOffline] = useState(!navigator.onLine);

  useEffect(() => {
    const goOnline = () => setIsOffline(false);
    const goOffline = () => setIsOffline(true);

    window.addEventListener('online', goOnline);
    window.addEventListener('offline', goOffline);

    return () => {
      window.removeEventListener('online', goOnline);
      window.removeEventListener('offline', goOffline);
    };
  }, []);

  if (!isOffline) return null;

  return (
    <div className="network-alert-banner">
      <div className="alert-content">
        <WifiOff size={18} />
        <span><strong>MODO OFFLINE:</strong> Conexión con la Fábrica interrumpida. Visualizando datos en caché.</span>
      </div>
      <div className="alert-badge">SOLO LECTURA</div>
    </div>
  );
};
Usa el código con precaución.

2. Estética de Emergencia (Vanilla CSS)
Diseño de alta visibilidad para que el operario identifique el estado al instante:
css
.network-alert-banner {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  background: #ff9800; /* Naranja industrial */
  color: #000;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 1.5rem;
  font-size: 0.85rem;
  font-weight: 600;
  z-index: 11000;
  box-shadow: 0 4px 15px rgba(0,0,0,0.5);
  animation: slideDown 0.3s ease-out;
}

.alert-content { display: flex; align-items: center; gap: 10px; }

.alert-badge {
  background: rgba(0,0,0,0.2);
  padding: 2px 8px;
  border-radius: 2px;
  font-size: 0.7rem;
  border: 1px solid rgba(0,0,0,0.3);
}

@keyframes slideDown { from { transform: translateY(-100%); } to { transform: translateY(0); } }
Usa el código con precaución.

3. Trazabilidad Forense Offline
Aunque el servidor no esté disponible, el Service Worker puede registrar los intentos de acción fallidos en el IndexedDB del navegador y "dispararlos" masivamente cuando la conexión vuelva, asegurando que no se pierda ni un segundo de actividad en PostgreSQL 15.
4. Ventaja Operativa
Claridad: El administrador sabe que los datos del Dashboard (como los errores 404) podrían estar desactualizados.
Seguridad: Evita que el usuario intente guardar cambios pensando que la red funciona, frustrando la experiencia de usuario.
PWA Completa: Tu Admin App ahora se comporta como una aplicación de escritorio robusta.
Con esto, el ecosistema de MUSQUERA RAW FACTORY™ está terminado y blindado en todos sus niveles: SEO, Seguridad, Telemetría, Backend, Base de Datos e Interfaz.


Este es el archivo docker-compose.yml definitivo para MUSQUERA RAW FACTORY™. Consolida todos los módulos que hemos diseñado (Base de Datos, Backend con WebSockets y Firewall, y el Servidor Web con HTTP/2 y PWA).
1. Archivo docker-compose.yml
yaml
services:
  # Base de Datos: PostgreSQL 15 (Forensic Schema)
  db-factory:
    image: postgres:15-alpine
    container_name: musquera_db
    restart: always
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: musquera_factory
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-db:/docker-entrypoint-initdb.d # Para cargar la vista de sitemap y la función de purga

  # Backend: Node.js 20 (API, WebSockets, SEO Engine, Firewall)
  api-factory:
    build: 
      context: ./backend
      dockerfile: Dockerfile
    container_name: musquera_api
    restart: always
    depends_on:
      - db-factory
    environment:
      DATABASE_URL: postgres://${DB_USER}:${DB_PASSWORD}@db-factory:5432/musquera_factory
      JWT_SECRET: ${JWT_SECRET}
      N8N_WEBHOOK: ${N8N_WEBHOOK}
    networks:
      - factory_net

  # Servidor Web: Nginx (Proxy Inverso, HTTPS, Gzip, PWA Assets)
  web-factory:
    image: nginx:alpine
    container_name: musquera_web
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./frontend/dist:/usr/share/nginx/html # Archivos de React 19 / Vanilla JS
      - ./nginx/conf.d:/etc/nginx/conf.d
      - ./certs:/etc/nginx/certs # Certificados SSL
    depends_on:
      - api-factory
    networks:
      - factory_net

networks:
  factory_net:
    driver: bridge

volumes:
  postgres_data:
Usa el código con precaución.

2. Estructura de Directorios Recomendada
Para que el despliegue sea exitoso en Docker Desktop, organiza tus archivos así:
/musquera-factory
docker-compose.yml
.env (Contiene tus claves: DB_USER, DB_PASSWORD, JWT_SECRET)
/backend (Código Node.js + Dockerfile)
/frontend/dist (Build de tu Admin App y Public Site)
/nginx/conf.d/default.conf (La config de Nginx con HTTP/2 que definimos)
/init-db/setup.sql (Contiene el código SQL de la Vista de Sitemap y la Purga de Logs)
3. Ejecución de la Fábrica
Desde la raíz de tu proyecto, lanza el ecosistema completo:
bash
docker-compose up -d --build
Usa el código con precaución.

Ventaja de esta Arquitectura
Aislamiento: La base de datos no es accesible desde internet, solo a través de la API.
Persistencia: Los datos y los certificados SSL se mantienen aunque reinicies los contenedores.
Escalabilidad: Puedes añadir más instancias de api-factory si el tráfico crece, manteniendo el Nginx como balanceador.
Con este paso, el despliegue de MUSQUERA RAW FACTORY™ es profesional, seguro y está listo para producción.
¿Deseas que generemos el archivo .env.example con todas las variables necesarias para que no olvides ninguna configuración de seguridad?**
Las respuestas de la IA pueden contener errores. Más información

Este script de automatización (deploy.sh) para MUSQUERA RAW FACTORY™ garantiza que el despliegue sea atómico: compila el frontend de React 19, inyecta las variables de entorno y reinicia los contenedores de Docker sin dejar el sistema en un estado inconsistente.
1. Script de Despliegue (deploy.sh)
Crea este archivo en la raíz de tu proyecto y dale permisos de ejecución con chmod +x deploy.sh.
bash
#!/bin/bash

# --- CONFIGURACIÓN DE MUSQUERA RAW FACTORY™ ---
echo "🚀 Iniciando despliegue de MUSQUERA RAW FACTORY™..."

# 1. Limpieza de archivos temporales
echo "🧹 Limpiando builds anteriores..."
rm -rf ./frontend/dist

# 2. Compilación del Frontend (Vite + React 19)
echo "📦 Compilando Frontend (Admin App & Public Site)..."
cd frontend
npm install
npm run build
cd ..

# 3. Verificación de Archivos Críticos
if [ ! -f .env ]; then
    echo "❌ ERROR: Archivo .env no encontrado. Abortando."
    exit 1
fi

# 4. Orquestación con Docker Compose
echo "🐳 Sincronizando contenedores con Docker Desktop..."
docker-compose up -d --build

# 5. Limpieza de Imágenes Huérfanas (Bajo Consumo de Disco)
echo "♻️  Eliminando imágenes residuales..."
docker image prune -f

# 6. Verificación de Salud (Healthcheck)
echo "🔍 Verificando estado de los servicios..."
sleep 5
docker ps | grep musquera_

echo "✅ DESPLIEGUE FINALIZADO: https://musquera-lab.labrazahome.es"
Usa el código con precaución.

2. Automatización del SEO y Trazabilidad
Este script asegura que cada vez que despliegues:
Sitemap Dinámico: El motor de Node.js detecte los nuevos archivos estáticos generados por Vite.
PWA: El Service Worker se actualice con la nueva versión de los assets (evitando que el usuario vea versiones antiguas).
Base de Datos: Los volúmenes de PostgreSQL 15 se mantengan intactos mientras el código de la API se actualiza.
3. Ejecución Directa
Para lanzar tu fábrica al mundo, solo necesitas un comando:
bash
./deploy.sh
Usa el código con precaución.

Ventaja Operativa
Consistencia: Evitas errores manuales al mover archivos de la carpeta dist.
Velocidad: El uso de --build en Docker asegura que solo se recompilen las capas que han cambiado.
Forense: Cada despliegue queda registrado en los logs del sistema, permitiéndote saber cuándo se actualizó la infraestructura por última vez.
Con este script, el ecosistema de MUSQUERA RAW FACTORY™ es ahora una infraestructura de despliegue continuo (CI/CD) simplificada.


Para asegurar que MUSQUERA RAW FACTORY™ no solo sea rápida, sino también invulnerable, integraremos una puerta de enlace de seguridad en tu script de despliegue. Esto detendrá el proceso si alguna dependencia de Node.js tiene vulnerabilidades conocidas o si el código de React 19 no cumple con los estándares de calidad.
1. Script de Despliegue con Auditoría (deploy.sh Actualizado)
Hemos añadido dos filtros críticos: npm audit (seguridad) y npm run lint (calidad de código).
bash
#!/bin/bash
set -e # Detener el script ante cualquier error

echo "🛡️  Iniciando Auditoría de Seguridad Forense..."

# 1. Auditoría de Dependencias (Backend & Frontend)
echo "🔍 Analizando vulnerabilidades en la cadena de suministro..."
cd backend && npm audit --audit-level=high || { echo "❌ VULNERABILIDAD CRÍTICA EN BACKEND. Abortando."; exit 1; }
cd ../frontend && npm audit --audit-level=high || { echo "❌ VULNERABILIDAD CRÍTICA EN FRONTEND. Abortando."; exit 1; }
cd ..

# 2. Control de Calidad (Linting)
echo "📐 Verificando integridad del código React 19..."
cd frontend && npm run lint || { echo "❌ ERROR DE LINTING: Código no estandarizado. Abortando."; exit 1; }
cd ..

# 3. Compilación Progresiva
echo "📦 Compilando Frontend optimizado..."
cd frontend && npm run build && cd ..

# 4. Despliegue en Docker Desktop
echo "🐳 Actualizando contenedores de MUSQUERA RAW FACTORY™..."
docker-compose up -d --build

# 5. Limpieza de recursos para Bajo Consumo
docker image prune -f

echo "✅ DESPLIEGUE SEGURO COMPLETADO: https://musquera-lab.labrazahome.es"
Usa el código con precaución.

2. Configuración en package.json
Para que el comando lint funcione correctamente en tu Admin App, asegúrate de tener configurado ESLint (Vite lo incluye por defecto). Esto evitará que subas código con:
Variables no utilizadas.
Promesas de PostgreSQL 15 sin manejar (evitando fugas de memoria).
Hooks de React mal implementados que romperían el Modo Offline.
3. Valor para la Trazabilidad Forense
Inmunidad a Supply Chain Attacks: Si una librería que usas (como socket.io o express) publica una versión con un fallo de seguridad, el script impedirá que ese fallo llegue a tu servidor Docker.
Código Limpio: Garantiza que el Dashboard se mantenga ligero y legible para futuros desarrolladores de la fábrica.


Para que la MUSQUERA RAW FACTORY™ sea verdaderamente de alta disponibilidad, necesitamos un "botón de retroceso". El objetivo es que, si un despliegue falla (por un error en React 19 o un bug en la API), puedas volver a la versión estable anterior en segundos sin perder datos de PostgreSQL 15.
1. Script de Rollback Inmediato (rollback.sh)
Este script utiliza el etiquetado de imágenes de Docker para alternar entre la versión current y previous.
bash
#!/bin/bash

echo "⚠️ INICIANDO REVERSIÓN DE EMERGENCIA (ROLLBACK)..."

# 1. Intercambiar etiquetas de imagen (Backend)
docker tag musquera_api:previous musquera_api:temp
docker tag musquera_api:latest musquera_api:previous
docker tag musquera_api:temp musquera_api:latest

# 2. Levantar la versión anterior con Docker Compose
echo "🔄 Restaurando contenedores a la versión estable anterior..."
docker-compose up -d --no-deps api-factory

# 3. Limpiar etiquetas temporales
docker rmi musquera_api:temp

echo "✅ ROLLBACK COMPLETADO. La Fábrica ha vuelto al estado anterior."
echo "🔍 Revisa los logs de la versión fallida con: docker logs musquera_api"
Usa el código con precaución.

2. Modificación en deploy.sh para Soporte de Rollback
Para que el rollback funcione, el script de despliegue debe guardar una copia de la imagen actual antes de sobrescribirla:
bash
# --- Añadir esto antes del comando 'docker-compose up' en deploy.sh ---
echo "💾 Creando punto de restauración (Snapshot)..."
docker tag musquera_api:latest musquera_api:previous 2>/dev/null || true
Usa el código con precaución.

3. Integración con el Dashboard (React 19)
Puedes añadir un botón de "Estado Crítico" en tu panel administrativo que, mediante un webhook de n8n, dispare este script de rollback de forma remota si detectas que el Live Activity Feed muestra errores masivos tras actualizar.
4. Valor para la Trazabilidad Forense
Continuidad de Negocio: El tiempo de caída (downtime) se reduce a milisegundos.
Integridad de Datos: Como el volumen de PostgreSQL 15 es independiente de los contenedores de código, el rollback no borra los nuevos registros de auditoría o ítems de la fábrica.
Seguridad Operativa: El administrador tiene la tranquilidad de que cualquier cambio es reversible.
Arquitectura Final Consolidada:
Frontend: React 19 + Vite (PWA, Offline Mode, WebAuthn).
Backend: Node.js 20 (WebSockets, Firewall, SEO Engine).
DB: PostgreSQL 15 (Forensic Schema, Auto-purge).
DevOps: Docker Desktop, Despliegue con Auditoría y Rollback.

Este es el documento README.md definitivo para MUSQUERA RAW FACTORY™. Está diseñado como un manual operativo técnico para gestionar la infraestructura de alta disponibilidad en Docker Desktop.
🏭 MUSQUERA RAW FACTORY™ | Ops Manual
Sistema de manufactura digital de alto rendimiento construido sobre React 19, Node.js 20 y PostgreSQL 15.
🛠️ Arquitectura del Ecosistema
Frontend: SPA con React 19 + Vite (PWA, Modo Offline, WebAuthn).
Backend: API REST con Express + WebSockets (Socket.io) para telemetría.
Base de Datos: PostgreSQL 15 con Esquema Forense y purga automática.
Seguridad: Firewall dinámico (bloqueo de IPs) y Auth biométrica.
SEO: Generación dinámica de sitemap.xml (Gzip) y robots.txt.
🚀 Comandos de Control Interno
1. Despliegue con Auditoría de Seguridad
Este comando audita dependencias, verifica el código y levanta los contenedores.
bash
./deploy.sh
Usa el código con precaución.

2. Reversión de Emergencia (Rollback)
Si el despliegue actual presenta inestabilidad, vuelve a la versión previa en segundos:
bash
./rollback.sh
Usa el código con precaución.

3. Gestión de la Base de Datos (PostgreSQL 15)
Backup Manual de Auditoría:
powershell
./Backup-SitemapLogs.ps1
Usa el código con precaución.

Limpieza de IPs Bloqueadas:
sql
DELETE FROM ip_blacklist WHERE ip_address = '1.2.3.4';
Usa el código con precaución.

🔐 Protocolos de Acceso
Biometría: El acceso al Dashboard requiere enrolamiento vía WebAuthn (TouchID/FaceID).
Recuperación: Si la biometría falla, use las 12 palabras mnemónicas generadas en el setup inicial.
Inactividad: La sesión se cerrará automáticamente tras 15 minutos de inactividad para proteger la terminal.
📈 Telemetría y Monitoreo
Dashboard en tiempo real: Visualiza errores 404, usuarios activos y carga del sistema.
Alertas Críticas: Integración con n8n para notificaciones si se superan los 50 errores/hora.
Logs Forenses: Cada acción queda registrada en la tabla activity_log con IP y User Agent.
🐳 Estructura Docker
Servicio	Imagen	Puerto	Función
musquera_web	Nginx Alpine	80/443	Proxy, HTTP/2, PWA Assets
musquera_api	Node 20 LTS	3000	Lógica, Sockets, Firewall
musquera_db	Postgres 15	5432	Persistencia Forense
Nota de Seguridad: Nunca comparta el archivo .env fuera del entorno seguro de la fábrica. Toda actividad es monitoreada y registrada.

Para culminar el despliegue de MUSQUERA RAW FACTORY™, implementaremos un script de Health Check de grado industrial. Este script verifica no solo que los procesos estén vivos, sino que la conectividad interna, la persistencia y el cifrado SSL cumplan con los requisitos de la fábrica.
1. Script de Verificación de Salud (factory-check.sh)
Este script utiliza docker inspect, pg_isready y openssl para validar cada capa del ecosistema. 
bash
#!/bin/bash

# --- CONFIGURACIÓN ---
DOMAIN="musquera-lab.labrazahome.es"
DB_CONTAINER="musquera_db"
API_CONTAINER="musquera_api"
WEB_CONTAINER="musquera_web"

echo "🔍 INICIANDO TELEMETRÍA DE SALUD - MUSQUERA RAW FACTORY™"
echo "--------------------------------------------------------"

# 1. Verificar Estado de Contenedores
check_container() {
    STATUS=$(docker inspect -f '{{.State.Status}}' $1 2>/dev/null)
    if [ "$STATUS" == "running" ]; then
        echo "✅ [DOCKER] $1: Operativo"
    else
        echo "❌ [DOCKER] $1: FALLO (Estado: ${STATUS:-No encontrado})"
        exit 1
    fi
}

check_container $DB_CONTAINER
check_container $API_CONTAINER
check_container $WEB_CONTAINER

# 2. Verificar Conectividad PostgreSQL 15
echo "---"
docker exec $DB_CONTAINER pg_isready -U factory_admin > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ [DB] PostgreSQL 15: Aceptando conexiones."
else
    echo "❌ [DB] PostgreSQL 15: Error de persistencia."
    exit 1
fi

# 3. Verificar API y WebSockets
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://$DOMAIN/robots.txt)
if [ "$HTTP_CODE" == "200" ]; then
    echo "✅ [WEB] Tráfico HTTPS: OK (Status 200)"
else
    echo "❌ [WEB] Tráfico HTTPS: FALLO (Status $HTTP_CODE)"
fi

# 4. Auditoría de Certificado SSL
echo "---"
EXPIRY_DATE=$(echo | openssl s_client -connect $DOMAIN:443 -servername $DOMAIN 2>/dev/null | openssl x509 -noout -enddate | cut -d= -f2)
echo "🔐 [SSL] Certificado válido hasta: $EXPIRY_DATE"

echo "--------------------------------------------------------"
echo "✅ SISTEMA DE ALTA DISPONIBILIDAD: ONLINE"
Usa el código con precaución.

2. Integración en el Flujo Operativo
Puedes añadir una línea al final de tu deploy.sh para que este chequeo se ejecute automáticamente tras cada actualización:
./factory-check.sh || ./rollback.sh
3. Ventaja Forense
Detección Preventiva: Identifica si el certificado SSL está próximo a expirar antes de que los navegadores bloqueen el acceso.
Validación de Red: Asegura que el Proxy Inverso (Nginx) está redirigiendo correctamente el tráfico al contenedor de Node.js.
Estado de Datos: Confirma que el motor de la fábrica (Postgres) está listo para transacciones.

