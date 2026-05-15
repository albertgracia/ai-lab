# CalaveraLAB

Frontend editorial y e-commerce dark para CalaveraLAB, servido con Vite + React en cliente y Express en runtime para checkout de Stripe y assets dinamicos del carrusel de artifacts.

## Puesta en marcha

Desde `C:\Users\leobc\AntiGravityCalaberaLab`:

```bash
npm install
npm run dev
```

Vista local por defecto de Vite:

```text
http://localhost:5173
```

## Despliegue rapido con Docker

La forma recomendada de levantar la misma app que consume el portal:

```bash
docker compose up -d --build
```

La web queda expuesta en:

```text
http://localhost:91
```

En produccion local de la casa, Nginx Proxy Manager reenvia `https://calaveralab.labrazahome.es` al contenedor `calavera-lab-web` en el puerto `91`.

## Variables sensibles

- Usa `.env.local` para claves reales de Stripe y configuracion local.
- Usa `.env.example` como plantilla sin secretos.
- `.env`, `.env.local` y `.env.production` estan ignorados por git.

Variables esperadas por servidor:

- `STRIPE_SECRET_KEY`
- `STRIPE_PUBLISHABLE_KEY`
- `STRIPE_ALLOWED_COUNTRIES`
- `PUBLIC_BASE_URL`
- `PORT`

## Estructura util

- `src/`: app React, secciones visuales y estilos.
- `public/artifacts-carousel/`: imagenes del carrusel inferior de `The Artifacts`.
- `public/ambient-track.mp3`: pista de ambiente reproducida en la web.
- `server.js`: runtime Express, config publica y checkout.
- `server/`: catalogos de producto usados por Stripe.
- `docker-compose.yml`: contenedor `calavera-lab-web` publicado en `91:80`.

## Mantenimiento rapido

- Tras cambios visuales o de contenido: `npm run build`.
- Para dejarlo publicado en la instancia usada por el portal: `docker compose up -d --build`.
- Si cambias imagenes del carrusel, reemplazalas en `public/artifacts-carousel/` y reconstruye.
- Si cambias la musica ambiente, reemplaza `public/ambient-track.mp3` y reconstruye.

## Notas actuales del proyecto

- `The Artifacts` tiene rail vertical con scroll interno independiente en desktop.
- La musica ambiente intenta autoplay y, si el navegador la bloquea, entra en el primer gesto del usuario.
- La tipografia principal usa acabado marfil tallado sin fondo para no interferir con el arte de la pagina.
