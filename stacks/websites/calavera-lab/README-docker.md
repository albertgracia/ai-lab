# CALAVERA LAB en Docker Desktop

## Opcion 1: Docker Desktop con Compose

Desde `C:\Users\leobc\AntiGravityCalaberaLab`:

1. Revisa o completa las variables en `.env.local`
2. Levanta el contenedor

```bash
docker compose up --build
```

Abrir:

```text
http://localhost:91
```

## Opcion 2: Build y run manual

```bash
docker build -t calavera-lab .
docker run --name calavera-lab-web --env-file .env.local -p 91:80 calavera-lab
```

Abrir:

```text
http://localhost:91
```

## Estructura usada

- `Dockerfile`: build multi-stage y runtime con Node
- `.env.local`: claves y configuracion sensible local
- `.env.production`: plantilla para despliegue/produccion
- `.env.example`: plantilla sin secretos
- `docker-compose.yml`: listo para Docker Desktop

## Notas

- La app se compila dentro del contenedor.
- El servidor Node expone la SPA, la API de Stripe y el endpoint del carrusel.
- `.env.local` y `.env.production` quedan ignorados por git para no subir secretos por error.
