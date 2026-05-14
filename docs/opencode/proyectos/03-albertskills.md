# AlbertSkills — Documentación del proyecto
## Home-Cloud Solutions Architect — Portfolio

---

## 1. Descripción
Portfolio personal de Albert, Arquitecto de Soluciones Home-Cloud. Muestra infraestructura containerizada, observabilidad enterprise y redes UniFi gestionadas en producción 24/7.

## 2. Stack tecnológico
| Componente | Tecnología |
|------------|-----------|
| Frontend | HTML5 + Tailwind CSS + JavaScript |
| Fuentes | Google Fonts (Inter, JetBrains Mono) |
| Servidor | nginx:alpine |
| Proxy | Traefik (AI-LAB) |

## 3. Arquitectura
```
Usuario → Cloudflare Tunnel → 192.168.1.30:80 → Traefik
                                                    ↓
                                       Host: albertskills.labrazahome.com
                                                    ↓
                                              nginx:alpine
                                                    ↓
                                        /opt/ai-lab/stacks/websites/albertskills/
```

## 4. Despliegue
- **Ruta código:** `/opt/ai-lab/stacks/websites/albertskills/`
- **Contenedor:** `albertskills`
- **Imagen:** nginx:alpine
- **Puerto interno:** 80
- **Red:** `proxy`
- **Stack:** `stacks/websites/docker-compose.yml`
- **Dominio:** `albertskills.labrazahome.com`

## 5. Operación
```bash
# Iniciar
docker compose -f /opt/ai-lab/stacks/websites/docker-compose.yml up -d albertskills

# Logs
docker logs albertskills --tail 50

# Backup
cp -r /opt/ai-lab/stacks/websites/albertskills /opt/ai-lab/snapshots/albertskills-$(date +%Y%m%d)
```

## 6. Archivos
```
albertskills/
├── index.html              # Página principal (62 KB)
├── favicon.png             # Icono
├── assets/                 # Assets gráficos
├── dessign_info/           # Documentación de diseño
├── nginx/                  # Configuración nginx legacy
├── docker-compose.yml      # Docker legacy
└── .git/                   # Repositorio
```

## 7. Origen
- **Ubicación original:** `\\192.168.1.200\e\Webs\AlbertSkills\AlbertSkills`
- **Restaurado el:** 13/05/2026
- **Tamaño:** ~4 MB
