# AlbertSkillsAMDMulti — Documentación del proyecto
## Portal Multi-servicio AMD

---

## 1. Descripción
Aplicación web construida con React + Vite que sirve como portal multi-servicio. Interfaz moderna con animaciones fluídas (Framer Motion) y diseño responsive con Tailwind CSS.

## 2. Stack tecnológico
| Componente | Tecnología |
|------------|-----------|
| Frontend | React 19 + Vite 8 |
| UI/UX | Framer Motion, Tailwind CSS, Lucide React |
| Build | Vite + Rolldown |
| Servidor | nginx:alpine (sirve build estático) |
| Proxy | Traefik (AI-LAB) |

## 3. Arquitectura
```
Usuario → Cloudflare Tunnel → 192.168.1.30:80 → Traefik
                                                    ↓
                                        Host: skills.labrazahome.com
                                                    ↓
                                              nginx:alpine
                                                    ↓
                                    /opt/ai-lab/stacks/websites/albertskills-amd-multi/dist/
```

## 4. Despliegue
- **Ruta código:** `/opt/ai-lab/stacks/websites/albertskills-amd-multi/`
- **Contenedor:** `albertskills-amd-multi`
- **Imagen:** nginx:alpine
- **Puerto interno:** 80
- **Red:** `proxy`
- **Stack:** `stacks/websites/docker-compose.yml`
- **Dominio:** `skills.labrazahome.com`

## 5. Operación

### Iniciar
```bash
docker compose -f /opt/ai-lab/stacks/websites/docker-compose.yml up -d albertskills-amd-multi
```

### Reconstruir (tras cambios en el código fuente)
```bash
cd /opt/ai-lab/stacks/websites/albertskills-amd-multi
npm install
npm run build
docker compose -f /opt/ai-lab/stacks/websites/docker-compose.yml up -d albertskills-amd-multi
```

### Logs
```bash
docker logs albertskills-amd-multi --tail 50
```

### Backup
```bash
cp -r /opt/ai-lab/stacks/websites/albertskills-amd-multi /opt/ai-lab/snapshots/albertskills-amd-multi-$(date +%Y%m%d)
```

## 6. Archivos
```
albertskills-amd-multi/
├── src/                    # Código fuente React
├── public/                 # Assets públicos
├── dist/                   # Build de producción (sirve nginx)
├── package.json            # Dependencias
├── vite.config.js          # Configuración Vite
├── nginx.conf              # Config nginx legacy
├── Dockerfile              # Docker legacy
├── data/                   # Datos
├── letsencrypt/            # SSL legacy
└── .git/                   # Repositorio
```

## 7. Notas
- El contenedor sirve el contenido de `dist/` (build estático)
- Para cambios en el frontend: editar `src/`, ejecutar `npm run build` y reiniciar contenedor
- No requiere base de datos ni backend

## 8. Origen
- **Ubicación original:** `\\192.168.1.200\e\Webs\AlbertSkillsAMDMulti\AlbertSkillsAMDMulti`
- **Restaurado el:** 13/05/2026
- **Tamaño:** ~201 MB (con node_modules)
