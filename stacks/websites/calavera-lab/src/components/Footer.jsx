import { motion } from 'framer-motion'
import { artistCredit } from '../data/content'

function Footer({ sealLogo, backgroundImage, backgroundY }) {
  return (
    <footer className="relative z-10 mx-4 mt-16 overflow-hidden rounded-[2rem] border border-white/10 px-4 py-20 sm:mx-6 sm:px-6 lg:px-8">
      <div className="absolute inset-0">
        <motion.img
          src={backgroundImage}
          alt="Sin perder el ritmo"
          style={{ y: backgroundY, scale: 1.12 }}
          className="h-full w-full object-cover object-center opacity-34"
        />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_rgba(0,0,0,0.06),_rgba(0,0,0,0.6)_48%,_rgba(0,0,0,0.92)_100%)]" />
        <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(0,0,0,0.8),rgba(0,0,0,0.28)_38%,rgba(0,0,0,0.9))]" />
        <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(0,0,0,0.72),rgba(0,0,0,0.18)_40%,rgba(0,0,0,0.78))]" />
      </div>
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_25%_36%,rgba(237,234,229,0.12),transparent_20%)]" />
      <div className="relative mx-auto grid max-w-7xl gap-10 border-t border-white/10 pt-10 lg:grid-cols-[1fr_auto] lg:items-end">
        <div>
          <p className="bone-title font-display text-2xl uppercase tracking-[0.12em] text-[var(--bone)] sm:text-4xl">CALAVERA LAB</p>
          <p className="mt-4 max-w-xl font-mono text-sm leading-7 text-white/62">
            Streetwear oscuro de edición limitada. Calavera como sello, precisión como dogma, identidad como producto final.
          </p>
          <div className="mt-8 max-w-2xl rounded-[1.5rem] border border-white/12 bg-black/30 px-5 py-5 shadow-[0_0_36px_rgba(237,234,229,0.05)] backdrop-blur-sm">
            <p className="font-mono text-[10px] uppercase tracking-[0.4em] text-white/46">Art Tribute</p>
            <p className="bone-title-soft mt-3 font-display text-lg uppercase tracking-[0.12em] text-[var(--bone)] sm:text-xl">{artistCredit}</p>
            <p className="mt-3 font-mono text-xs leading-6 text-white/56">
              Una firma visible para reconocer al artista de grabados que inspira muchos de los códigos visuales de la marca.
            </p>
            <a
              href="https://www.eduardorobledo.com/en"
              target="_blank"
              rel="noreferrer"
              className="mt-5 inline-flex items-center rounded-full border border-white/12 px-4 py-3 font-mono text-[10px] uppercase tracking-[0.32em] text-[var(--bone)] transition hover:border-[var(--bone)] hover:bg-[var(--bone)] hover:text-black"
            >
              Conoce La Obra E Historia De Eduardo Robledo
            </a>
          </div>
        </div>
        <div className="footer-seal-panel flex items-center gap-6 rounded-[1.75rem] px-5 py-4 sm:gap-8 sm:px-6">
          <img src={sealLogo} alt="Occult Streetwear seal" className="seal-spin seal-transparent h-32 w-32 opacity-95 sm:h-36 sm:w-36" />
          <div className="font-mono text-[10px] uppercase tracking-[0.4em] text-white/45">
            <p>Occult Streetwear</p>
            <p className="mt-3">MMXIV // Ritual Core Drop</p>
          </div>
        </div>
      </div>
    </footer>
  )
}

export default Footer
