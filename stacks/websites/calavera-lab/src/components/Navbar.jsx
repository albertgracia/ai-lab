import { motion } from 'framer-motion'
import { createWhatsAppLink } from '../lib/whatsapp'
import { trackWhatsAppIntent } from '../lib/analytics'

function Navbar({ showNav, logo, links }) {
  return (
    <motion.header
      initial={{ opacity: 0, y: -24 }}
      animate={{ opacity: showNav ? 1 : 0, y: showNav ? 0 : -24 }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
      className="fixed inset-x-0 top-0 z-30 px-4 py-4 sm:px-6"
    >
      <div className="nav-shell mx-auto flex max-w-7xl items-center justify-between rounded-full px-4 py-3 sm:px-6">
        <a href="/" className="flex items-center gap-4 text-[10px] uppercase tracking-[0.38em] text-white/80">
          <img src={logo} alt="CALAVERA LAB" className="h-12 w-auto sm:h-14" />
          <span className="bone-label hidden border-l border-white/10 pl-4 text-[11px] tracking-[0.42em] text-[var(--bone)] sm:block">CALAVERA LAB</span>
        </a>
        <div className="flex items-center gap-4 text-[10px] uppercase tracking-[0.38em] text-white/65 sm:gap-8">
          {links.map((link) => (
            <a key={link.href} href={link.href} className="bone-label hidden transition hover:text-[var(--bone)] sm:block">
              {link.label}
            </a>
          ))}
          <a
            href={createWhatsAppLink('Quiero entrar al ritual de CALAVERA LAB y recibir el drop actual.')}
            target="_blank"
            rel="noreferrer"
            onClick={() => trackWhatsAppIntent('navbar', 'ritual_access')}
            className="bone-button rounded-full border border-white/12 bg-white/[0.03] px-4 py-2.5 text-[var(--bone)] shadow-[0_0_24px_rgba(237,234,229,0.05)] transition hover:bg-[var(--bone)] hover:text-black"
          >
            WhatsApp
          </a>
        </div>
      </div>
    </motion.header>
  )
}

export default Navbar
