import { motion } from 'framer-motion'
import { createWhatsAppLink } from '../lib/whatsapp'
import { trackWhatsAppIntent } from '../lib/analytics'

function UnboxingSection({ reveal, image }) {
  return (
    <motion.section {...reveal} className="mx-4 overflow-hidden rounded-[2rem] border border-white/10 sm:mx-6">
      <div className="grid lg:grid-cols-[1.15fr_0.85fr]">
        <div className="relative overflow-hidden">
          <img src={image} alt="Packaging negro mate CALAVERA LAB" className="h-full min-h-[28rem] w-full object-cover" />
          <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(0,0,0,0.1),rgba(0,0,0,0.78))]" />
        </div>
        <div className="flex flex-col justify-center bg-white/[0.03] px-6 py-14 sm:px-10 lg:px-14">
          <p className="font-mono text-[10px] uppercase tracking-[0.4em] text-white/45">Unboxing Experience</p>
          <h2 className="bone-title mt-5 max-w-xl font-display text-4xl uppercase leading-none tracking-[0.12em] sm:text-6xl">
            ESTA NO ES ROPA. ES IDENTIDAD.
          </h2>
          <p className="mt-6 max-w-lg font-mono text-sm leading-7 text-white/70 sm:text-base">
            Packaging negro mate, sello Calavera y capas de detalle pensadas para hacer del primer contacto un gesto de pertenencia. Cada apertura se siente como entrada al ritual.
          </p>
          <div className="mt-10 flex flex-wrap gap-4">
            <a
              href="#product-vault"
              className="inline-flex w-fit rounded-full border border-white/12 px-6 py-4 font-mono text-[11px] uppercase tracking-[0.35em] text-[var(--bone)] transition hover:border-[var(--bone)] hover:bg-[var(--bone)] hover:text-black"
            >
              Ver artefactos
            </a>
            <a
              href={createWhatsAppLink('Quiero reservar el packaging premium de CALAVERA LAB.')}
              target="_blank"
              rel="noreferrer"
              onClick={() => trackWhatsAppIntent('unboxing', 'reserve_packaging')}
              className="inline-flex w-fit rounded-full border border-white/12 px-6 py-4 font-mono text-[11px] uppercase tracking-[0.35em] text-[var(--bone)] transition hover:border-[var(--bone)]"
            >
              Reservar por WhatsApp
            </a>
          </div>
        </div>
      </div>
    </motion.section>
  )
}

export default UnboxingSection
