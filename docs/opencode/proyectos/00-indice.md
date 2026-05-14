# PROYECTOS RESTAURADOS — Índice
## 13 de mayo de 2026

---

| # | Proyecto | Tipo | Dominio | Documentación |
|---|----------|------|---------|---------------|
| 1 | **AGITHome** | Web estática | `agithome.labrazahome.com` | [`01-agithome.md`](01-agithome.md) |
| 2 | **AGITServices** | Web estática | `agitservices.labrazahome.com` | [`02-agitservices.md`](02-agitservices.md) |
| 3 | **AlbertSkills** | Web estática | `albertskills.labrazahome.com` | [`03-albertskills.md`](03-albertskills.md) |
| 4 | **AlbertSkillsAMDMulti** | React + Vite (estático) | `skills.labrazahome.com` | [`04-albertskills-amd-multi.md`](04-albertskills-amd-multi.md) |
| 5 | **Calavera LAB** | Node + Express + Stripe | `calavera.labrazahome.com` | [`05-calavera-lab.md`](05-calavera-lab.md) |
| 6 | **Musquera RAW LAB** | Node + Express + PostgreSQL | `musquera.labrazahome.com` | [`06-musquera-raw.md`](06-musquera-raw.md) |

### Infraestructura común
- **Proxy:** Traefik (red `proxy`)
- **Acceso:** Cloudflare Tunnel → `192.168.1.30:80`
- **Orquestación:** Docker Compose
- **Almacenamiento:** `/opt/ai-lab/stacks/websites/`

### Stacks
| Stack | Archivo |
|-------|---------|
| Webs estáticas | `/opt/ai-lab/stacks/websites/docker-compose.yml` |
| Backends (Calavera + Musquera) | `/opt/ai-lab/stacks/websites/docker-compose.backend.yml` |

### Documentación relacionada
- [`10-proyectos-restaurados.md`](../10-proyectos-restaurados.md) — Visión general, puertos, Cloudflare
- `CHANGELOG.md` — Registro de operaciones
