# Guía de Diseño UI/UX: RAW LAB (Industrial Mode)

La interfaz de **MUSQUERA RAW FACTORY™** ha evolucionado hacia un lenguaje visual puramente industrial, de alto contraste y estética premium.

---

## 🎨 1. Paleta de Colores (Industrial Hierarchy)

### Admin Panel (Operations Center)
- **Fondo Primario**: `#0a0a0a` (Capa de oscuridad técnica).
- **Acento Primario**: `#e85d04` (Naranja Industrial / Admin Accent).
- **Acciones Críticas**: `#dc2626` (Rojo Alarma).
- **Éxito / Sincro**: `#a3e635` (Verde Neón Lab).

### Frontend (El Lab)
- **Neutral 1**: `#ffffff` (Texto principal).
- **Neutral 2**: `#737373` (Metadatos).
- **Glow Accent**: `#a3e635` (Brillo neon para configuradores).

---

## 📐 2. Tipografía y Estructura
- **Fuente Principal**: Inter (Sans-serif moderna para legibilidad).
- **Fuente Técnica**: Familia Mono (JetBrains Mono / Courier) para IDs de seguimiento, logs y terminales.
- **Micro-interacciones**: Se han implementado transiciones de opacidad y escala para el filtrado del portafolio y los pasos del configurador.

---

## 💎 3. Componentes RAW
- **Glassmorphism**: Los modales de la Ficha Técnica utilizan desenfoque de fondo (`backdrop-filter: blur(12px)`).
- **Industrial Borders**: Bordes finos de 1px en `rgba(255,255,255,0.05)` para delimitar secciones sin saturar el diseño.

---
**MUSQUERA RAW FACTORY™ — DISEÑO MECÁNICO DE ALTA PRECISIÓN**
