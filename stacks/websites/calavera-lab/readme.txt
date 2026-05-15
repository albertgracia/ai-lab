CALAVERA LAB - README DEL PROYECTO

1. RESUMEN

Este proyecto es una SPA premium de CALAVERA LAB construida con React, Vite, Tailwind CSS y Framer Motion.
Incluye:

- Landing principal con direccion de arte dark luxury / cyber-occult
- Seccion The Artifacts con checkout y carruseles visuales
- Pagina secundaria de coleccion en /coleccion
- Checkout con Stripe desde backend
- Panel local de configuracion para links de Stripe y GA4
- SEO, Open Graph, Twitter Cards, JSON-LD, favicon y manifest
- Docker listo para ejecutar en local


2. URLS PRINCIPALES

- Web local en Docker: http://localhost:91
- Coleccion secundaria: http://localhost:91/coleccion
- Pagina de gracias: http://localhost:91/gracias


3. ESTRUCTURA IMPORTANTE

- src/App.jsx
  Orquestacion principal de la app, rutas simples y layout general.

- src/components/
  Componentes visuales principales.

- src/components/ApparelCatalogPage.jsx
  Pagina secundaria de Camisetas y Sudaderas.

- src/components/ProductVault.jsx
  Seccion The Artifacts.

- src/components/CheckoutModal.jsx
  Formulario previo al checkout de Stripe.

- src/components/AdminConfigPanel.jsx
  Panel local para configurar links de Stripe y GA4 sin tocar codigo.

- src/data/content.js
  Contenido principal de la landing.

- src/data/apparelCatalog.js
  Mapeo de disenos de la coleccion textil.

- server.js
  Servidor Express que sirve la SPA, el endpoint de configuracion, el checkout y el endpoint del carrusel.

- server/product-catalog.js
  Catalogo principal de productos para Stripe.

- server/apparel-catalog.js
  Catalogo de camisetas y sudaderas para Stripe.

- public/artifacts-carousel/
  Carpeta viva para el carrusel de The Artifacts. Se puede actualizar sin recompilar.

- .env.local
  Variables locales sensibles.


4. REQUISITOS

- Node.js
- npm
- Docker Desktop


5. EJECUCION EN LOCAL SIN DOCKER

Instalar dependencias:

  npm install

Modo desarrollo:

  npm run dev

Build de produccion:

  npm run build


6. EJECUCION EN DOCKER

Levantar el proyecto:

  docker compose up -d --build

Parar el proyecto:

  docker compose down


7. VARIABLES DE ENTORNO

Archivo principal en local:

  .env.local

Variables usadas:

- PORT
- STRIPE_SECRET_KEY
- STRIPE_PUBLISHABLE_KEY
- STRIPE_ALLOWED_COUNTRIES

Plantillas disponibles:

- .env.example
- .env.production

IMPORTANTE:

- .env.local y .env.production estan ignorados por git
- antes de publicar en real conviene rotar las claves de Stripe y usar secretos del hosting


8. CHECKOUT Y STRIPE

El flujo de compra funciona asi:

1. El usuario pulsa Checkout
2. Se abre un formulario previo
3. Se piden estos datos:
   - Nombre
   - Apellidos
   - Talla
   - Direccion completa de envio
   - Telefono de contacto
   - Observaciones
4. El backend crea una Checkout Session de Stripe
5. Stripe recoge direccion de envio y pago en entorno seguro

Backend implicado:

- POST /api/create-checkout-session

Configuracion sugerida en Stripe:

- success URL: https://tu-dominio.com/gracias
- cancel URL: https://tu-dominio.com/#product-vault o /coleccion


9. PANEL CONFIG LOCAL

En entorno local aparece un boton llamado:

  Config Local

Sirve para:

- pegar links de Stripe por producto
- configurar GA4 Measurement ID
- importar configuracion masiva en JSON
- exportar configuracion en JSON

Tambien funciona en red local o con:

  ?admin=1

Ejemplo de JSON para importar:

{
  "ga4MeasurementId": "G-XXXXXXXXXX",
  "stripeLinks": {
    "ritual-core-tee": "https://buy.stripe.com/...",
    "serpent-hoodie": "https://buy.stripe.com/...",
    "collector-pack": "https://buy.stripe.com/..."
  }
}


10. THE ARTIFACTS

La seccion The Artifacts incluye:

- Hover UHD en desktop
- Version optimizada para movil
- Carrusel inferior de imagenes
- Carga de imagenes desde public/artifacts-carousel

Para actualizar ese carrusel sin recompilar:

1. Añade o sustituye imagenes en:

   public/artifacts-carousel

2. Recarga la web

No hace falta rebuild si mantienes el contenedor y el volumen de Docker.


11. COLECCION CAMISETAS Y SUDADERAS

Ruta:

  /coleccion

Funciones incluidas:

- Filtros por tipo
- Busqueda por diseño
- Cards agrupadas por diseño
- Cambio entre camiseta y sudadera
- Mockups extra
- Lightbox de mookups
- Paginas detalle por diseño
- Navegacion anterior / siguiente
- Breadcrumbs

Precios configurados:

- Camisetas: 39 EUR
- Sudaderas: 69 EUR


12. COMO AÑADIR O ACTUALIZAR PRODUCTOS DE COLECCION

Carpeta fuente original:

  Camisetas y Sudaderas

Carpeta optimizada usada por frontend:

  src/assets/catalogo-camisetas-sudaderas

Mockups optimizados:

  src/assets/catalogo-mookups

Si se añaden diseños nuevos:

1. colocar archivos en la carpeta fuente
2. revisar naming
3. añadir slug/titulo en:

   src/data/apparelCatalog.js
   server/apparel-catalog.js

4. volver a optimizar assets si hace falta
5. reconstruir la app


13. ANALYTICS

Preparado:

- GA4 configurable desde Config Local
- eventos base de checkout y WhatsApp

Archivo principal:

  src/lib/analytics.js


14. SEO Y MARCA

Incluye:

- title, meta description y keywords
- Open Graph y Twitter Cards
- JSON-LD de productos y marca
- robots.txt
- sitemap.xml
- favicon y manifest


15. ARCHIVOS DE IMAGEN IMPORTANTES

- Fondo landing: hero-skeleton-party.webp
- Fondo footer: footer-sin-perder-ritmo.webp
- Carrusel The Artifacts: public/artifacts-carousel
- Catalogo textil: src/assets/catalogo-camisetas-sudaderas
- Mookups textil: src/assets/catalogo-mookups


16. RECOMENDACIONES ANTES DE PRODUCCION

- Rotar claves de Stripe si han sido compartidas
- Añadir webhook real de Stripe con firma
- Añadir rate limiting a /api/create-checkout-session
- Usar secretos del hosting en vez de archivos locales
- Revisar dominio final para success/cancel URL
- Probar pagos reales o en test segun entorno


17. COMANDOS UTILES

Instalar dependencias:

  npm install

Desarrollo:

  npm run dev

Build:

  npm run build

Docker levantar:

  docker compose up -d --build

Docker parar:

  docker compose down


18. ESTADO ACTUAL

El proyecto queda funcionando en local y en Docker con una experiencia premium, responsive, preparada para seguir evolucionando.
