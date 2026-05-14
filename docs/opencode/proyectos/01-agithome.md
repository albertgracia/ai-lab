# AGITHome — Documentación del proyecto
## Soluciones IT a domicilio

---

## 1. Descripción
Web corporativa de AG IT Home Services, empresa de soporte técnico IT a domicilio especializada en redes UniFi, WiFi profesional, migración 10Gb y seguridad informática.

## 2. Stack tecnológico
| Componente | Tecnología |
|------------|-----------|
| Frontend | HTML5 + CSS3 + JavaScript vanilla |
| Fuentes | Google Fonts (Plus Jakarta Sans, Inter, JetBrains Mono) |
| Servidor | nginx:alpine |
| Proxy | Traefik (AI-LAB) |

## 3. Arquitectura
```
Usuario → Cloudflare Tunnel → 192.168.1.30:80
                                    ↓
                               Traefik
                                    ↓
                        Host: agithome.labrazahome.com
                                    ↓
                             nginx:alpine
                                    ↓
                    /opt/ai-lab/stacks/websites/agithome/
```

## 4. Despliegue
- **Ruta código:** `/opt/ai-lab/stacks/websites/agithome/`
- **Contenedor:** `agithome`
- **Imagen:** nginx:alpine
- **Puerto interno:** 80
- **Red:** `proxy`
- **Stack:** `stacks/websites/docker-compose.yml`
- **Dominio:** `agithome.labrazahome.com`

## 5. Operación
```bash
# Iniciar
docker compose -f /opt/ai-lab/stacks/websites/docker-compose.yml up -d agithome

# Logs
docker logs agithome --tail 50

# Estado
docker ps --filter name=agithome

# Backup
cp -r /opt/ai-lab/stacks/websites/agithome /opt/ai-lab/snapshots/agithome-$(date +%Y%m%d)
```

## 6. Archivos
```
agithome/
├── index.html      # Página principal (53 KB)
├── styles.css      # Estilos (36 KB)
├── script.js       # Lógica JS (18 KB)
├── images/         # Assets
└── .git/           # Repositorio
```

## 7. Origen
- **Ubicación original:** `\\192.168.1.200\e\Webs\AGITHome`
- **Restaurado el:** 13/05/2026
- **Tamaño:** ~37 MB
