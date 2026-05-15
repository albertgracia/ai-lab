# AG IT Services — Landing Page Premium Dark Mode

**"Tu tecnología operativa sin interrupciones"**

## 📁 Estructura del Proyecto

```
AntiGravityWeb/
├── index.html          # Estructura HTML completa
├── styles.css          # Sistema de diseño Dark Luxury
├── script.js           # Animaciones e interacciones
├── README.md           # Este archivo
└── images/
    ├── logo.png        # Logo generado con IA
    ├── hero_visual.png # Visual principal del hero
    ├── service_1.png   # Soporte Técnico / Helpdesk
    ├── service_3.png   # Ciberseguridad
    └── service_4.png   # Consultoría IT
```

## 🎨 Paleta de Colores

| Token | Valor | Uso |
|-------|-------|-----|
| `--primary-500` | `#3B82F6` | Color principal |
| `--primary-400` | `#60A5FA` | Hover, acentos |
| `--primary-600` | `#2563EB` | Botones activos |
| `--bg-primary` | `#000000` | Fondo principal |
| `--bg-secondary` | `#09090B` | Secciones alternas |
| `--bg-tertiary` | `#18181B` | Cards, paneles |

## 🚀 Funcionalidades

- ✅ Navbar sticky con blur glassmorphism al hacer scroll
- ✅ Sistema de partículas flotantes (50 desktop / 20 mobile)
- ✅ Flip Cards 3D interactivas (hover desktop / tap mobile)
- ✅ Contadores animados con easing cubic
- ✅ Scroll reveal con stagger por sección
- ✅ Botones con gradient shift y pulse glow
- ✅ Carrousel de logos de clientes
- ✅ Mobile menu hamburguesa
- ✅ Smooth scroll a secciones
- ✅ Parallax suave en el hero
- ✅ Efecto ripple en botones CTA
- ✅ 100% Responsive (Mobile → Desktop XL)

## 🖼️ Imágenes Generadas

| Archivo | Servicio | Estado |
|---------|----------|--------|
| `logo.png` | Logo AG IT Services | ✅ Generada |
| `hero_visual.png` | Visual principal hero | ✅ Generada |
| `service_1.png` | Soporte Técnico / Helpdesk | ✅ Generada |
| `service_2.png` | Infraestructura y Redes | 🎨 SVG animado |
| `service_3.png` | Ciberseguridad | ✅ Generada |
| `service_4.png` | Consultoría IT | ✅ Generada |
| `service_5.png` | Cloud Computing | 🎨 SVG animado |
| `service_6.png` | Monitoreo 24/7 | 🎨 SVG animado |

> **Nota:** Los servicios sin imagen usan SVGs animados inline con la misma estética Dark Luxury en azul eléctrico.

## ⚙️ Personalización

### Cambiar color principal
En `styles.css`, modificar las variables en `:root`:
```css
--primary-500: #3B82F6; /* Tu nuevo color */
--primary-rgb: 59, 130, 246; /* RGB del nuevo color */
```

### Cambiar textos
- **Nombre y tagline:** Buscar `AG IT Services` en `index.html`
- **Servicios:** Sección `.services-grid` en `index.html`
- **Contacto:** Cambiar `info@labrazahome.es` y el teléfono

### Cambiar imágenes
Reemplazar los archivos en `/images/` manteniendo los mismos nombres.

## 🌐 Cómo Publicar

1. Subir toda la carpeta a tu servidor o hosting
2. Asegurarte de que `index.html` esté en la raíz
3. Opcional: configurar dominio personalizado

**Hostings recomendados:** Netlify, Vercel, GitHub Pages (gratuitos)

---
© 2026 AG IT Services. Desarrollado con AG IT Services Premium Landing Page Template.
