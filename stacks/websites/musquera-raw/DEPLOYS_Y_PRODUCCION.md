# Guía de Despliegue y Migración a Producción (MUSQUERA RAW FACTORY™)

Esta guía detalla el procedimiento técnico para mover el entorno actual de pruebas en Homelab (`musquera-lab.labrazahome.es`) hacia un servidor en la nube definitivo, como AWS EC2, DigitalOcean o un VPS privado, asegurando que la pasarela administrativa y pública operen bajo estándares de producción seguros.

---

## FASE 1: Preparación del Entorno Definitivo (VPS)

### 1. Requisitos Previos del Nuevo Servidor
*   Instalación limpia de **Ubuntu 22.04 LTS** (o similar).
*   Se requiere tener instalado el combo de virtualización: `docker` y `docker-compose`.
*   Apertura de puertos en el Firewall del proveedor de nube (Reglas de Entrada VPC):
    *   Puerto 80: Tráfico Web HTTP.
    *   Puerto 443: Tráfico Seguro SSL HTTPS.
    *   Puerto 22: Acceso SSH Administrativo.

### 2. Migración Segura del Código ("Clone")
Evitar mover la base de datos de pruebas si no es necesario.
Clona el proyecto o muévelo vía SCP/SFTP al nuevo servidor, copiando toda la raíz desde:
`d:\DockerContainers\Webs\Musquera RAW LAB`

---

## FASE 2: Transición a Seguridad de Producción (.ENV)

Es **CRÍTICO** eliminar las credenciales base que se encuentran actualmente codificadas en crudo dentro los archivos.

### 1. Modificar Docker Compose
Abrir [docker-compose.yml](file:///d:/DockerContainers/Webs/docker-compose.yml) y cambiar la inyección de entorno del servicio Postgres y la App de Node para que dejen de usar `CHANGE_ME` y pasen a utilizar un archivo [.env](file:///d:/DockerContainers/PortalWeb/.env):
```yaml
services:
  db_postgres:
    image: postgres:15-alpine
    env_file:
      - .env # <-- Llamada segura al archivo de variables
```

### 2. Crear archivo oculto [.env](file:///d:/DockerContainers/PortalWeb/.env) en la raíz
Contendrá todos los "secretos" del proyecto que nunca deben subirse al repositorio Git.
```env
# Configuración Postgres
POSTGRES_USER=admin_raw_prod
POSTGRES_PASSWORD=GenerarUnaContrasenaMuyAvanzada123!
POSTGRES_DB=raw_factory_db

# Configuración API Node.js/JWT
NODE_ENV=production
JWT_SECRET=SemillaDeCifradoAvanzadaDeJWT!5432
```

---

## FASE 3: Servidor Inverso NGINX y SSL (HTTPS)

La app actualmente expone los puertos sin protección directa de tráfico frontal más allá que el túnel de Cloudflare local. Es obligatorio configurar NGINX o Traefik.

### Opción Nginx en Docker
1. Añade un tercer contenedor en [docker-compose.yml](file:///d:/DockerContainers/Webs/docker-compose.yml) usando la imagen `nginx:alpine`.
2. Configura un archivo `nginx.conf` para hacer un "**Reverse Proxy**" hacia nuestro frontend y API. Nginx interceptará el tráfico de internet y lo dirigirá a la app en el puerto 3000.
3. El bloque HTTP del nginx.conf:
```nginx
server {
    listen 80;
    server_name www.musqueraraw.com musqueraraw.com;
    
    location / {
        proxy_pass http://raw_factory_app:3000;
        proxy_set_header Host $host;
    }
}
```

### Certificados SSL con Let's Encrypt (Certbot)
*   Se recomienda combinar el contenedor de Nginx con el módulo de **Certbot** vía Certbot-Docker para generar y auto-renovar licencias criptográficas de certificado SSL, posibilitando el famoso *"candado verde HTTPS"* de forma gratuita. Tarea a programar vía CronJob mensual.

---

## FASE 4: Ejecución Final

Una vez configurado [.env](file:///d:/DockerContainers/PortalWeb/.env) y el candado NGINX, levanta el proyecto sin el flag `--build` a menos que hagas cambios en el código (ya que el contenedor Node ha absorbido los cambios).

```bash
docker-compose up -d
```
Comprobar `docker logs raw_factory_app -f` para verificar que la carga en *Production Mode* está emitiendo tráfico saludable en su primer arranque en la nube.
