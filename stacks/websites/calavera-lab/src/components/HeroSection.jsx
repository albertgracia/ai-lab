import { motion } from 'framer-motion'
import { createWhatsAppLink } from '../lib/whatsapp'
import { trackWhatsAppIntent } from '../lib/analytics'
import { artistCredit } from '../data/content'

function HeroSection({ logo, backgroundImage, heroY, auraY, reveal, stats }) {
  return (
    <section className="circuit-border mx-4 mt-4 min-h-screen overflow-hidden rounded-[2rem] px-4 pb-16 pt-28 sm:mx-6 sm:px-8 lg:px-10">
      <div className="absolute inset-0">
        <motion.img
          src={backgroundImage}
          alt="Esqueletos de fiesta"
          style={{ y: auraY, scale: 1.14 }}
          className="h-full w-full object-cover object-center opacity-44"
        />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_rgba(0,0,0,0.04),_rgba(0,0,0,0.48)_42%,_rgba(0,0,0,0.88)_100%)]" />
        <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(0,0,0,0.62),rgba(0,0,0,0.18)_44%,rgba(0,0,0,0.76))]" />
        <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(0,0,0,0.18),transparent_20%,transparent_72%,rgba(0,0,0,0.58))]" />
      </div>
      <motion.div style={{ y: auraY }} className="pointer-events-none absolute inset-x-0 top-0 h-[44rem] bg-[radial-gradient(circle_at_center,_rgba(237,234,229,0.18),_transparent_42%)] opacity-70" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_65%_34%,rgba(237,234,229,0.12),transparent_18%)]" />
      <div className="relative mx-auto grid max-w-7xl gap-12 lg:grid-cols-[1.1fr_0.9fr] lg:items-end">
        <motion.div {...reveal} className="order-2 flex flex-col gap-8 lg:order-1 lg:pb-14">
          <div className="space-y-5">
            <p className="bone-label text-[11px] uppercase tracking-[0.45em] text-white/55">Cyber-Occult Luxury Streetwear</p>
            <h1 className="bone-title max-w-3xl font-display text-5xl uppercase leading-none tracking-[0.08em] text-[var(--bone)] sm:text-7xl xl:text-[7rem]">
              NOT FOR EVERYONE
            </h1>
            <p className="max-w-xl font-mono text-sm leading-7 text-white/72 sm:text-base">
              Streetwear oscuro. Edición limitada. Calavera como emblema, precisión ceremonial y una presencia hecha para quienes no se mezclan.
            </p>
          </div>

          <div className="flex flex-col items-start gap-4 sm:flex-row sm:items-center">
            <a
              href="#product-vault"
              className="bone-button group inline-flex items-center rounded-full border border-[var(--bone)] px-7 py-4 font-mono text-[11px] uppercase tracking-[0.35em] text-[var(--bone)] transition duration-500 hover:bg-[var(--bone)] hover:text-black"
            >
              ENTRAR AL RITUAL
            </a>
            <a
              href="/coleccion"
              className="bone-button group inline-flex items-center rounded-full border border-white/12 px-7 py-4 font-mono text-[11px] uppercase tracking-[0.35em] text-[var(--bone)] transition duration-500 hover:border-[var(--bone)] hover:bg-white/[0.05]"
            >
              VER COLECCION TEXTIL
            </a>
            <a
              href={createWhatsAppLink('Quiero acceso prioritario al ritual de CALAVERA LAB.')}
              target="_blank"
              rel="noreferrer"
              onClick={() => trackWhatsAppIntent('hero', 'priority_access')}
              className="bone-label inline-flex items-center gap-3 text-[10px] uppercase tracking-[0.38em] text-white/48 transition hover:text-[var(--bone)]"
            >
              <span className="h-px w-10 bg-white/20" />
              Acceso directo por WhatsApp
            </a>
          </div>

          <div className="grid gap-6 border-t border-white/10 pt-8 sm:grid-cols-3">
            {stats.map(([label, value]) => (
              <div key={label}>
                <p className="bone-label font-mono text-[10px] uppercase tracking-[0.4em] text-white/45">{label}</p>
                <p className="mt-3 text-sm uppercase tracking-[0.2em] text-[var(--bone)]">{value}</p>
              </div>
            ))}
          </div>
          <div className="max-w-3xl rounded-[1.5rem] border border-white/12 bg-white/[0.05] px-5 py-5 shadow-[0_0_40px_rgba(237,234,229,0.05)] backdrop-blur-sm">
              <p className="bone-label font-mono text-[10px] uppercase tracking-[0.4em] text-white/45">Art Tribute</p>
            <p className="bone-title-soft mt-3 font-display text-lg uppercase tracking-[0.12em] text-[var(--bone)] sm:text-xl">
              {artistCredit}
            </p>
            <p className="mt-3 max-w-2xl font-mono text-xs leading-6 text-white/58">
              CALAVERA LAB rinde homenaje al imaginario grabado de Eduardo Robledo como una influencia esencial en la energía visual del ritual.
            </p>
          </div>
        </motion.div>

        <motion.div style={{ y: heroY }} {...reveal} className="order-1 flex justify-center lg:order-2 lg:justify-end">
          <div className="relative isolate w-full max-w-[42rem] overflow-hidden rounded-[2rem] border border-white/10 bg-black/20 px-6 py-10 shadow-[0_0_90px_rgba(255,255,255,0.08)] backdrop-blur-md sm:px-10">
            <div className="absolute inset-0 bg-[linear-gradient(135deg,rgba(255,255,255,0.08),transparent_35%,transparent_70%,rgba(255,255,255,0.05))]" />
            <div className="absolute inset-x-8 top-8 h-px bg-white/10" />
            <div className="absolute inset-y-8 left-8 w-px bg-white/8" />
            <img src={logo} alt="Logo CALAVERA LAB" className="relative z-10 mx-auto h-auto w-full max-w-[29rem] drop-shadow-[0_0_35px_rgba(237,234,229,0.12)]" />
          </div>
        </motion.div>
      </div>
    </section>
  )
}

export default HeroSection
