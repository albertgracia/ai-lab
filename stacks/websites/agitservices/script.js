/**
 * AG IT Services — script.js
 * Dark Luxury Corporate IT Landing Page
 * Interactions: Navbar, Particles, Flip Cards, Counters, Scroll Animations
 */

'use strict';

// ─────────────────────────────────────────────────────────────
// UTILITIES
// ─────────────────────────────────────────────────────────────
function debounce(fn, delay = 100) {
    let t;
    return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), delay); };
}

// ─────────────────────────────────────────────────────────────
// PARTICLES
// ─────────────────────────────────────────────────────────────
function initParticles() {
    const container = document.getElementById('particles');
    if (!container) return;

    const count = window.innerWidth <= 768 ? 20 : 50;
    const fragment = document.createDocumentFragment();

    for (let i = 0; i < count; i++) {
        const p = document.createElement('div');
        p.className = 'particle';
        p.style.cssText = `
            left: ${Math.random() * 100}%;
            top: ${Math.random() * 100}%;
            animation-delay: ${(Math.random() * 20).toFixed(2)}s;
            animation-duration: ${(15 + Math.random() * 10).toFixed(2)}s;
        `;
        fragment.appendChild(p);
    }
    container.appendChild(fragment);
}

// ─────────────────────────────────────────────────────────────
// NAVBAR — sticky + blur on scroll + mobile menu
// ─────────────────────────────────────────────────────────────
function initNavbar() {
    const navbar  = document.getElementById('navbar');
    const toggle  = document.getElementById('menuToggle');
    const menu    = document.getElementById('mobileMenu');
    const mLinks  = document.querySelectorAll('.mobile-nav-link');

    if (!navbar) return;

    // Sticky scroll
    const onScroll = debounce(() => {
        navbar.classList.toggle('scrolled', window.scrollY > 20);
    }, 10);
    window.addEventListener('scroll', onScroll, { passive: true });

    // Mobile toggle
    if (toggle && menu) {
        toggle.addEventListener('click', () => {
            const open = menu.classList.toggle('open');
            toggle.classList.toggle('active', open);
            toggle.setAttribute('aria-expanded', String(open));
            document.body.style.overflow = open ? 'hidden' : '';
        });

        // Close on link click
        mLinks.forEach(link => {
            link.addEventListener('click', () => {
                menu.classList.remove('open');
                toggle.classList.remove('active');
                toggle.setAttribute('aria-expanded', 'false');
                document.body.style.overflow = '';
            });
        });
    }

    // Smooth scroll for all anchor links
    document.querySelectorAll('a[href^="#"]').forEach(link => {
        link.addEventListener('click', e => {
            const target = document.querySelector(link.getAttribute('href'));
            if (target) {
                e.preventDefault();
                const offset = navbar.offsetHeight + 20;
                const top = target.getBoundingClientRect().top + window.scrollY - offset;
                window.scrollTo({ top, behavior: 'smooth' });
            }
        });
    });
}

// ─────────────────────────────────────────────────────────────
// FLIP CARDS — hover (desktop) + tap/click (mobile)
// ─────────────────────────────────────────────────────────────
function initFlipCards() {
    const cards = document.querySelectorAll('.service-card-flip');
    const isTouchDevice = () => window.matchMedia('(hover: none)').matches;

    cards.forEach(card => {
        // Touch / click flip for mobile
        card.addEventListener('click', () => {
            if (isTouchDevice()) {
                card.classList.toggle('flipped');
            }
        });

        // Keyboard accessibility
        card.setAttribute('tabindex', '0');
        card.setAttribute('role', 'button');
        card.setAttribute('aria-label', 'Ver detalles del servicio');
        card.addEventListener('keydown', e => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                card.classList.toggle('flipped');
            }
        });
    });
}

// ─────────────────────────────────────────────────────────────
// ANIMATED COUNTERS
// ─────────────────────────────────────────────────────────────
function animateCounter(el, target, duration = 2000) {
    const isDecimal = el.hasAttribute('data-decimal');
    const start = performance.now();

    function update(now) {
        const elapsed = now - start;
        const progress = Math.min(elapsed / duration, 1);
        // Ease out quad
        const eased = 1 - (1 - progress) ** 3;
        const current = eased * target;

        if (isDecimal) {
            el.textContent = current.toFixed(1);
        } else {
            el.textContent = Math.round(current).toLocaleString('es-ES');
        }

        if (progress < 1) requestAnimationFrame(update);
        else el.textContent = isDecimal ? target.toFixed(1) : Math.round(target).toLocaleString('es-ES');
    }

    requestAnimationFrame(update);
}

function initCounters() {
    const counters = document.querySelectorAll('.stat-number[data-target]');
    if (!counters.length) return;

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const el = entry.target;
                const target = parseFloat(el.getAttribute('data-target'));
                animateCounter(el, target, 2200);
                observer.unobserve(el);
            }
        });
    }, { threshold: 0.5 });

    counters.forEach(c => observer.observe(c));
}

// ─────────────────────────────────────────────────────────────
// SCROLL REVEAL — Intersection Observer with stagger
// ─────────────────────────────────────────────────────────────
function initScrollReveal() {
    const cards = document.querySelectorAll('.reveal-card');
    if (!cards.length) return;

    const observer = new IntersectionObserver((entries) => {
        const visible = entries.filter(e => e.isIntersecting);

        // Group visible cards by their parent section for stagger
        visible.forEach((entry, i) => {
            const el = entry.target;
            const siblings = [...el.parentElement.querySelectorAll('.reveal-card:not(.revealed)')];
            const idx = siblings.indexOf(el);

            setTimeout(() => {
                el.classList.add('revealed');
                observer.unobserve(el);
            }, idx * 100);
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -80px 0px'
    });

    cards.forEach(card => observer.observe(card));
}

// ─────────────────────────────────────────────────────────────
// PARALLAX — gentle background shift on scroll
// ─────────────────────────────────────────────────────────────
function initParallax() {
    const heroBg = document.querySelector('.hero-bg-gradient');
    if (!heroBg) return;

    const onScroll = debounce(() => {
        const scrolled = window.scrollY;
        heroBg.style.transform = `translateY(${scrolled * 0.15}px)`;
    }, 5);

    window.addEventListener('scroll', onScroll, { passive: true });
}

// ─────────────────────────────────────────────────────────────
// ACTIVE NAV LINK — highlight current section
// ─────────────────────────────────────────────────────────────
function initActiveNav() {
    const sections = document.querySelectorAll('section[id]');
    const navLinks = document.querySelectorAll('.nav-link');
    if (!sections.length || !navLinks.length) return;

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const id = entry.target.id;
                navLinks.forEach(link => {
                    const active = link.getAttribute('href') === `#${id}`;
                    link.style.color = active ? 'var(--primary-400)' : '';
                });
            }
        });
    }, { threshold: 0.4 });

    sections.forEach(s => observer.observe(s));
}

// ─────────────────────────────────────────────────────────────
// CTA BUTTON — click ripple effect
// ─────────────────────────────────────────────────────────────
function initRipple() {
    document.querySelectorAll('.btn-primary').forEach(btn => {
        btn.addEventListener('click', function(e) {
            const rect = this.getBoundingClientRect();
            const ripple = document.createElement('span');
            const size = Math.max(rect.width, rect.height);
            ripple.style.cssText = `
                position: absolute;
                width: ${size}px; height: ${size}px;
                border-radius: 50%;
                background: rgba(255,255,255,0.15);
                top: ${e.clientY - rect.top - size / 2}px;
                left: ${e.clientX - rect.left - size / 2}px;
                transform: scale(0);
                animation: ripple-expand 0.6s ease-out forwards;
                pointer-events: none;
            `;
            // Ensure button has position relative
            this.style.position = 'relative';
            this.style.overflow = 'hidden';
            this.appendChild(ripple);
            setTimeout(() => ripple.remove(), 600);
        });
    });

    // Inject ripple keyframe
    const style = document.createElement('style');
    style.textContent = `
        @keyframes ripple-expand {
            to { transform: scale(2.5); opacity: 0; }
        }
    `;
    document.head.appendChild(style);
}

// ─────────────────────────────────────────────────────────────
// HERO CTA — micro interaction on hover
// ─────────────────────────────────────────────────────────────
function initHeroInteraction() {
    const heroCTA = document.getElementById('heroCTA');
    if (!heroCTA) return;

    heroCTA.addEventListener('mouseenter', () => {
        heroCTA.textContent = '→ Habla con un Experto';
    });
    heroCTA.addEventListener('mouseleave', () => {
        heroCTA.textContent = 'Habla con un Experto';
    });
}

// ─────────────────────────────────────────────────────────────
// INIT ALL
// ─────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initParticles();
    initNavbar();
    initFlipCards();
    initCounters();
    initScrollReveal();
    initParallax();
    initActiveNav();
    initRipple();
    initHeroInteraction();

    // Restore scroll on hero load
    if ('scrollRestoration' in history) {
        history.scrollRestoration = 'manual';
    }

    console.log('%c🚀 AG IT Services', 'color:#3B82F6;font-size:1.2rem;font-weight:bold;');
    console.log('%cTu tecnología operativa sin interrupciones.', 'color:#60A5FA;');
});
