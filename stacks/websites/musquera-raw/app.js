/* ═══════════════════════════════════════════
   MUSQUERA RAW FACTORY™ — app.js
   All interactive behaviour
   ═══════════════════════════════════════════ */

'use strict';

/* ─────────────────────────────────────────────
   1. NAV — scroll effect & mobile hamburger
───────────────────────────────────────────── */
const navbar   = document.getElementById('navbar');
const hamburger = document.getElementById('hamburger');
const navLinks  = document.getElementById('nav-links');

window.addEventListener('scroll', () => {
  navbar.classList.toggle('scrolled', window.scrollY > 40);
});

hamburger.addEventListener('click', () => {
  navLinks.classList.toggle('open');
});

// Close mobile nav on link click
navLinks.querySelectorAll('a').forEach(a => {
  a.addEventListener('click', () => navLinks.classList.remove('open'));
});

/* ─────────────────────────────────────────────
   2. SCROLL ANIMATIONS — Intersection Observer
───────────────────────────────────────────── */
const animItems = document.querySelectorAll('.animate-in');
const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.classList.add('visible');
        observer.unobserve(e.target);
      }
    });
  },
  { threshold: 0.1 }
);
animItems.forEach(el => observer.observe(el));

/* ─────────────────────────────────────────────
   3. EL LAB — Multi-step configurator
───────────────────────────────────────────── */
let labState = {
  step:    1,
  garment: 'camiseta',
  artFile: null,
  tech:    'serigrafia',
};

const TECH_LABELS = {
  serigrafia: 'Serigrafía',
  dtf:        'DTF — Direct to Film',
  bordado:    'Bordado',
};
const GARMENT_LABELS = {
  camiseta:  'Camiseta',
  hoodie:    'Hoodie / Sudadera',
  polo:      'Polo',
  chaqueta:  'Chaqueta',
  gorra:     'Gorra',
  bolsa:     'Bolsa Tote',
};

function goToLabStep(step) {
  // Update panels
  document.querySelectorAll('.lab-panel').forEach(p => p.classList.remove('active'));
  document.getElementById(`lab-panel-${step}`).classList.add('active');

  // Update step indicators
  document.querySelectorAll('.lab-step').forEach((s, i) => {
    const idx = i / 2 + 1; // accounting for connectors — use data-step instead
  });
  document.querySelectorAll('[data-step]').forEach(s => {
    const n = parseInt(s.dataset.step);
    s.classList.remove('active', 'done');
    if (n === step) s.classList.add('active');
    if (n < step) s.classList.add('done');
  });

  labState.step = step;

  // If going to summary, populate it
  if (step === 4) updateLabSummary();
}

function updateLabSummary() {
  document.getElementById('sum-garment').textContent =
    GARMENT_LABELS[labState.garment] || labState.garment;
  document.getElementById('sum-art').textContent =
    labState.artFile ? labState.artFile : 'No subido (enviar después)';
  document.getElementById('sum-tech').textContent =
    TECH_LABELS[labState.tech] || labState.tech;
  
  const now = new Date();
  document.getElementById('sum-date').textContent = 
    `${now.getDate().toString().padStart(2, '0')}/${(now.getMonth() + 1).toString().padStart(2, '0')}/${now.getFullYear()}`;
}

/* ─────────────────────────────────────────────
   3b. SIGNATURE PAD & PDF ENGINE
───────────────────────────────────────────── */
const sigCanvas = document.getElementById('signature-pad');
const ctx = sigCanvas?.getContext('2d');
let drawing = false;
let isSigned = false;

if (sigCanvas) {
  ctx.lineWidth = 2;
  ctx.lineCap = 'round';
  ctx.strokeStyle = '#000';

  const getPos = (e) => {
    const rect = sigCanvas.getBoundingClientRect();
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    return { x: clientX - rect.left, y: clientY - rect.top };
  };

  const startDraw = (e) => {
    drawing = true;
    const pos = getPos(e);
    ctx.beginPath();
    ctx.moveTo(pos.x, pos.y);
    e.preventDefault();
  };

  const draw = (e) => {
    if (!drawing) return;
    const pos = getPos(e);
    ctx.lineTo(pos.x, pos.y);
    ctx.stroke();
    isSigned = true;
    document.getElementById('btn-generate-pdf').disabled = false;
    e.preventDefault();
  };

  const endDraw = () => { drawing = false; };

  sigCanvas.addEventListener('mousedown', startDraw);
  sigCanvas.addEventListener('mousemove', draw);
  window.addEventListener('mouseup', endDraw);
  
  sigCanvas.addEventListener('touchstart', startDraw);
  sigCanvas.addEventListener('touchmove', draw);
  sigCanvas.addEventListener('touchend', endDraw);
}

document.getElementById('btn-clear-sig')?.addEventListener('click', () => {
  ctx.clearRect(0, 0, sigCanvas.width, sigCanvas.height);
  isSigned = false;
  document.getElementById('btn-generate-pdf').disabled = true;
});

async function generateTechnicalSheet() {
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF();
  
  const garment = GARMENT_LABELS[labState.garment] || labState.garment;
  const tech = TECH_LABELS[labState.tech] || labState.tech;
  const art = labState.artFile || 'No proporcionado';
  const date = document.getElementById('sum-date').textContent;

  // Header
  doc.setFillColor(10, 10, 10);
  doc.rect(0, 0, 210, 40, 'F');
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(22);
  doc.text('MUSQUERA RAW FACTORY', 20, 25);
  doc.setFontSize(10);
  doc.text('FICHA TÉCNICA DE PRODUCCIÓN INDUSTRIAL', 20, 32);

  // Body
  doc.setTextColor(0, 0, 0);
  doc.setFontSize(14);
  doc.text('ESPECIFICACIONES DEL PEDIDO', 20, 60);
  
  doc.setFontSize(11);
  doc.text(`FECHA DE VALIDACIÓN: ${date}`, 20, 75);
  doc.text(`TIPO DE PRENDA: ${garment.toUpperCase()}`, 20, 85);
  doc.text(`TÉCNICA DE ESTAMPADO: ${tech.toUpperCase()}`, 20, 95);
  doc.text(`ORIGEN DEL ARTE: ${art}`, 20, 105);

  // Legal
  doc.setFontSize(9);
  doc.setTextColor(100, 100, 100);
  const legalText = "Al firmar este documento, el cliente aprueba las especificaciones técnicas descritas. MUSQUERA RAW FACTORY queda exenta de responsabilidad legal por errores en el diseño proporcionado once validada esta ficha.";
  doc.text(doc.splitTextToSize(legalText, 170), 20, 125);

  // Signature
  doc.setTextColor(0, 0, 0);
  doc.setFontSize(11);
  doc.text('FIRMA DE CONFORMIDAD DEL CLIENTE:', 20, 160);
  
  const sigData = sigCanvas.toDataURL('image/png');
  doc.addImage(sigData, 'PNG', 20, 165, 80, 30);
  
  doc.line(20, 195, 100, 195);
  doc.setFontSize(8);
  doc.text('VALIDADO DIGITALMENTE', 20, 200);

  // Status Stamp
  doc.setDrawColor(232, 93, 4);
  doc.setLineWidth(1);
  doc.rect(140, 160, 40, 20);
  doc.setTextColor(232, 93, 4);
  doc.setFontSize(10);
  doc.text('APROBADO', 145, 172);

  doc.save(`MUSQUERA_FICHA_${date.replace(/\//g, '-')}.pdf`);
  
  // RAW_FACTORY_OS: Persist Order to DB
  try {
    const totalRaw = document.getElementById('res-total-price')?.textContent || "0 €";
    const totalNum = parseFloat(totalRaw.replace(' €', '').replace(',', '.'));
    const qtyNum = parseInt(document.getElementById('qty-slider')?.value || 1);
    const trackingId = `LAB-${Date.now().toString().slice(-6)}`;
    
    await fetch('/api/lab-order', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        cliente: 'CLIENTE_LAB_ANÓNIMO',
        tecnica: tech,
        total: totalNum,
        trackingId: trackingId,
        cantidad: qtyNum
      })
    });
    
    alert(`✓ Ficha técnica generada con éxito.\nID DE SEGUIMIENTO: ${trackingId}`);
  } catch (err) {
    console.error("Error persistiendo pedido Lab:", err);
    alert('✓ Ficha técnica generada. (Error de persistencia en DB)');
  }
}

document.getElementById('btn-generate-pdf')?.addEventListener('click', generateTechnicalSheet);

// Navigation buttons
document.getElementById('lab-next-1').addEventListener('click', () => goToLabStep(2));
document.getElementById('lab-prev-2').addEventListener('click', () => goToLabStep(1));
document.getElementById('lab-next-2').addEventListener('click', () => goToLabStep(3));
document.getElementById('lab-prev-3').addEventListener('click', () => goToLabStep(2));
document.getElementById('lab-next-3').addEventListener('click', () => goToLabStep(4));
document.getElementById('lab-prev-4').addEventListener('click', () => goToLabStep(3));

// Garment selection
document.querySelectorAll('.garment-card').forEach(card => {
  card.addEventListener('click', () => {
    document.querySelectorAll('.garment-card').forEach(c => c.classList.remove('selected'));
    card.classList.add('selected');
    labState.garment = card.dataset.garment;
    // sync with calculator
    const calcSelect = document.getElementById('calc-garment');
    if (calcSelect) calcSelect.value = labState.garment;
  });
  card.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') card.click(); });
});

// Technique selection
document.querySelectorAll('.technique-card').forEach(card => {
  card.addEventListener('click', () => {
    document.querySelectorAll('.technique-card').forEach(c => c.classList.remove('selected'));
    card.classList.add('selected');
    labState.tech = card.dataset.tech;
    // sync with calculator tab
    document.querySelectorAll('.calc-tab').forEach(t => t.classList.remove('active'));
    const syncTab = document.querySelector(`[data-ctab="${labState.tech}"]`);
    if (syncTab) {
      syncTab.classList.add('active');
      updateCalcTech(labState.tech);
    }
    updateCalc();
  });
  card.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') card.click(); });
});

// File upload
const uploadZone = document.getElementById('upload-zone');
const fileInput  = document.getElementById('file-input');
const preview    = document.getElementById('upload-preview');

uploadZone.addEventListener('click', () => fileInput.click());
uploadZone.addEventListener('dragover', e => {
  e.preventDefault();
  uploadZone.classList.add('dragging');
});
uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('dragging'));
uploadZone.addEventListener('drop', e => {
  e.preventDefault();
  uploadZone.classList.remove('dragging');
  const file = e.dataTransfer.files[0];
  if (file) handleFileUpload(file);
});
fileInput.addEventListener('change', () => {
  if (fileInput.files[0]) handleFileUpload(fileInput.files[0]);
});

function handleFileUpload(file) {
  labState.artFile = file.name;
  preview.innerHTML = `
    <div style="display:flex;align-items:center;gap:12px;background:var(--accent-soft);
                border:1px solid var(--accent);border-radius:2px;padding:10px 16px;margin-top:12px">
      <span style="font-size:1.2rem">📎</span>
      <span style="font-family:var(--font-mono);font-size:0.7rem;color:var(--text-2)">
        ${file.name} — ${(file.size / 1024).toFixed(1)} KB
      </span>
      <span style="color:var(--accent);font-family:var(--font-mono);font-size:0.6rem;margin-left:auto">✓ SUBIDO</span>
    </div>`;
}

/* ─────────────────────────────────────────────
   4. CALCULADORA DINÁMICA (Deprecated - Logic moved to EOF)
───────────────────────────────────────────── */

/* ─────────────────────────────────────────────
   5. DASHBOARD PRO — Tracking Simulation
───────────────────────────────────────────── */
const trackBtn    = document.getElementById('track-btn');
const trackInput  = document.getElementById('track-input');
const trackResult = document.getElementById('track-result');
const statusSteps = document.querySelectorAll('.status-step');

const MOCK_ORDERS = {
  'MRF-2024': 1, // Recibido
  'STAGE-X': 2,  // En Plancha
  'QUALITY-1': 3, // Calidad
  'SENT-V': 4    // Enviado
};

trackBtn?.addEventListener('click', async () => {
  const code = trackInput.value.toUpperCase().trim();
  if (!code) return;
  
  try {
    const response = await fetch(`/api/status/${code}`);
    const data = await response.json();
    
    if (data.success) {
      trackResult.classList.remove('error');
      
      // Map Internal DB statuses (Uppercase) to UI Levels (1-4)
      const levelMap = { 
        // Internal Codes (Production)
        'RECEIVED': 1, 
        'IN_PRINT': 2, 
        'QUALITY_CHECK': 3, 
        'SHIPPED': 4,
        
        // Display Aliases (Legacy/Frontend)
        'RECIBIDO': 1, 
        'EN PLANCHA': 2, 
        'CONTROL CALIDAD': 3, 
        'ENVIADO': 4
      };
      
      const level = levelMap[data.status] || 1;
      
      statusSteps.forEach((step, i) => {
        const isActive = i + 1 <= level;
        const isCurrent = i + 1 === level;
        step.classList.toggle('active', isActive);
        step.classList.toggle('current', isCurrent);
        
        // Trigger fire/smoke animation for "En Plancha" step
        if (step.id === 'step-plancha') {
          step.classList.toggle('in-production', isCurrent);
        }
      });

      // Shipment Tracking Logic
      const trackingContainer = document.getElementById('tracking-logistics'); 
      if (level === 4 && data.transport_tracking) {
        const id = data.transport_tracking;
        let url = '#';
        let agency = 'AGENCIA_DESCONOCIDA';

        if (/^[0-9]{14,20}$/.test(id)) { agency = 'CORREOS'; url = `https://www.correos.es/es/es/herramientas/localizador/envios/detalle?devolucion=false&reintento=0&numero=${id}`; }
        else if (/^[0-9]{10}$/.test(id)) { agency = 'DHL'; url = `https://www.dhl.com/es-es/home/tracking/tracking-express.html?submit=1&tracking-id=${id}`; }
        else if (/^[A-Z0-9]{12}$/.test(id)) { agency = 'SEUR'; url = `https://www.seur.com/livetracking/pages/seguimiento-online-busqueda.do?idSeguimiento=${id}`; }
        else if (/^[0-9]{12}$/.test(id)) { agency = 'FEDEX'; url = `https://www.fedex.com/fedextrack/?tracknumbers=${id}`; }

        if (trackingContainer) {
          trackingContainer.innerHTML = `
            <div class="shipment-status animate-in">
              <p style="color:var(--accent); font-weight:bold; margin-bottom:10px;">[PAQUETE_EN_CAMINO]</p>
              <p style="font-size:12px; margin-bottom:15px;">Transportista: ${agency}<br>Código: ${id}</p>
              <a href="${url}" target="_blank" class="btn-cta" style="display:inline-block; text-decoration:none; font-size:12px; padding:10px 20px;">LOCALIZAR MI PEDIDO →</a>
            </div>
          `;
          trackingContainer.style.display = 'block';
        }
      } else if (trackingContainer) {
        trackingContainer.style.display = 'none';
      }

      trackResult.style.display = 'block';
    } else {
      trackResult.classList.add('error');
      alert('Pedido no encontrado en la base de datos industrial.');
    }
  } catch (err) {
    alert('Error de conexión con el HomeServer.');
  }
});

const supportBtn = document.getElementById('btn-talk-production');
supportBtn?.addEventListener('click', () => {
  const eventId = trackInput.value.trim() || '[Nombre del Evento]';
  const phone = '34600123456'; // Placeholder WhatsApp Business Number
  const message = `Hola, soy del evento ${eventId} y necesito asistencia técnica con mi archivo vectorial.`;
  const waUrl = `https://wa.me/${phone}?text=${encodeURIComponent(message)}`;
  window.open(waUrl, '_blank');
});



/* ─────────────────────────────────────────────
   5. PORTFOLIO — Filter
───────────────────────────────────────────── */
document.querySelectorAll('.pf-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.pf-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const filter = btn.dataset.pf;

    document.querySelectorAll('.portfolio-item').forEach(item => {
      const cat = item.dataset.cat;
      if (filter === 'all' || cat === filter) {
        item.style.display = '';
        item.style.opacity = '0';
        item.style.transform = 'scale(0.95)';
        requestAnimationFrame(() => {
          item.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
          item.style.opacity = '1';
          item.style.transform = 'scale(1)';
        });
      } else {
        item.style.opacity = '0';
        item.style.transform = 'scale(0.95)';
        setTimeout(() => { item.style.display = 'none'; }, 350);
      }
    });
  });
});

/* ─────────────────────────────────────────────
   6. CONTACT FORM — Submit simulation
───────────────────────────────────────────── */
const contactForm = document.getElementById('contact-form');
const formSuccess = document.getElementById('form-success');
const formBtnText = document.getElementById('form-btn-text');

contactForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const btn = document.getElementById('form-submit');
  btn.disabled = true;
  formBtnText.textContent = 'ENVIANDO...';

  setTimeout(() => {
    formSuccess.classList.add('show');
    contactForm.reset();
    btn.disabled = false;
    formBtnText.textContent = 'ENVIAR BRIEFING →';
    setTimeout(() => formSuccess.classList.remove('show'), 5000);
  }, 1200);
});

/* ─────────────────────────────────────────────
   7. Active nav link highlight on scroll
───────────────────────────────────────────── */
const sections = document.querySelectorAll('section[id]');
const navAnchors = document.querySelectorAll('.nav-links a');

const navObserver = new IntersectionObserver(
  (entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        navAnchors.forEach(a => {
          a.style.color = '';
          a.style.borderBottomColor = '';
        });
        const active = document.querySelector(`.nav-links a[href="#${e.target.id}"]`);
        if (active) {
          active.style.color = 'var(--accent)';
          active.style.borderBottomColor = 'var(--accent)';
        }
      }
    });
  },
  { threshold: 0.3, rootMargin: '-80px 0px 0px 0px' }
);
sections.forEach(s => navObserver.observe(s));

/* ─────────────────────────────────────────────
   11. B2B GRANDES EVENTOS — API SUBMISSION
───────────────────────────────────────────── */
const eventBespokeForm = document.getElementById('event-bespoke-form');
if (eventBespokeForm) {
  eventBespokeForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = eventBespokeForm.querySelector('button');
    const originalText = btn.textContent;
    
    btn.textContent = 'PROCESANDO BRIEFING...';
    btn.disabled = true;

    // RAW_FACTORY_OS: Map to Server-Side expected keys (clientName, eventDate)
    const formData = new FormData();
    formData.append('clientName', eventBespokeForm.querySelector('input[type="text"]').value);
    formData.append('eventDate', eventBespokeForm.querySelector('input[type="date"]').value);
    formData.append('technique', eventBespokeForm.querySelector('select').value);
    formData.append('quantity', '1'); // Default for bespoke briefings
    
    const fileInput = eventBespokeForm.querySelector('input[type="file"]');
    if (fileInput && fileInput.files.length > 0) {
      formData.append('vectorFile', fileInput.files[0]);
    }

    try {
      const response = await fetch('/api/orders', {
        method: 'POST',
        body: formData
      });
      const data = await response.json();
      
      if (data.success) {
        alert(`¡ BRIEFING LOGÍSTICO RECIBIDO ! \nID de Tráfico Generado: ${data.trackingId}`);
        eventBespokeForm.reset();
      } else {
        alert('Error en el servidor: ' + data.error);
      }
    } catch (err) {
      alert('Error crítico de red. Contacte con TALK_TO_PRODUCTION.');
    } finally {
      btn.textContent = originalText;
      btn.disabled = false;
    }
  });
}

/* ─────────────────────────────────────────────
   8. CTA "Solicitar Presupuesto" — pre-fill form
───────────────────────────────────────────── */
document.getElementById('btn-request-quote')?.addEventListener('click', (e) => {
  e.preventDefault();
  const qty = parseInt(qtySlider.value);
  const garmentSelect = document.getElementById('calc-garment');
  const garmentName = garmentSelect?.options[garmentSelect.selectedIndex]?.text || '';
  const tech = TECH_LABELS[currentTech] || currentTech;
  const unitPrice = document.getElementById('res-unit-price')?.textContent || '';
  const totalPrice = document.getElementById('res-total-price')?.textContent || '';

  const msgField = document.getElementById('form-msg');
  if (msgField) {
    msgField.value =
      `Técnica: ${tech}\nPrenda: ${garmentName}\nCantidad: ${qty} unidades\nPrecio/und: ${unitPrice}\nTotal: ${totalPrice}\n\n[Detalla aquí tu diseño, fechas de entrega y cualquier requerimiento especial]`;
  }
  document.getElementById('contacto')?.scrollIntoView({ behavior: 'smooth' });
});

/* ─────────────────────────────────────────────
   9. Micro-animations — solution cards hover
───────────────────────────────────────────── */
document.querySelectorAll('.solution-card').forEach(card => {
  card.addEventListener('mouseenter', () => {
    const icon = card.querySelector('.sol-icon');
    if (icon) icon.style.transform = 'scale(1.1) rotate(-5deg)';
  });
  card.addEventListener('mouseleave', () => {
    const icon = card.querySelector('.sol-icon');
    if (icon) icon.style.transform = '';
  });
});

/* ─────────────────────────────────────────────
   10. Section reveal on load
───────────────────────────────────────────── */
window.addEventListener('load', () => {
  document.querySelectorAll('.animate-in').forEach(el => observer.observe(el));
  // Trigger hero immediately
  document.querySelectorAll('#hero .animate-in').forEach((el, i) => {
    setTimeout(() => el.classList.add('visible'), i * 120);
  });
});

console.log("%c[RAW_FACTORY_OS v1.0] Running on Musquera-Lab HomeServer | Port: 99 | Storage: RAID_CONNECTED", "color: #e85d04; font-family: monospace; font-weight: bold;");

/* ─────────────────────────────────────────────
   12. EASTER EGG — CTRL + L + A + B
───────────────────────────────────────────── */
const keysPressed = new Set();
window.addEventListener('keydown', (e) => {
  keysPressed.add(e.key.toLowerCase());
  
  const isCtrl = keysPressed.has('control');
  const hasL = keysPressed.has('l');
  const hasA = keysPressed.has('a');
  const hasB = keysPressed.has('b');

  if (isCtrl && hasL && hasA && hasB) {
    triggerEasterEgg();
  }
});

window.addEventListener('keyup', (e) => {
  keysPressed.delete(e.key.toLowerCase());
});

function triggerEasterEgg() {
  const logo = document.querySelector('.logo');
  const msg = "[ENGINEERED_BY_MUSQUERA_LAB // LABRAZAHOME_OS_v1.0]";
  
  // Create toast
  let toast = document.getElementById('easter-egg-toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'easter-egg-toast';
    toast.className = 'easter-egg-toast';
    document.body.appendChild(toast);
  }
  
  toast.textContent = msg;
  
  // Activate
  logo?.classList.add('logo-glow');
  toast.classList.add('show');
  
  // Reset
  setTimeout(() => {
    logo?.classList.remove('logo-glow');
    toast.classList.remove('show');
  }, 3000);

  // Clear keys to prevent double trigger
  keysPressed.clear();
}

/* ─────────────────────────────────────────────
   13. CALCULADORA DE PRESUPUESTOS (B2B)
───────────────────────────────────────────── */
(function initCalculator() {
  const calcTabs = document.querySelectorAll('.calc-tab');
  const selectGarment = document.getElementById('calc-garment');
  const sliderQty = document.getElementById('qty-slider');
  const displayQty = document.getElementById('qty-display');
  const sliderColors = document.getElementById('colors-slider');
  const displayColors = document.getElementById('colors-display');
  const colorGroup = document.getElementById('color-group');
  const priorityShip = document.getElementById('priority-ship');
  const posFront = document.getElementById('pos-front');
  const posBack = document.getElementById('pos-back');
  const posSleeve = document.getElementById('pos-sleeve');

  // Verify elements exist to prevent silent failures in other pages
  if (!sliderQty || !selectGarment) return;

  const PRICES = {
    garments: {
      'camiseta-evento': 2.50,
      'hoodie-staff': 14.00,
      'camiseta-premium': 4.50,
      'polo': 8.00,
      'chaqueta': 22.00,
      'gorra': 3.00,
      'bolsa': 2.00
    },
    techBase: {
      'dtf': 3.50,
      'bordado': 4.00
    }
  };

  let currentTech = 'serigrafia';

  function updateCalculator() {
    const qty = parseInt(sliderQty.value) || 1;
    let garmentPrice = PRICES.garments[selectGarment.value] || 0;
    
    if (displayQty) displayQty.textContent = qty + " unidades";
    if (displayColors && sliderColors) displayColors.textContent = sliderColors.value;
    
    let positions = 0;
    if (posFront && posFront.checked) positions++;
    if (posBack && posBack.checked) positions++;
    if (posSleeve && posSleeve.checked) positions++;
    
    let printPrice = 0;
    if (currentTech === 'serigrafia') {
      const colors = sliderColors ? parseInt(sliderColors.value) : 1;
      printPrice = (0.50 + (0.80 * colors)) * positions;
    } else {
      printPrice = (PRICES.techBase[currentTech] || 0) * positions;
    }

    let tierDiscount = 0;
    let tierLabel = "NIVEL BASE";
    
    document.querySelectorAll('.tier').forEach(t => t.style.opacity = '0.4');
    
    if (qty >= 200) {
      tierDiscount = 0.45;
      tierLabel = "BULK (-45%)";
      const t = document.getElementById('tier-4');
      if (t) t.style.opacity = '1';
    } else if (qty >= 51) {
      tierDiscount = 0.30;
      tierLabel = "NIVEL 3 (-30%)";
      const t = document.getElementById('tier-3');
      if (t) t.style.opacity = '1';
    } else if (qty >= 11) {
      tierDiscount = 0.15;
      tierLabel = "NIVEL 2 (-15%)";
      const t = document.getElementById('tier-2');
      if (t) t.style.opacity = '1';
    } else {
      tierLabel = "PREC. BASE (1-10)";
      const t = document.getElementById('tier-1');
      if (t) t.style.opacity = '1';
    }
    
    let baseUnit = garmentPrice + printPrice;
    let discountedUnit = baseUnit * (1 - tierDiscount);
    
    const isPriority = priorityShip && priorityShip.checked;
    if (isPriority) discountedUnit *= 1.25;
    
    const total = discountedUnit * qty;
    
    const tl = document.getElementById('result-tier-label');
    if(tl) tl.textContent = tierLabel;
    
    const rs = document.getElementById('result-saving');
    const rbd = document.getElementById('rb-discount');
    if (tierDiscount > 0) {
      if(rs) rs.textContent = `Ahorrando ${(tierDiscount*100).toFixed(0)}% vs. unitario`;
      if(rbd) rbd.textContent = `-${(tierDiscount*100).toFixed(0)}%`;
    } else {
      if(rs) rs.textContent = "Precios base aplicados";
      if(rbd) rbd.textContent = "0%";
    }

    const rup = document.getElementById('res-unit-price');
    if(rup) rup.textContent = discountedUnit.toLocaleString('es-ES', {minimumFractionDigits:2, maximumFractionDigits:2}) + " €";
    
    const rtp = document.getElementById('res-total-price');
    if(rtp) rtp.textContent = total.toLocaleString('es-ES', {minimumFractionDigits:2, maximumFractionDigits:2}) + " €";
    
    const rbg = document.getElementById('rb-garment');
    if(rbg) rbg.textContent = garmentPrice.toLocaleString('es-ES', {minimumFractionDigits:2, maximumFractionDigits:2}) + " €";
    
    const rbp = document.getElementById('rb-print');
    if(rbp) rbp.textContent = printPrice.toLocaleString('es-ES', {minimumFractionDigits:2, maximumFractionDigits:2}) + " €";

    renderChart(qty, baseUnit, discountedUnit);
  }

  function renderChart(qty, baseUnit, discountedUnit) {
    const chart = document.getElementById('chart-bars');
    if (!chart) return;
    chart.innerHTML = '';
    const maxPrice = baseUnit * 1.5; 
    
    const points = [
      { q: "1 un.", p: baseUnit },
      { q: "50 un.", p: baseUnit * 0.85 },
      { q: "200 un.", p: baseUnit * 0.70 },
      { q: "Tú", p: discountedUnit }
    ];
    
    points.forEach((pt, idx) => {
      let ht = maxPrice > 0 ? (pt.p / maxPrice) * 100 : 0;
      if (ht > 100) ht = 100;
      let isYou = idx === 3;
      let html = `
        <div style="display:flex; flex-direction:column; align-items:center; gap:4px; height:100%; justify-content:flex-end;">
          <div style="font-size:0.6rem; color:var(--text-3);">${pt.p.toLocaleString('es-ES', {minimumFractionDigits:1, maximumFractionDigits:1})}€</div>
          <div style="width:24px; height:${Math.max(4, ht)}px; background:${isYou ? 'var(--accent)' : 'var(--border)'}; border-radius:2px; transition:all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);"></div>
          <div style="font-size:0.55rem; color:${isYou ? 'var(--accent)' : 'var(--text-3)'}; font-family:var(--font-mono);">${pt.q}</div>
        </div>
      `;
      chart.insertAdjacentHTML('beforeend', html);
    });
    chart.style.display = 'flex';
    chart.style.alignItems = 'flex-end';
    chart.style.justifyContent = 'space-between';
    chart.style.height = '120px';
    chart.style.paddingTop = '16px';
    chart.style.borderBottom = '1px solid var(--border)';
  }

  if(calcTabs) {
    calcTabs.forEach(tab => {
      tab.addEventListener('click', (e) => {
        calcTabs.forEach(t => t.classList.remove('active'));
        e.target.classList.add('active');
        currentTech = e.target.dataset.ctab || e.target.id.replace('ctab-', '');
        if (currentTech === 's') currentTech = 'serigrafia';
        if (currentTech === 'd') currentTech = 'dtf';
        if (currentTech === 'b') currentTech = 'bordado';
        
        if (colorGroup) {
          colorGroup.style.display = currentTech === 'serigrafia' ? 'flex' : 'none';
        }
        updateCalculator();
      });
    });
  }

  // Bind direct DOM listeners instead of array iterators to bypass scoping issues
  if (sliderQty) {
    sliderQty.oninput = updateCalculator;
    sliderQty.onchange = updateCalculator;
  }
  if (selectGarment) selectGarment.onchange = updateCalculator;
  if (sliderColors) sliderColors.oninput = updateCalculator;
  if (priorityShip) priorityShip.onchange = updateCalculator;
  if (posFront) posFront.onchange = updateCalculator;
  if (posBack) posBack.onchange = updateCalculator;
  if (posSleeve) posSleeve.onchange = updateCalculator;

  // Initial render
  setTimeout(updateCalculator, 100);
})();



