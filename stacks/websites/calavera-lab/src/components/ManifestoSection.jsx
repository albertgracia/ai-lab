import { AnimatePresence, motion } from 'framer-motion'
import { useMemo, useState } from 'react'

function ManifestoSection({ reveal, panels, activePanel, setActivePanel }) {
  const [hoveredPanel, setHoveredPanel] = useState(0)
  const currentPanel = panels[activePanel]
  const desktopPanel = useMemo(() => panels[hoveredPanel] ?? panels[0], [hoveredPanel, panels])

  return (
    <motion.section id="manifesto" {...reveal} className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8">
      <div className="mb-10 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.4em] text-white/45">Campaign Manifesto</p>
          <h2 className="bone-title mt-4 font-display text-3xl uppercase tracking-[0.12em] sm:text-5xl">The Cult Signal</h2>
        </div>
        <p className="max-w-xl font-mono text-sm leading-7 text-white/68">
          Cuatro paneles. Cuatro declaraciones. Un sistema visual guiado por Calavera, materia negra y precisión editorial UHD.
        </p>
      </div>

      <div className="hidden gap-6 lg:grid lg:grid-cols-[1.15fr_0.85fr] lg:items-stretch">
        <div className="manifesto-stage group relative min-h-[44rem] overflow-hidden rounded-[2rem] border border-white/10 bg-black/70">
          <AnimatePresence mode="wait">
            <motion.div
              key={desktopPanel.title}
              initial={{ opacity: 0, scale: 1.08, filter: 'blur(8px)' }}
              animate={{ opacity: 1, scale: 1, filter: 'blur(0px)' }}
              exit={{ opacity: 0, scale: 1.05, filter: 'blur(10px)' }}
              transition={{ duration: 0.75, ease: [0.22, 1, 0.36, 1] }}
              className="absolute inset-0"
            >
              <img src={desktopPanel.image} alt={desktopPanel.title} className="h-full w-full object-contain p-6" />
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_rgba(255,255,255,0.02),_transparent_34%),linear-gradient(180deg,rgba(0,0,0,0.06),rgba(0,0,0,0.78))]" />
              <div className="manifesto-flare absolute inset-y-0 left-[-22%] w-[42%] -skew-x-12 bg-[linear-gradient(90deg,transparent,rgba(255,255,255,0.22),transparent)] opacity-0" />
            </motion.div>
          </AnimatePresence>

          <div className="absolute inset-x-0 top-0 h-28 bg-[linear-gradient(180deg,rgba(0,0,0,0.7),transparent)]" />
          <div className="absolute inset-x-0 bottom-0 bg-[linear-gradient(180deg,transparent,rgba(0,0,0,0.86))] p-8">
            <div className="max-w-2xl space-y-4">
              <p className="font-mono text-[10px] uppercase tracking-[0.42em] text-white/48">UHD Reveal // Full Campaign Image</p>
              <h3 className="bone-title font-display text-4xl uppercase tracking-[0.12em] text-[var(--bone)] xl:text-5xl">{desktopPanel.title}</h3>
              <p className="max-w-xl font-mono text-sm leading-7 text-white/72">{desktopPanel.copy}</p>
            </div>
          </div>
        </div>

        <div className="grid gap-4">
          {panels.map((panel, index) => {
            const isActive = hoveredPanel === index
            return (
              <article
                key={panel.title}
                onMouseEnter={() => setHoveredPanel(index)}
                className={`group relative overflow-hidden rounded-[1.6rem] border px-5 py-6 transition duration-500 ${
                  isActive
                    ? 'border-[var(--bone)] bg-white/[0.08] shadow-[0_0_36px_rgba(237,234,229,0.06)]'
                    : 'border-white/10 bg-white/[0.03] hover:border-white/25 hover:bg-white/[0.05]'
                }`}
              >
                <div className="absolute inset-0 opacity-20 transition duration-500 group-hover:opacity-35">
                  <img src={panel.image} alt={panel.title} className="h-full w-full object-cover" />
                </div>
                <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(0,0,0,0.92),rgba(0,0,0,0.58))]" />
                <div className="relative flex h-full min-h-[9.5rem] flex-col justify-between">
                  <div className="flex items-center justify-between gap-4">
                    <p className="font-mono text-[10px] uppercase tracking-[0.42em] text-white/45">Panel 0{index + 1}</p>
                    <span className={`h-2.5 w-2.5 rounded-full transition ${isActive ? 'bg-[var(--bone)] shadow-[0_0_18px_rgba(237,234,229,0.8)]' : 'bg-white/25'}`} />
                  </div>
                  <div className="space-y-3">
                    <h3 className="bone-title-soft font-display text-2xl uppercase leading-none tracking-[0.1em] text-[var(--bone)]">{panel.title}</h3>
                    <p className="max-w-[22rem] font-mono text-xs leading-6 text-white/66">{panel.copy}</p>
                  </div>
                </div>
              </article>
            )
          })}
        </div>
      </div>

      <div className="space-y-4 lg:hidden">
        <div className="overflow-hidden rounded-[1.8rem] border border-white/10">
          <img src={currentPanel.image} alt={currentPanel.title} className="h-[28rem] w-full object-cover" />
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {panels.map((panel, index) => (
            <button
              key={panel.title}
              onClick={() => setActivePanel(index)}
              className={`rounded-[1.25rem] border px-4 py-4 text-left transition ${
                activePanel === index ? 'border-[var(--bone)] bg-white/[0.06]' : 'border-white/10 bg-white/[0.02]'
              }`}
            >
                <span className="bone-title-soft font-display text-sm uppercase tracking-[0.09em]">{panel.title}</span>
            </button>
          ))}
        </div>
        <p className="font-mono text-sm leading-7 text-white/70">{currentPanel.copy}</p>
      </div>
    </motion.section>
  )
}

export default ManifestoSection
