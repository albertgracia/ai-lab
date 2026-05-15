# AG IT Home Services — Landing Page

Landing page premium dark mode para **AG IT Home Services**.

## 📁 Estructura de archivos

```
/
├── index.html        # Estructura HTML completa
├── styles.css        # Sistema de diseño, animaciones, flip cards
├── script.js         # Interacciones, canvas de red, partículas
├── README.md         # Este archivo
└── images/           # Carpeta de imágenes (añadir tus fotos aquí)
    ├── logo.png           # Logo principal (recomendado: 512x512 PNG)
    ├── hero_visual.png    # Visual del hero (recomendado: 1200x1200)
    ├── service_1.png      # Reparación de PCs
    ├── service_2.png      # Instalación de Software
    ├── service_3.png      # WiFi Profesional Unifi
    ├── service_4.png      # Mejora de Cobertura WiFi
    ├── service_5.png      # Migración 2.5Gb/10Gb
    └── service_6.png      # Securización & Unifi Protect
```

## 🎨 Sistema de Diseño

| Variable         | Valor            |
|-----------------|------------------|
| Color principal | `#3B82F6` (Azul Eléctrico) |
| Fondo primario  | `#000000`        |
| Fuente display  | Plus Jakarta Sans |
| Fuente cuerpo   | Inter             |
| Fuente mono     | JetBrains Mono    |

## 🖼️ Cómo añadir imágenes

1. Coloca tus imágenes en la carpeta `images/`
2. Usa los nombres exactos de la tabla de arriba
3. Las flip cards de servicios usarán las imágenes automáticamente

Para cada servicio, modifica el HTML buscando la sección correspondiente y añade dentro del `service-visual`:

```html
<img src="images/service_1.png" alt="Reparación de PCs" class="service-image">
```

## 📱 Responsive

- ✅ Desktop XL (>1440px)
- ✅ Desktop (1024–1440px)
- ✅ Tablet (768–1023px)
- ✅ Mobile (<768px) — Cards flip al hacer tap

## ✏️ Personalización rápida

- **Teléfono/WhatsApp:** Busca `+34XXXXXXXXX` y reemplaza con tu número real
- **Email:** Busca `info@labrazahome.es` y actualiza con tu email real
- **Testimonios:** Sección `#testimonios` en `index.html`
- **Estadísticas:** Atributos `data-target` en los contadores del hero
- **Redes sociales:** Sección `.footer-social` en el footer

## 🚀 Visualizar localmente

Abre `index.html` directamente en tu navegador,  
o usa un servidor local (recomendado):

```bash
npx serve .
# o
python -m http.server 8080
```

---
© 2026 AG IT Home Services
