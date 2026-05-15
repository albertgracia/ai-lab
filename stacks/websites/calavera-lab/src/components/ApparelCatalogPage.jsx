import { AnimatePresence, motion } from 'framer-motion'
import { useMemo, useState } from 'react'
import CheckoutModal from './CheckoutModal'
import { apparelTitleMap, canonicalizeApparelSlug, getApparelDescription } from '../data/apparelCatalog'

const apparelImages = Object.entries(
  import.meta.glob('../assets/catalogo-camisetas-sudaderas/*.{webp,png,jpg,jpeg}', {
    eager: true,
    import: 'default',
  }),
)
  .map(([filePath, src]) => ({ filePath, src }))
  .sort((a, b) => a.filePath.localeCompare(b.filePath))

const mookupEntries = Object.entries(
  import.meta.glob('../assets/catalogo-mookups/*.{webp,png,jpg,jpeg}', {
    eager: true,
    import: 'default',
  }),
)
  .map(([filePath, src]) => ({ filePath, src }))
  .sort((a, b) => a.filePath.localeCompare(b.filePath))

const groupedDesigns = Object.values(
  apparelImages.reduce((acc, { filePath, src }) => {
    const fileName = filePath.split('/').pop()?.replace(/\.(webp|png|jpg|jpeg)$/i, '') || ''
    const isHoodie = fileName.endsWith('-sud')
    const slug = canonicalizeApparelSlug(isHoodie ? fileName.replace(/-sud$/, '') : fileName)
    const title = apparelTitleMap[slug]
    if (!title) return acc

    const variant = isHoodie ? 'sudadera' : 'camiseta'
    acc[slug] = acc[slug] || {
      slug,
      title,
      variants: {},
    }

    acc[slug].variants[variant] = {
      id: `${slug}-${variant}`,
      name: `${title} ${isHoodie ? 'Sudadera' : 'Camiseta'}`,
      designTitle: title,
      variant,
      price: isHoodie ? '69 EUR' : '39 EUR',
      badge: isHoodie ? 'SUDADERA PREMIUM' : 'CAMISETA PREMIUM',
      image: src,
      note: getApparelDescription(title, variant),
    }

    return acc
  }, {}),
).sort((a, b) => a.title.localeCompare(b.title))

const normalize = (value) => String(value || '').toLowerCase().replace(/[^a-z0-9]/g, '')

function getDesignMockups(design) {
  const designKey = normalize(design.slug)
  const generic = []
  const specific = []

  for (const entry of mookupEntries) {
    const fileSlug = entry.filePath.split('/').pop()?.replace(/\.(webp|png|jpg|jpeg)$/i, '') || ''
    const normalizedFile = normalize(fileSlug)

    if (normalizedFile.includes('camisetatrasera') || normalizedFile.includes('sudaderatrasera')) {
      generic.push(entry.src)
      continue
    }

    if (normalizedFile.includes(designKey) || designKey.includes(normalizedFile.replace(/^mookup/, ''))) {
      specific.push(entry.src)
    }
  }

  return [...specific, ...generic]
}

function ApparelCatalogPage({ pathname = '/coleccion', backgroundImage, auraY }) {
  const [activeType, setActiveType] = useState('all')
  const [activeDesign, setActiveDesign] = useState('all')
  const [searchTerm, setSearchTerm] = useState('')
  const [variantOverrides, setVariantOverrides] = useState({})
  const [checkoutProduct, setCheckoutProduct] = useState(null)
  const [mookupLightbox, setMookupLightbox] = useState(null)

  const detailSlug = pathname.startsWith('/coleccion/') ? decodeURIComponent(pathname.replace('/coleccion/', '')) : ''
  const detailDesign = groupedDesigns.find((design) => design.slug === detailSlug)

  const linkedMookups = useMemo(
    () =>
      mookupEntries.map((entry) => {
        const fileSlug = entry.filePath.split('/').pop()?.replace(/\.(webp|png|jpg|jpeg)$/i, '') || ''
        const normalizedFile = normalize(fileSlug.replace(/^mookup/, ''))
        const relatedDesign = groupedDesigns.find((design) => normalizedFile.includes(normalize(design.slug)))

        return {
          src: entry.src,
          relatedSlug: relatedDesign?.slug || '',
          relatedTitle: relatedDesign?.title || '',
        }
      }),
    [],
  )

  const filteredDesigns = useMemo(() => {
    const normalizedSearch = searchTerm.trim().toLowerCase()

    return groupedDesigns.filter((design) => {
      const matchesDesign = activeDesign === 'all' || design.slug === activeDesign
      const matchesType =
        activeType === 'all' ||
        (activeType === 'camiseta' && design.variants.camiseta) ||
        (activeType === 'sudadera' && design.variants.sudadera)
      const matchesSearch = !normalizedSearch || design.title.toLowerCase().includes(normalizedSearch)

      return matchesDesign && matchesType && matchesSearch
    })
  }, [activeDesign, activeType, searchTerm])

  const getActiveVariant = (design) => {
    const preferred = variantOverrides[design.slug]
    if (preferred && design.variants[preferred]) return design.variants[preferred]
    if (activeType !== 'all' && design.variants[activeType]) return design.variants[activeType]
    return design.variants.camiseta || design.variants.sudadera
  }

  return (
    <>
      {detailDesign ? (
        <DesignDetailView design={detailDesign} onCheckout={setCheckoutProduct} />
      ) : (
        <main className="relative z-10 px-4 pb-20 pt-32 sm:px-6 lg:px-8">
          <section className="circuit-border relative mx-auto max-w-7xl overflow-hidden rounded-[2rem] px-5 py-10 sm:px-8 sm:py-14">
            <div className="absolute inset-0">
              <motion.img
                src={backgroundImage}
                alt="Fondo editorial CALAVERA LAB"
                style={{ y: auraY, scale: 1.14 }}
                className="h-full w-full object-cover object-center opacity-36"
              />
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_rgba(0,0,0,0.04),_rgba(0,0,0,0.48)_42%,_rgba(0,0,0,0.88)_100%)]" />
              <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(0,0,0,0.62),rgba(0,0,0,0.18)_44%,rgba(0,0,0,0.76))]" />
              <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(0,0,0,0.18),transparent_20%,transparent_72%,rgba(0,0,0,0.58))]" />
            </div>
            <motion.div style={{ y: auraY }} className="pointer-events-none absolute inset-x-0 top-0 h-[44rem] bg-[radial-gradient(circle_at_center,_rgba(237,234,229,0.18),_transparent_42%)] opacity-70" />
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_65%_34%,rgba(237,234,229,0.12),transparent_18%)]" />

            <div className="relative grid gap-10 lg:grid-cols-[0.92fr_1.08fr] lg:items-end">
              <div className="space-y-6">
                <p className="font-mono text-[10px] uppercase tracking-[0.42em] text-white/45">Coleccion Secundaria</p>
                <h1 className="bone-title font-display text-4xl uppercase tracking-[0.1em] text-[var(--bone)] sm:text-6xl">Camisetas Y Sudaderas</h1>
                <p className="max-w-2xl font-mono text-sm leading-7 text-white/68 sm:text-base">
                  Una pagina secundaria para recorrer toda la coleccion textil con el mismo lenguaje visual de CALAVERA LAB: atmosfera oscura, producto protagonista y compra directa desde una experiencia editorial.
                </p>

                <div className="space-y-4 pt-2">
                  <div>
                    <label className="block">
                      <span className="font-mono text-[10px] uppercase tracking-[0.32em] text-white/42">Buscar Por Diseño</span>
                      <input
                        type="text"
                        value={searchTerm}
                        onChange={(event) => setSearchTerm(event.target.value)}
                        placeholder="Escribe un nombre de diseño"
                        className="mt-3 w-full max-w-xl rounded-full border border-white/12 bg-black/35 px-5 py-3 font-mono text-sm text-[var(--bone)] outline-none placeholder:text-white/24"
                      />
                    </label>
                  </div>

                  <div className="flex flex-wrap gap-3">
                    {[
                      ['all', 'Todo'],
                      ['camiseta', 'Camisetas'],
                      ['sudadera', 'Sudaderas'],
                    ].map(([value, label]) => (
                      <button
                        key={value}
                        onClick={() => setActiveType(value)}
                        className={`rounded-full border px-5 py-3 font-mono text-[10px] uppercase tracking-[0.35em] transition ${
                          activeType === value ? 'border-[var(--bone)] bg-[var(--bone)] text-black' : 'border-white/12 text-[var(--bone)]'
                        }`}
                      >
                        {label}
                      </button>
                    ))}
                  </div>

                  <div className="flex flex-wrap gap-3">
                    <button
                      onClick={() => setActiveDesign('all')}
                      className={`rounded-full border px-4 py-2.5 font-mono text-[10px] uppercase tracking-[0.3em] transition ${
                        activeDesign === 'all' ? 'border-white/40 bg-white/[0.08] text-[var(--bone)]' : 'border-white/10 text-white/56'
                      }`}
                    >
                      Todos Los Diseños
                    </button>
                    {groupedDesigns.map((design) => (
                      <button
                        key={design.slug}
                        onClick={() => setActiveDesign(design.slug)}
                        className={`rounded-full border px-4 py-2.5 font-mono text-[10px] uppercase tracking-[0.3em] transition ${
                          activeDesign === design.slug ? 'border-white/40 bg-white/[0.08] text-[var(--bone)]' : 'border-white/10 text-white/56'
                        }`}
                      >
                        {design.title}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                {linkedMookups.length > 0 && (
                  <div className="overflow-hidden rounded-[1.6rem] border border-white/10 bg-white/[0.03] py-6 shadow-[0_0_24px_rgba(237,234,229,0.03)]">
                    <div className="px-5 pb-5 text-center">
                      <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-white/42">Mookup Carousel</p>
                    </div>
                    <MookupCarousel items={linkedMookups} onOpen={setMookupLightbox} />
                  </div>
                )}

                <div className="grid gap-4 sm:grid-cols-3">
                  {[
                    ['Camisetas', '39 EUR'],
                    ['Sudaderas', '69 EUR'],
                    ['Interactivo', 'Hover Swap'],
                  ].map(([label, value]) => (
                    <div key={label} className="rounded-[1.5rem] border border-white/10 bg-white/[0.03] px-5 py-6">
                      <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-white/42">{label}</p>
                      <p className="bone-title-soft mt-3 font-display text-2xl uppercase tracking-[0.08em] text-[var(--bone)]">{value}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </section>

          <section className="mx-auto mt-10 grid max-w-7xl gap-6 sm:grid-cols-2 xl:grid-cols-3">
            {filteredDesigns.map((design) => {
              const activeVariant = getActiveVariant(design)
              const hasBothVariants = design.variants.camiseta && design.variants.sudadera
              const mockups = getDesignMockups(design)

              return (
                <article
                  key={design.slug}
                  className="group overflow-hidden rounded-[1.8rem] border border-white/10 bg-white/[0.03] shadow-[0_0_30px_rgba(237,234,229,0.03)]"
                  onMouseEnter={() => {
                    if (hasBothVariants) {
                      setVariantOverrides((current) => ({
                        ...current,
                        [design.slug]: activeVariant.variant === 'camiseta' ? 'sudadera' : 'camiseta',
                      }))
                    }
                  }}
                  onMouseLeave={() => {
                    setVariantOverrides((current) => ({ ...current, [design.slug]: activeType === 'all' ? 'camiseta' : activeType }))
                  }}
                >
                  <div className="relative overflow-hidden">
                    <div className="absolute left-5 top-5 z-10 rounded-full border border-white/12 bg-black/65 px-4 py-2 font-mono text-[10px] uppercase tracking-[0.35em] text-[var(--bone)] backdrop-blur-md">
                      {activeVariant.badge}
                    </div>
                    <AnimatePresence mode="wait">
                      <motion.img
                        key={activeVariant.id}
                        src={activeVariant.image}
                        alt={activeVariant.name}
                        loading="lazy"
                        decoding="async"
                        initial={{ opacity: 0, scale: 1.02 }}
                        animate={{ opacity: 1, scale: 1.08 }}
                        exit={{ opacity: 0, scale: 1.01 }}
                        transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
                        className="h-[30rem] w-full object-cover object-top transition-transform duration-700 group-hover:scale-[1.12]"
                      />
                    </AnimatePresence>
                    <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(0,0,0,0.04),rgba(0,0,0,0.78))]" />
                    {hasBothVariants && (
                      <div className="absolute bottom-5 left-5 right-5 space-y-3">
                        <div className="flex gap-2">
                          {['camiseta', 'sudadera'].map((variant) => (
                            <button
                              key={variant}
                              type="button"
                              onClick={() => setVariantOverrides((current) => ({ ...current, [design.slug]: variant }))}
                              className={`rounded-full border px-3 py-2 font-mono text-[10px] uppercase tracking-[0.28em] backdrop-blur-md transition ${
                                activeVariant.variant === variant
                                  ? 'border-[var(--bone)] bg-[var(--bone)] text-black'
                                  : 'border-white/12 bg-black/55 text-[var(--bone)]'
                              }`}
                            >
                              {variant === 'camiseta' ? 'Camiseta' : 'Sudadera'}
                            </button>
                          ))}
                        </div>

                        <div className="flex gap-2">
                          {['camiseta', 'sudadera'].map((variant) => (
                            <button
                              key={`${variant}-thumb`}
                              type="button"
                              onClick={() => setVariantOverrides((current) => ({ ...current, [design.slug]: variant }))}
                              className={`overflow-hidden rounded-[0.9rem] border transition ${
                                activeVariant.variant === variant ? 'border-[var(--bone)]' : 'border-white/12'
                              }`}
                            >
                              <img
                                src={design.variants[variant]?.image}
                                alt={`${design.title} ${variant}`}
                                loading="lazy"
                                decoding="async"
                                className="h-16 w-16 object-cover object-top"
                              />
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  <div className="space-y-4 p-6">
                    <div className="flex items-end justify-between gap-4">
                      <div>
                        <p className="font-mono text-[10px] uppercase tracking-[0.32em] text-white/42">{design.title}</p>
                        <a href={`/coleccion/${design.slug}`} className="bone-title-soft mt-3 block font-display text-2xl uppercase tracking-[0.08em] text-[var(--bone)] hover:text-white">
                          {activeVariant.name}
                        </a>
                      </div>
                      <span className="font-mono text-sm uppercase tracking-[0.24em] text-[var(--bone)]">{activeVariant.price}</span>
                    </div>
                    <p className="font-mono text-sm leading-7 text-white/66">{activeVariant.note}</p>

                    {mockups.length > 0 && (
                      <div className="space-y-3">
                        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-white/42">Mockups Extra</p>
                        <div className="flex gap-2 overflow-x-auto pb-1">
                          {mockups.map((mockup, index) => (
                            <button
                              key={`${mockup}-${index}`}
                              onClick={() => setMookupLightbox({ src: mockup, relatedSlug: design.slug, relatedTitle: design.title, title: `${design.title} Mockup ${index + 1}` })}
                              className="flex-none overflow-hidden rounded-[0.9rem] border border-white/10"
                            >
                              <img src={mockup} alt={`${design.title} mockup ${index + 1}`} className="h-20 w-20 object-cover object-center transition duration-500 hover:scale-[1.04]" />
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="flex gap-3">
                      <button
                        onClick={() => setCheckoutProduct(activeVariant)}
                        className="inline-flex flex-1 items-center justify-center rounded-full border border-white/15 bg-[var(--bone)] px-6 py-4 font-mono text-[11px] uppercase tracking-[0.35em] text-black"
                      >
                        Checkout
                      </button>
                      <a
                        href={`/coleccion/${design.slug}`}
                        className="inline-flex items-center justify-center rounded-full border border-white/12 px-5 py-4 font-mono text-[11px] uppercase tracking-[0.35em] text-[var(--bone)]"
                      >
                        Detalle
                      </a>
                    </div>
                  </div>
                </article>
              )
            })}
          </section>
        </main>
      )}

      <AnimatePresence>
        {checkoutProduct && <CheckoutModal product={checkoutProduct} onClose={() => setCheckoutProduct(null)} />}
        {mookupLightbox && <MookupLightbox item={mookupLightbox} onClose={() => setMookupLightbox(null)} />}
      </AnimatePresence>
    </>
  )
}

function DesignDetailView({ design, onCheckout }) {
  const [activeVariant, setActiveVariant] = useState(design.variants.camiseta ? 'camiseta' : 'sudadera')
  const [selectedVisual, setSelectedVisual] = useState('principal')
  const [detailLightbox, setDetailLightbox] = useState(null)
  const variant = design.variants[activeVariant] || design.variants.camiseta || design.variants.sudadera
  const mockups = getDesignMockups(design)
  const designIndex = groupedDesigns.findIndex((item) => item.slug === design.slug)
  const previousDesign = designIndex > 0 ? groupedDesigns[designIndex - 1] : groupedDesigns[groupedDesigns.length - 1]
  const nextDesign = designIndex < groupedDesigns.length - 1 ? groupedDesigns[designIndex + 1] : groupedDesigns[0]
  const visualOptions = [{ key: 'principal', src: variant.image, label: 'Principal' }].concat(
    mockups.map((mockup, index) => ({ key: `mockup-${index}`, src: mockup, label: `Mockup ${index + 1}` })),
  )
  const activeVisual = visualOptions.find((option) => option.key === selectedVisual) || visualOptions[0]

  const handleVariantChange = (variantKey) => {
    setActiveVariant(variantKey)
    setSelectedVisual('principal')
  }

  return (
    <main className="relative z-10 px-4 pb-20 pt-32 sm:px-6 lg:px-8">
      <section className="mx-auto max-w-7xl space-y-8">
        <div className="flex flex-wrap gap-3">
          <a href="/coleccion" className="inline-flex rounded-full border border-white/12 px-5 py-3 font-mono text-[10px] uppercase tracking-[0.35em] text-[var(--bone)]">
            Volver A Coleccion
          </a>
          <a href={`/coleccion/${previousDesign.slug}`} className="inline-flex rounded-full border border-white/12 px-5 py-3 font-mono text-[10px] uppercase tracking-[0.35em] text-[var(--bone)]">
            Anterior: {previousDesign.title}
          </a>
          <a href={`/coleccion/${nextDesign.slug}`} className="inline-flex rounded-full border border-white/12 px-5 py-3 font-mono text-[10px] uppercase tracking-[0.35em] text-[var(--bone)]">
            Siguiente: {nextDesign.title}
          </a>
        </div>

        <div className="grid gap-8 lg:grid-cols-[1fr_0.9fr]">
          <div className="overflow-hidden rounded-[2rem] border border-white/10 bg-white/[0.03]">
            <AnimatePresence mode="wait">
              <motion.img
                key={activeVisual.key}
                src={activeVisual.src}
                alt={variant.name}
                initial={{ opacity: 0, scale: 1.02 }}
                animate={{ opacity: 1, scale: 1.04 }}
                exit={{ opacity: 0, scale: 1.01 }}
                transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
                className="h-[38rem] w-full object-cover object-top transition-transform duration-700 hover:scale-[1.1]"
              />
            </AnimatePresence>
          </div>

          <div className="circuit-border rounded-[2rem] px-6 py-8 sm:px-8">
            <div className="mb-6 flex flex-wrap items-center gap-3 font-mono text-[10px] uppercase tracking-[0.3em] text-white/42">
              <a href="/" className="transition hover:text-[var(--bone)]">Inicio</a>
              <span>/</span>
              <a href="/coleccion" className="transition hover:text-[var(--bone)]">Coleccion</a>
              <span>/</span>
              <span className="text-[var(--bone)]">{design.title}</span>
            </div>
            <p className="font-mono text-[10px] uppercase tracking-[0.42em] text-white/45">Detalle Individual</p>
            <h1 className="bone-title mt-4 font-display text-4xl uppercase tracking-[0.1em] text-[var(--bone)] sm:text-5xl">{design.title}</h1>
            <p className="mt-5 font-mono text-sm leading-7 text-white/68">{variant.note}</p>

            <div className="mt-8 flex flex-wrap gap-3">
              {Object.keys(design.variants).map((variantKey) => (
                <button
                  key={variantKey}
                  onClick={() => handleVariantChange(variantKey)}
                  className={`rounded-full border px-5 py-3 font-mono text-[10px] uppercase tracking-[0.35em] ${
                    activeVariant === variantKey ? 'border-[var(--bone)] bg-[var(--bone)] text-black' : 'border-white/12 text-[var(--bone)]'
                  }`}
                >
                  {variantKey === 'camiseta' ? 'Camiseta 39 EUR' : 'Sudadera 69 EUR'}
                </button>
              ))}
            </div>

            <div className="mt-8 grid gap-4 sm:grid-cols-2">
              {Object.keys(design.variants).map((variantKey) => (
                <button
                  key={`${variantKey}-detail-thumb`}
                  onClick={() => handleVariantChange(variantKey)}
                  className={`overflow-hidden rounded-[1.2rem] border ${activeVariant === variantKey ? 'border-[var(--bone)]' : 'border-white/10'}`}
                >
                  <img src={design.variants[variantKey].image} alt={design.variants[variantKey].name} className="h-32 w-full object-cover object-top" />
                </button>
              ))}
            </div>

            {visualOptions.length > 1 && (
              <div className="mt-8 space-y-3">
                <p className="font-mono text-[10px] uppercase tracking-[0.32em] text-white/42">Variante Visual</p>
                <div className="flex flex-wrap gap-2">
                  {visualOptions.map((option) => (
                    <button
                      key={option.key}
                      onClick={() => setSelectedVisual(option.key)}
                      className={`rounded-full border px-4 py-2.5 font-mono text-[10px] uppercase tracking-[0.28em] ${
                        selectedVisual === option.key ? 'border-[var(--bone)] bg-[var(--bone)] text-black' : 'border-white/12 text-[var(--bone)]'
                      }`}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {mockups.length > 0 && (
              <div className="mt-8 space-y-3">
                <p className="font-mono text-[10px] uppercase tracking-[0.32em] text-white/42">Mockups Frontales / Espalda</p>
                <div className="grid gap-3 sm:grid-cols-2">
                  {mockups.map((mockup, index) => (
                    <button
                      key={`${mockup}-${index}`}
                      onClick={() => setDetailLightbox({ src: mockup, title: `${design.title} Mockup ${index + 1}` })}
                      className="overflow-hidden rounded-[1.2rem] border border-white/10 bg-white/[0.03]"
                    >
                      <img src={mockup} alt={`${design.title} mockup ${index + 1}`} className="h-36 w-full object-cover object-center transition duration-500 hover:scale-[1.04]" />
                    </button>
                  ))}
                </div>
              </div>
            )}

            <button
              onClick={() => onCheckout(variant)}
              className="mt-8 inline-flex w-full items-center justify-center rounded-full border border-white/15 bg-[var(--bone)] px-6 py-4 font-mono text-[11px] uppercase tracking-[0.35em] text-black"
            >
              Checkout {variant.price}
            </button>
          </div>
        </div>
      </section>

      <AnimatePresence>
        {detailLightbox && <MookupLightbox item={detailLightbox} onClose={() => setDetailLightbox(null)} />}
      </AnimatePresence>
    </main>
  )
}

function MookupCarousel({ items, onOpen }) {
  const doubled = [...items, ...items]

  return (
    <div className="carousel-shell relative overflow-hidden">
      <div className="carousel-marquee carousel-mookup flex w-max items-center gap-5 px-4">
        {doubled.map((item, index) => (
          <button
            type="button"
            key={`${item.src}-${index}`}
            onClick={() => onOpen(item)}
            className="group relative flex items-center justify-center overflow-hidden rounded-[1.2rem] border border-white/10 bg-black/35"
          >
            <img src={item.src} alt={item.relatedTitle || 'Mookup catalogo'} loading="lazy" decoding="async" className="h-44 w-72 object-contain object-center transition duration-500 group-hover:scale-[1.03]" />
            {item.relatedSlug && (
              <div className="absolute inset-x-3 bottom-3 rounded-full border border-white/12 bg-black/65 px-3 py-2 font-mono text-[10px] uppercase tracking-[0.28em] text-[var(--bone)] backdrop-blur-md">
                {item.relatedTitle}
              </div>
            )}
          </button>
        ))}
      </div>
      <div className="pointer-events-none absolute inset-y-0 left-0 w-12 bg-[linear-gradient(90deg,rgba(0,0,0,0.72),transparent)]" />
      <div className="pointer-events-none absolute inset-y-0 right-0 w-12 bg-[linear-gradient(270deg,rgba(0,0,0,0.72),transparent)]" />
    </div>
  )
}

function MookupLightbox({ item, onClose }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[88] flex items-center justify-center bg-black/92 p-4 backdrop-blur-md"
    >
      <div className="w-full max-w-5xl rounded-[2rem] border border-white/10 bg-black/92 p-5 shadow-[0_0_80px_rgba(0,0,0,0.6)] sm:p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-white/42">Mookup Expandido</p>
            <p className="bone-title-soft mt-3 font-display text-2xl uppercase tracking-[0.08em] text-[var(--bone)]">{item.relatedTitle || item.title || 'Mookup Editorial'}</p>
          </div>
          <button onClick={onClose} className="rounded-full border border-white/12 px-4 py-2 font-mono text-[10px] uppercase tracking-[0.3em] text-white/60">
            Cerrar
          </button>
        </div>

        <img src={item.src} alt={item.relatedTitle || item.title || 'Mookup editorial'} className="mt-6 max-h-[72vh] w-full rounded-[1.5rem] border border-white/10 object-contain" />

        {item.relatedSlug && (
          <a href={`/coleccion/${item.relatedSlug}`} className="mt-6 inline-flex rounded-full border border-white/12 bg-[var(--bone)] px-5 py-4 font-mono text-[11px] uppercase tracking-[0.35em] text-black">
            Ver Diseno Relacionado
          </a>
        )}
      </div>
    </motion.div>
  )
}

export default ApparelCatalogPage
