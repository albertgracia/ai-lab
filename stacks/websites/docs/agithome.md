# AGITHome — Documentación del proyecto
## Soluciones IT a domicilio

---

## 1. Descripción
Web corporativa de **AG IT Home Services**, empresa de soporte técnico IT a domicilio especializada en redes UniFi, WiFi profesional, migración 10Gb y seguridad informática.

## 2. Stack tecnológico
| Componente | Tecnología |
|------------|-----------|
| Frontend | HTML5 + CSS3 + JavaScript vanilla |
| Fuentes | Google Fonts (Plus Jakarta Sans, Inter, JetBrains Mono) |
| Servidor | nginx:alpine |
| Proxy | Traefik (en AI-LAB) |

## 3. Arquitectura
```
Usuario → Cloudflare Tunnel → 192.168.1.30:80 → Traefik
                                                    │
                                               agithome.labrazahome.com
                                                    │
                                              nginx:alpine
                                                    │
                                          /opt/ai-lab/stacks/websites/agithome/
                                              index.html, styles.css, script.js
```

## 4. Despliegue
- **Ruta código:** `/opt/ai-lab/stacks/websites/agithome/`
- **Contenedor:** `agithome` (nginx:alpine)
- **Puerto interno:** 80
- **Red:** `proxy` (Traefik)
- **Stack:** `/opt/ai-lab/stacks/websites/docker-compose.yml`
- **Dominio:** `agithome.labrazahome.com`

## 5. Operación

### Iniciar / Reiniciar
```bash
docker compose -f /opt/ai-lab/stacks/websites/docker-compose.yml up -d agithome
```

### Logs
```bash
docker logs agithome --tail 50
```

### Ver estado
```bash
docker ps --filter name=agithome
```

### Actualizar contenido
```bash
# Editar archivos en /opt/ai-lab/stacks/websites/agithome/
# nginx recarga automáticamente al cambiar archivos (bind mount)
```

### Backup
```bash
# El contenido está en bind mount, no en volumen. Backupar la carpeta:
cp -r /opt/ai-lab/stacks/websites/agithome /opt/ai-lab/snapshots/agithome-$(date +%Y%m%d)
```

## 6. Estructura de archivos
```
agithome/
├── index.html          # Página principal
├── styles.css          # Estilos (36 KB)
├── script.js           # Lógica JS (18 KB)
├── creativewebbuilder.svg
├── images/             # Assets gráficos
├── .git/               # Repositorio git
├── backup-now.bat      # Script backup (legacy Windows)
└── README.md
```

## 7. Origen
- **Ubicación original:** `\\192.168.1.200\e\Webs\AGITHome`
- **Restaurado el:** 13/05/2026
- **Backup en NAS-N5:** conservado
