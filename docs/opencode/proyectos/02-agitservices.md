# AGITServices — Documentación del proyecto
## Servicios IT corporativos

---

## 1. Descripción
Web corporativa de AG IT Services, proveedora de soporte técnico, infraestructura de redes, ciberseguridad y consultoría IT para empresas.

## 2. Stack tecnológico
| Componente | Tecnología |
|------------|-----------|
| Frontend | HTML5 + CSS3 + JavaScript vanilla |
| Fuentes | Google Fonts (Plus Jakarta Sans, Inter, JetBrains Mono) |
| Servidor | nginx:alpine |
| Proxy | Traefik (AI-LAB) |

## 3. Arquitectura
```
Usuario → Cloudflare Tunnel → 192.168.1.30:80 → Traefik
                                                    ↓
                                        Host: agitservices.labrazahome.com
                                                    ↓
                                              nginx:alpine
                                                    ↓
                                        /opt/ai-lab/stacks/websites/agitservices/
```

## 4. Despliegue
- **Ruta código:** `/opt/ai-lab/stacks/websites/agitservices/`
- **Contenedor:** `agitservices`
- **Imagen:** nginx:alpine
- **Puerto interno:** 80
- **Red:** `proxy`
- **Stack:** `stacks/websites/docker-compose.yml`
- **Dominio:** `agitservices.labrazahome.com`

## 5. Operación
```bash
# Iniciar
docker compose -f /opt/ai-lab/stacks/websites/docker-compose.yml up -d agitservices

# Logs
docker logs agitservices --tail 50

# Backup
cp -r /opt/ai-lab/stacks/websites/agitservices /opt/ai-lab/snapshots/agitservices-$(date +%Y%m%d)
```

## 6. Archivos
```
agitservices/
├── index.html      # Página principal (39 KB)
├── styles.css      # Estilos (33 KB)
├── script.js       # Lógica JS (13 KB)
├── images/         # Assets
├── public/         # Archivos públicos
└── .git/           # Repositorio
```

## 7. Origen
- **Ubicación original:** `\\192.168.1.200\e\Webs\AGITServices`
- **Restaurado el:** 13/05/2026
- **Tamaño:** ~9 MB
