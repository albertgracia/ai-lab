/* ================================================
   AG IT Home Services - Main JavaScript
   Animations, Flip Cards, Particles, Canvas Network
   ================================================ */

'use strict';

// ============================================================
// UTILITY: Debounce
// ============================================================
function debounce(fn, wait = 100) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
}

// ============================================================
// ANIMATED COUNTER
// ============================================================
function animateCounter(el, target, duration = 1800) {
  let start = null;
  const step = (timestamp) => {
    if (!start) start = timestamp;
    const progress = Math.min((timestamp - start) / duration, 1);
    // Ease-out
    const eased = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.round(eased * target);
    if (progress < 1) requestAnimationFrame(step);
    else el.textContent = target;
  };
  requestAnimationFrame(step);
}

// ============================================================
// PARTICLE SYSTEM
// ============================================================
function initParticles() {
  const container = document.getElementById('particles-container');
  if (!container) return;

  const count = window.innerWidth < 768 ? 20 : 50;

  for (let i = 0; i < count; i++) {
    const p = document.createElement('div');
    p.className = 'particle' + (Math.random() > 0.7 ? ' large' : '');
    p.style.left = Math.random() * 100 + '%';
    p.style.top = Math.random() * 100 + '%';
    p.style.animationDelay = (Math.random() * 20) + 's';
    p.style.animationDuration = (15 + Math.random() * 15) + 's';
    container.appendChild(p);
  }
}

// ============================================================
// NETWORK CANVAS (Hero Visual)
// ============================================================
function initNetworkCanvas() {
  const canvas = document.getElementById('network-canvas');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  const W = canvas.width;
  const H = canvas.height;
  const cx = W / 2;
  const cy = H / 2;

  // Primary color rgb
  const PR = 59, PG = 130, PB = 246;

  const nodeCount = 18;
  const nodes = [];

  // Create nodes distributed in a sphere-like pattern
  for (let i = 0; i < nodeCount; i++) {
    const angle = (i / nodeCount) * Math.PI * 2;
    const radius = 80 + Math.random() * 140;
    nodes.push({
      x: cx + Math.cos(angle) * radius * (0.8 + Math.random() * 0.4),
      y: cy + Math.sin(angle) * radius * 0.6 * (0.8 + Math.random() * 0.4),
      vx: (Math.random() - 0.5) * 0.4,
      vy: (Math.random() - 0.5) * 0.4,
      size: 2 + Math.random() * 3,
      opacity: 0.4 + Math.random() * 0.6,
      pulseOffset: Math.random() * Math.PI * 2,
    });
  }

  // Add center node
  nodes.push({ x: cx, y: cy, vx: 0, vy: 0, size: 6, opacity: 1, pulseOffset: 0, isCenter: true });

  const maxDist = 200;
  let animFrame;

  function draw(timestamp) {
    ctx.clearRect(0, 0, W, H);

    const t = timestamp * 0.001;

    // Circular mask for orb effect
    ctx.save();
    ctx.beginPath();
    ctx.arc(cx, cy, 230, 0, Math.PI * 2);
    ctx.clip();

    // Background glow
    const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, 230);
    grad.addColorStop(0, `rgba(${PR},${PG},${PB},0.06)`);
    grad.addColorStop(1, 'transparent');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, W, H);

    // Move nodes
    nodes.forEach(n => {
      if (n.isCenter) return;
      n.x += n.vx;
      n.y += n.vy;

      // Gentle bounce from center with attraction
      const dx = cx - n.x;
      const dy = cy - n.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist > 190) {
        n.vx += dx * 0.0002;
        n.vy += dy * 0.0002;
      }

      // Dampen
      n.vx *= 0.99;
      n.vy *= 0.99;
    });

    // Draw connections
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i], b = nodes[j];
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < maxDist) {
          const alpha = (1 - dist / maxDist) * 0.35;
          ctx.beginPath();
          ctx.strokeStyle = `rgba(${PR},${PG},${PB},${alpha})`;
          ctx.lineWidth = 1;
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();

          // Data packet traveling along some connections
          if (dist < 120 && Math.random() < 0.003) {
            const prog = (t * 0.5) % 1;
            const px = a.x + (b.x - a.x) * prog;
            const py = a.y + (b.y - a.y) * prog;
            ctx.beginPath();
            ctx.arc(px, py, 2, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(${PR},${PG},${PB},0.9)`;
            ctx.fill();
          }
        }
      }
    }

    // Draw nodes
    nodes.forEach((n, i) => {
      const pulse = Math.sin(t * 2 + n.pulseOffset) * 0.3 + 0.7;
      const size = n.size * pulse;

      if (n.isCenter) {
        // Center pulsing orb
        const cg = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, 30);
        cg.addColorStop(0, `rgba(${PR},${PG},${PB},0.6)`);
        cg.addColorStop(1, 'transparent');
        ctx.beginPath();
        ctx.arc(n.x, n.y, 30, 0, Math.PI * 2);
        ctx.fillStyle = cg;
        ctx.fill();
      }

      ctx.beginPath();
      ctx.arc(n.x, n.y, size, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${PR},${PG},${PB},${n.opacity * pulse})`;
      ctx.fill();

      // Outer ring on some nodes
      if (n.size > 3) {
        ctx.beginPath();
        ctx.arc(n.x, n.y, size + 4, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(${PR},${PG},${PB},${0.2 * pulse})`;
        ctx.lineWidth = 1;
        ctx.stroke();
      }
    });

    ctx.restore();
    animFrame = requestAnimationFrame(draw);
  }

  animFrame = requestAnimationFrame(draw);

  // Cleanup when out of view
  const obs = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (!e.isIntersecting) {
        cancelAnimationFrame(animFrame);
      } else {
        animFrame = requestAnimationFrame(draw);
      }
    });
  });
  obs.observe(canvas);
}

// ============================================================
// NAVBAR: Sticky with scroll
// ============================================================
function initNavbar() {
  const navbar = document.getElementById('navbar');
  if (!navbar) return;

  const onScroll = debounce(() => {
    navbar.classList.toggle('scrolled', window.scrollY > 60);
  }, 10);

  window.addEventListener('scroll', onScroll, { passive: true });
}

// ============================================================
// MOBILE MENU
// ============================================================
function initMobileMenu() {
  const hamburger = document.getElementById('hamburger');
  const mobileMenu = document.getElementById('mobile-menu');
  const mobileLinks = document.querySelectorAll('.mobile-link');

  if (!hamburger || !mobileMenu) return;

  hamburger.addEventListener('click', () => {
    const isOpen = mobileMenu.classList.toggle('open');
    hamburger.classList.toggle('open', isOpen);
    hamburger.setAttribute('aria-expanded', isOpen);
    document.body.style.overflow = isOpen ? 'hidden' : '';
  });

  mobileLinks.forEach(link => {
    link.addEventListener('click', () => {
      mobileMenu.classList.remove('open');
      hamburger.classList.remove('open');
      hamburger.setAttribute('aria-expanded', 'false');
      document.body.style.overflow = '';
    });
  });

  // Close on outside click
  document.addEventListener('click', (e) => {
    if (!mobileMenu.contains(e.target) && !hamburger.contains(e.target)) {
      mobileMenu.classList.remove('open');
      hamburger.classList.remove('open');
      document.body.style.overflow = '';
    }
  });
}

// ============================================================
// SCROLL REVEAL with Intersection Observer
// ============================================================
function initScrollReveal() {
  const elements = document.querySelectorAll('.scroll-reveal');

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const delay = entry.target.dataset.delay || 0;
        setTimeout(() => {
          entry.target.classList.add('revealed');
          // Trigger counter if inside revealed element
          const counters = entry.target.querySelectorAll('[data-target]');
          counters.forEach(el => {
            if (!el.dataset.animated) {
              el.dataset.animated = 'true';
              animateCounter(el, parseInt(el.dataset.target));
            }
          });
        }, parseInt(delay));
        observer.unobserve(entry.target);
      }
    });
  }, {
    threshold: 0.12,
    rootMargin: '0px 0px -60px 0px'
  });

  elements.forEach(el => observer.observe(el));
}

// ============================================================
// HERO STATS COUNTER (triggered once hero is visible)
// ============================================================
function initHeroCounters() {
  const statsSection = document.querySelector('.hero-stats');
  if (!statsSection) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const counters = entry.target.querySelectorAll('[data-target]');
        counters.forEach(el => {
          if (!el.dataset.animated) {
            el.dataset.animated = 'true';
            setTimeout(() => animateCounter(el, parseInt(el.dataset.target)), 800);
          }
        });
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.5 });

  observer.observe(statsSection);
}

// ============================================================
// ABOUT SECTION COUNTERS
// ============================================================
function initAboutCounters() {
  const aboutSection = document.querySelector('.about-badges');
  if (!aboutSection) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const counters = entry.target.querySelectorAll('[data-target]');
        counters.forEach(el => {
          if (!el.dataset.animated) {
            el.dataset.animated = 'true';
            animateCounter(el, parseInt(el.dataset.target));
          }
        });
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.5 });

  observer.observe(aboutSection);
}

// ============================================================
// FLIP CARDS: click/tap for mobile, hover handled by CSS
// ============================================================
function initFlipCards() {
  const cards = document.querySelectorAll('.service-card-flip');
  const isMobile = () => window.innerWidth < 768;

  cards.forEach(card => {
    // Touch/click for mobile
    card.addEventListener('click', () => {
      if (isMobile()) {
        card.classList.toggle('flipped');
      }
    });

    // Keyboard accessibility
    card.setAttribute('tabindex', '0');
    card.setAttribute('role', 'button');
    card.setAttribute('aria-label', 'Ver detalles del servicio');

    card.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        card.classList.toggle('flipped');
      }
    });
  });
}

// ============================================================
// SPEED BARS ANIMATION (Dashboard)
// ============================================================
function initSpeedBars() {
  const dashboard = document.querySelector('.dashboard-card');
  if (!dashboard) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const fills = entry.target.querySelectorAll('.speed-fill');
        fills.forEach(fill => {
          const targetW = fill.style.getPropertyValue('--w');
          fill.style.setProperty('--w', '0%');
          setTimeout(() => {
            fill.style.setProperty('--w', targetW);
          }, 300);
        });
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.4 });

  observer.observe(dashboard);
}

// ============================================================
// SMOOTH SCROLL for all anchor links
// ============================================================
function initSmoothScroll() {
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', (e) => {
      const target = document.querySelector(anchor.getAttribute('href'));
      if (target) {
        e.preventDefault();
        const offset = 80;
        const top = target.getBoundingClientRect().top + window.scrollY - offset;
        window.scrollTo({ top, behavior: 'smooth' });
      }
    });
  });
}

// ============================================================
// ACTIVE NAV LINK (highlight based on scroll position)
// ============================================================
function initActiveNavLinks() {
  const sections = document.querySelectorAll('section[id]');
  const navLinks = document.querySelectorAll('.nav-link:not(.nav-link-cta)');

  const onScroll = debounce(() => {
    let currentId = '';
    sections.forEach(section => {
      if (window.scrollY >= section.offsetTop - 140) {
        currentId = section.id;
      }
    });

    navLinks.forEach(link => {
      link.classList.remove('active');
      if (link.getAttribute('href') === '#' + currentId) {
        link.classList.add('active');
      }
    });
  }, 50);

  window.addEventListener('scroll', onScroll, { passive: true });
}

// ============================================================
// FORM SUBMISSION
// ============================================================
function handleFormSubmit(e) {
  e.preventDefault();
  const btn = document.getElementById('submit-btn');
  const btnText = document.getElementById('btn-text');

  btn.disabled = true;
  btn.style.opacity = '0.8';
  btnText.textContent = 'Enviando...';

  // Recopilar datos del formulario
  const payload = {
    name: document.getElementById('name').value,
    email: document.getElementById('email').value,
    service: document.getElementById('service').value,
    message: document.getElementById('message').value
  };

  // Enviar a n8n Webhook
  fetch('https://albertgracia.app.n8n.cloud/webhook/e96fabce-f52d-4bf8-822b-44c6cd290bed', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  })
  .then(response => {
    if (!response.ok) throw new Error('Network response was not ok');
    
    // UI Feedback: Éxito
    btnText.textContent = '✓ Enviado correctamente';
    btn.style.background = 'linear-gradient(135deg, #16a34a, #22c55e)';
    btn.style.animation = 'none';

    setTimeout(() => {
      btnText.textContent = 'Enviar Consulta Gratuita';
      btn.disabled = false;
      btn.style.opacity = '1';
      btn.style.background = '';
      btn.style.animation = '';
      document.getElementById('contact-form').reset();
    }, 3000);
  })
  .catch(error => {
    console.error('Error al enviar el formulario:', error);
    
    // UI Feedback: Error
    btnText.textContent = '❌ Error al enviar';
    btn.style.background = 'linear-gradient(135deg, #dc2626, #ef4444)';
    btn.style.animation = 'none';

    setTimeout(() => {
      btnText.textContent = 'Intentar de nuevo';
      btn.disabled = false;
      btn.style.opacity = '1';
      btn.style.background = '';
      btn.style.animation = '';
    }, 3000);
  });
}

// ============================================================
// PARALLAX: subtle background parallax on scroll
// ============================================================
function initParallax() {
  const heroBg = document.querySelector('.hero-bg-gradient');
  if (!heroBg) return;

  const onScroll = debounce(() => {
    const scrolled = window.scrollY;
    if (scrolled < window.innerHeight) {
      heroBg.style.transform = `translateY(${scrolled * 0.2}px)`;
    }
  }, 5);

  window.addEventListener('scroll', onScroll, { passive: true });
}

// ============================================================
// CURSOR GLOW (optional, desktop only)
// ============================================================
function initCursorGlow() {
  if (window.innerWidth < 1024) return;

  const glow = document.createElement('div');
  glow.style.cssText = `
    position: fixed; pointer-events: none; z-index: 9999;
    width: 300px; height: 300px;
    background: radial-gradient(circle, rgba(59,130,246,0.06) 0%, transparent 70%);
    transform: translate(-50%, -50%);
    transition: left 0.3s ease, top 0.3s ease;
    border-radius: 50%;
  `;
  document.body.appendChild(glow);

  let mx = 0, my = 0;
  document.addEventListener('mousemove', (e) => {
    mx = e.clientX;
    my = e.clientY;
    glow.style.left = mx + 'px';
    glow.style.top = my + 'px';
  });
}

// ============================================================
// ACTIVE NAV LINK STYLE
// ============================================================
const style = document.createElement('style');
style.textContent = `
  .nav-link.active {
    color: var(--primary-400) !important;
    background: rgba(59,130,246,0.08) !important;
  }
`;
document.head.appendChild(style);

// ============================================================
// ADD IMAGE FALLBACK: if images not found, show gradient placeholder
// ============================================================
function initImageFallbacks() {
  const serviceImages = document.querySelectorAll('.service-image');
  serviceImages.forEach(img => {
    img.addEventListener('error', () => {
      img.style.display = 'none';
    });
  });
}

// ============================================================
// INIT ALL
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
  initParticles();
  initNetworkCanvas();
  initNavbar();
  initMobileMenu();
  initScrollReveal();
  initHeroCounters();
  initAboutCounters();
  initFlipCards();
  initSpeedBars();
  initSmoothScroll();
  initActiveNavLinks();
  initParallax();
  initCursorGlow();
  initImageFallbacks();
});

// Expose globally for inline handlers
window.handleFormSubmit = handleFormSubmit;
