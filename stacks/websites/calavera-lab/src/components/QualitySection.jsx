import { motion } from 'framer-motion'
import { artistCredit } from '../data/content'

function QualitySection({ reveal, qualityLabel, detailImage, pillars }) {
  return (
    <motion.section id="quality" {...reveal} className="mx-auto grid max-w-7xl gap-6 px-4 py-20 sm:px-6 lg:grid-cols-[0.92fr_1.08fr] lg:px-8">
      <div className="overflow-hidden rounded-[1.8rem] border border-white/10 bg-white/[0.03] p-6 sm:p-8">
        <div className="grid gap-4 sm:grid-cols-[0.8fr_1.2fr]">
          <div className="overflow-hidden rounded-[1.4rem] border border-white/10 bg-black/50 p-4">
            <img src={qualityLabel} alt="Etiqueta Occult Streetwear" className="h-full w-full object-contain" />
          </div>
          <div className="overflow-hidden rounded-[1.4rem] border border-white/10">
            <img src={detailImage} alt="Detalle de bordado CALAVERA LAB" className="h-full min-h-[18rem] w-full object-cover" />
          </div>
        </div>
      </div>

      <div className="circuit-border rounded-[1.8rem] px-6 py-8 sm:px-10 sm:py-12">
        <p className="bone-label font-mono text-[10px] uppercase tracking-[0.4em] text-white/45">Anatomy Of Quality</p>
        <h2 className="bone-title mt-5 font-display text-3xl uppercase tracking-[0.12em] sm:text-5xl">INGENIERÍA OSCURA</h2>
        <p className="mt-6 max-w-2xl font-mono text-sm leading-7 text-white/72 sm:text-base">
          Etiquetado OCCULT STREETWEAR, parches bordados y gramaje premium integrados como lenguaje de precisión. Calavera deja de ser logo y se convierte en sistema constructivo.
        </p>
        <div className="mt-10 grid gap-6 sm:grid-cols-3">
          {pillars.map(([title, text]) => (
            <div key={title} className="border-t border-white/10 pt-5">
              <h3 className="bone-title-soft font-display text-lg uppercase tracking-[0.1em]">{title}</h3>
              <p className="mt-3 font-mono text-sm leading-7 text-white/66">{text}</p>
            </div>
          ))}
        </div>
        <div className="mt-10 rounded-[1.5rem] border border-white/12 bg-white/[0.04] px-5 py-5 shadow-[0_0_36px_rgba(237,234,229,0.04)]">
          <p className="bone-label font-mono text-[10px] uppercase tracking-[0.4em] text-white/44">Art Tribute</p>
          <p className="bone-title-soft mt-3 font-display text-lg uppercase tracking-[0.12em] text-[var(--bone)] sm:text-xl">{artistCredit}</p>
          <p className="mt-3 max-w-xl font-mono text-xs leading-6 text-white/56">
            Homenaje editorial al artista de grabados cuya sensibilidad visual inspira parte del lenguaje gráfico de la marca.
          </p>
        </div>
      </div>
    </motion.section>
  )
}

export default QualitySection
