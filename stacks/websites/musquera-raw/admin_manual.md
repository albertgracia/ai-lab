# 📔 Manual de Operador: RAW_FACTORY_OS v2.0 (Industrial)

Este manual documenta el funcionamiento del ecosistema **MUSQUERA RAW FACTORY™** renovado, centrado en la trazabilidad forense, gestión B2B y logística avanzada.

---

## 📡 1. Operations Center (Kanban Industrial)
El centro neurálgico de producción. Permite gestionar el flujo de trabajo desde la recepción hasta el envío.

### 🔄 Gestión de Estados
- **RECIBIDO**: Pedido pendiente de revisión técnica.
- **EN PLANCHA**: Producción activa (notifica al cliente con animación de "Plancha").
- **CONTROL CALIDAD**: Verificación final de acabados.
- **ENVIADO / SHIPPED**: Salida de fábrica. 
  > [!IMPORTANT]
  > Para marcar un pedido como **ENVIADO**, es obligatorio introducir el **Transportista** y el **Nº de Seguimiento**. El sistema bloqueará el cambio si faltan estos datos.

---

## 📦 2. Control de Inventario
Gestión en tiempo real de stock de prendas base (Camisetas, Hoodies, etc.).
- **Alertas de Stock Bajo**: Los ítems que bajen del umbral crítico aparecerán resaltados en rojo.
- **Actualización**: Permite ajustar niveles de stock tras cada tirada de producción.

---

## 👥 3. Gestión de Clientes (CRM B2B)
Base de datos para fidelización y métricas de negocio.
- **Status VIP**: Clasificación de clientes según volumen de facturación.
- **Lifetime Value (LTV)**: Visualización del total facturado por cliente.
- **Asignación**: Control de operarios asignados a cada cuenta.

---

## 📑 4. Gestión de Briefings (El Lab)
Ubicado en `[BRIEFINGS_LAB]`, esta sección segrega los diseños técnicos enviados desde el configurador.
- **Trazabilidad**: ID con prefijo `LAB-`.
- **Ficha Técnica**: Permite ver los detalles exactos de prenda, técnica y arte antes de pasar a producción.

---

## 🚚 5. Logística de Eventos (B2B)
Ubicado en `[LOGÍSTICA_EVENTOS]`, gestiona los briefings de grandes cuentas.
- **Trazabilidad**: ID con prefijo `B2B-`.
- **Control Logístico**: Panel dedicado para introducir direcciones de envío masivo y agencias de transporte.

---

## 📑 6. Motor de Presupuestos (Quoting Engine)
Generación instantánea de documentos comerciales vinculantes.
- **Botón "Generar Presupuesto B2B"**: Disponible en la Ficha Técnica de cada pedido.
- **Branding**: Los PDFs incluyen automáticamente el logo industrial y las cláusulas comerciales actualizadas.

---

## 🛠️ 5. Mantenimiento y Backups
- **Backups DB**: Ejecutar `/scripts/backup_db.ps1` periódicamente. Los backups se guardan con timestamp.
- **Monitorización**: Acceso vía Docker logs: `docker compose logs -f raw-app`.

---
**MUSQUERA RAW FACTORY™ — OPERACIÓN INDUSTRIAL GARANTIZADA**
