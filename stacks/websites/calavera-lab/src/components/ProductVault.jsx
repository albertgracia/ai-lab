import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useMemo, useRef, useState } from 'react'
import { getProductPurchaseHref } from '../lib/checkout'
import CheckoutModal from './CheckoutModal'

function ProductVault({ reveal, products }) {
  const [hoveredProduct, setHoveredProduct] = useState(0)
  const [activeMobileProduct, setActiveMobileProduct] = useState(0)
  const [carouselImages, setCarouselImages] = useState([])
  const [lightboxImage, setLightboxImage] = useState('')
  const [checkoutProduct, setCheckoutProduct] = useState(null)
  const productCardRefs = useRef([])
  const artifactRailRef = useRef(null)
  const desktopProduct = useMemo(() => products[hoveredProduct] ?? products[0], [hoveredProduct, products])
  const mobileProduct = useMemo(() => products[activeMobileProduct] ?? products[0], [activeMobileProduct, products])

  useEffect(() => {
    let active = true

    const loadCarousel = async () => {
      try {
        const response = await fetch('/api/artifacts-carousel', { cache: 'no-store' })
        const payload = await response.json()
        const unique = Array.isArray(payload.images) ? payload.images : []
        if (active) {
          setCarouselImages(unique)
        }
      } catch {
        if (active) {
          setCarouselImages([])
        }
      }
    }

    loadCarousel()
    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    const activeCard = productCardRefs.current[hoveredProduct]
    const rail = artifactRailRef.current
    if (!activeCard) {
      return
    }

    if (rail) {
      const cardTop = activeCard.offsetTop
      const cardBottom = cardTop + activeCard.offsetHeight
      const viewTop = rail.scrollTop
      const viewBottom = viewTop + rail.clientHeight
      const isFullyVisible = cardTop >= viewTop && cardBottom <= viewBottom

      if (isFullyVisible) {
        return
      }
    }

    activeCard.scrollIntoView({
      block: 'nearest',
      behavior: 'auto',
      inline: 'nearest',
    })
  }, [hoveredProduct])

  useEffect(() => {
    const rail = artifactRailRef.current
    if (!rail) {
      return undefined
    }

    const handleWheel = (event) => {
      if (window.innerWidth < 1024) {
        return
      }

      const { deltaY } = event
      if (deltaY === 0) {
        return
      }

      const maxScrollTop = rail.scrollHeight - rail.clientHeight
      const nextScrollTop = rail.scrollTop + deltaY
      const canScrollDown = deltaY > 0 && rail.scrollTop < maxScrollTop
      const canScrollUp = deltaY < 0 && rail.scrollTop > 0

      if (!canScrollDown && !canScrollUp) {
        return
      }

      event.preventDefault()
      rail.scrollTop = Math.max(0, Math.min(maxScrollTop, nextScrollTop))
    }

    rail.addEventListener('wheel', handleWheel, { passive: false })
    return () => {
      rail.removeEventListener('wheel', handleWheel)
    }
  }, [])

  return (
    <motion.section id="product-vault" {...reveal} className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8">
      <div className="mb-10 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.4em] text-white/45">Product Vault</p>
          <h2 className="bone-title mt-4 font-display text-3xl uppercase tracking-[0.12em] sm:text-5xl">The Artifacts</h2>
        </div>
        <p className="max-w-xl font-mono text-sm leading-7 text-white/68">
          Piezas concebidas como reliquias urbanas: visuales de alta definición, materiales pesados y señales de escasez visibles en cada artefacto.
        </p>
      </div>

      <div className="artifact-desktop-frame hidden gap-6 lg:grid lg:grid-cols-[1.15fr_0.85fr] lg:items-stretch lg:sticky lg:top-28">
        <div className="artifact-preview-panel overflow-hidden rounded-[2rem] border border-white/10 bg-black/70">
          <div className="manifesto-stage relative min-h-[31rem] overflow-hidden bg-black/80">
              <AnimatePresence mode="wait">
                <motion.div
                  key={desktopProduct.name}
                  initial={{ opacity: 0, scale: 1.08, filter: 'blur(8px)' }}
                  animate={{ opacity: 1, scale: 1, filter: 'blur(0px)' }}
                  exit={{ opacity: 0, scale: 1.05, filter: 'blur(10px)' }}
                  transition={{ duration: 0.75, ease: [0.22, 1, 0.36, 1] }}
                  className="absolute inset-0"
                >
                  <img
                    src={desktopProduct.image}
                    alt={desktopProduct.name}
                    loading="lazy"
                    decoding="async"
                    className="h-full w-full object-contain object-top p-6 pb-2"
                  />
                  <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_rgba(255,255,255,0.02),_transparent_34%),linear-gradient(180deg,rgba(0,0,0,0.04),rgba(0,0,0,0.44))]" />
                  <div className="manifesto-flare absolute inset-y-0 left-[-22%] w-[42%] -skew-x-12 bg-[linear-gradient(90deg,transparent,rgba(255,255,255,0.22),transparent)] opacity-0" />
                </motion.div>
              </AnimatePresence>

              <div className="absolute left-6 top-6 z-10 rounded-full border border-white/12 bg-black/60 px-4 py-2 font-mono text-[10px] uppercase tracking-[0.38em] text-[var(--bone)] backdrop-blur-md">
                {desktopProduct.badge}
              </div>
              <div className="absolute inset-x-0 top-0 h-28 bg-[linear-gradient(180deg,rgba(0,0,0,0.7),transparent)]" />
            </div>

            <div className="artifact-preview-copy border-t border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.04),rgba(255,255,255,0.02))] p-8">
              <div className="max-w-2xl space-y-4">
                <p className="font-mono text-[10px] uppercase tracking-[0.42em] text-white/48">UHD Artifact Reveal // Full Product Image</p>
                <div className="flex items-end justify-between gap-6">
                  <h3 className="bone-title font-display text-4xl uppercase tracking-[0.12em] text-[var(--bone)] xl:text-5xl">{desktopProduct.name}</h3>
                  <span className="font-mono text-sm uppercase tracking-[0.24em] text-[var(--bone)]">{desktopProduct.price}</span>
                </div>
                <p className="max-w-xl font-mono text-sm leading-7 text-white/72">{desktopProduct.note}</p>
                <div className="flex flex-wrap items-center gap-4">
                  <a
                    href={getProductPurchaseHref(desktopProduct)}
                    onClick={(event) => {
                      event.preventDefault()
                      setCheckoutProduct(desktopProduct)
                    }}
                    className="inline-flex items-center justify-center rounded-full border border-white/15 bg-[var(--bone)] px-6 py-4 font-mono text-[11px] uppercase tracking-[0.35em] text-black transition duration-500 hover:scale-[1.02]"
                  >
                    CHECKOUT
                  </a>
                  <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-white/46">Pago seguro con Stripe y recogida de datos de envio.</p>
                </div>
              </div>
            </div>

          {carouselImages.length > 0 && (
            <div className="artifact-carousel-panel border-t border-white/10 bg-black/35 py-4">
              <div className="px-5 pb-4">
                <p className="font-mono text-[10px] uppercase tracking-[0.38em] text-white/42">Carrusel De Imagenes En The Artifacts</p>
              </div>
              <CarouselTrack images={carouselImages} onOpen={setLightboxImage} />
            </div>
          )}
        </div>

        <div className="artifact-card-rail-shell relative overflow-hidden rounded-[2rem] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.04),rgba(255,255,255,0.02))]">
          <div className="pointer-events-none absolute inset-x-0 top-0 z-10 h-20 bg-[linear-gradient(180deg,rgba(0,0,0,0.92),rgba(0,0,0,0.4),transparent)]" />
          <div className="pointer-events-none absolute inset-x-0 bottom-0 z-10 h-24 bg-[linear-gradient(0deg,rgba(0,0,0,0.94),rgba(0,0,0,0.45),transparent)]" />
          <div ref={artifactRailRef} className="artifact-card-rail grid gap-4 overflow-y-auto p-4 pr-3">
            {products.map((product, index) => {
              const isActive = hoveredProduct === index
              return (
                <article
                  key={product.name}
                  ref={(node) => {
                    productCardRefs.current[index] = node
                  }}
                  onMouseEnter={() => setHoveredProduct(index)}
                  data-cursor="product"
                  className={`artifact-rail-card group relative overflow-hidden rounded-[1.6rem] border px-5 py-6 transition duration-500 ${
                    isActive
                      ? 'border-[var(--bone)] bg-white/[0.08] shadow-[0_0_36px_rgba(237,234,229,0.06)]'
                      : 'border-white/10 bg-white/[0.03] hover:border-white/25 hover:bg-white/[0.05]'
                  }`}
                >
                  <div className="absolute inset-0 opacity-20 transition duration-500 group-hover:opacity-35">
                    <img src={product.image} alt={product.name} loading="lazy" decoding="async" className="h-full w-full object-cover" />
                  </div>
                  <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(0,0,0,0.92),rgba(0,0,0,0.58))]" />
                  <div className="relative flex h-full min-h-[11rem] flex-col justify-between gap-6">
                    <div className="flex items-center justify-between gap-4">
                      <div className="rounded-full border border-white/12 bg-black/50 px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.38em] text-[var(--bone)]">
                        {product.badge}
                      </div>
                      <span className={`h-2.5 w-2.5 rounded-full transition ${isActive ? 'bg-[var(--bone)] shadow-[0_0_18px_rgba(237,234,229,0.8)]' : 'bg-white/25'}`} />
                    </div>
                    <div className="space-y-3">
                      <div className="flex items-end justify-between gap-4">
                        <h3 className="bone-title-soft font-display text-2xl uppercase leading-none tracking-[0.1em] text-[var(--bone)]">{product.name}</h3>
                        <span className="font-mono text-xs uppercase tracking-[0.24em] text-white/74">{product.price}</span>
                      </div>
                      <p className="max-w-[22rem] font-mono text-xs leading-6 text-white/66">{product.note}</p>
                    </div>
                  </div>
                </article>
              )
            })}
          </div>
        </div>
      </div>

      <div className="block space-y-5 lg:hidden">
        <div className="rounded-[1.6rem] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.05),rgba(255,255,255,0.02))] px-5 py-5 shadow-[0_0_30px_rgba(237,234,229,0.04)] backdrop-blur-sm">
          <p className="font-mono text-[10px] uppercase tracking-[0.42em] text-white/45">Mobile Artifact Vault</p>
          <p className="bone-title mt-3 font-display text-xl uppercase tracking-[0.1em] text-[var(--bone)]">The Artifacts</p>
          <p className="mt-3 font-mono text-sm leading-7 text-white/62">
            Selecciona un artefacto y explora una vista premium optimizada para móvil, con carga ligera y acceso directo a compra.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-3">
          {products.map((product, index) => (
            <button
              key={product.name}
              onClick={() => setActiveMobileProduct(index)}
              className={`rounded-[1.2rem] border px-4 py-4 text-left transition ${
                activeMobileProduct === index
                  ? 'border-[var(--bone)] bg-white/[0.08] shadow-[0_0_24px_rgba(237,234,229,0.05)]'
                  : 'border-white/10 bg-white/[0.03]'
              }`}
            >
              <span className="bone-title-soft block font-display text-sm uppercase tracking-[0.08em] text-[var(--bone)]">{product.name}</span>
              <span className="mt-2 block font-mono text-[10px] uppercase tracking-[0.28em] text-white/46">{product.price}</span>
            </button>
          ))}
        </div>

        <article data-cursor="product" className="group overflow-hidden rounded-[1.9rem] border border-white/10 bg-white/[0.03] shadow-[0_0_30px_rgba(237,234,229,0.04)]">
          <div className="absolute left-5 top-5 z-10 rounded-full border border-white/12 bg-black/65 px-4 py-2 font-mono text-[10px] uppercase tracking-[0.38em] text-[var(--bone)] backdrop-blur-md">
            {mobileProduct.badge}
          </div>
          <img
            key={mobileProduct.name}
            src={mobileProduct.image}
            alt={mobileProduct.name}
            loading="eager"
            decoding="async"
            className="h-[18rem] w-full object-cover object-top sm:h-[22rem]"
          />
          <div className="border-t border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.04),rgba(255,255,255,0.02))] p-5">
            <div className="rounded-[1.4rem] border border-white/10 bg-black/28 p-5 backdrop-blur-sm">
              <div className="flex items-end justify-between gap-4">
                <div>
                  <h3 className="bone-title-soft font-display text-2xl uppercase tracking-[0.08em] text-[var(--bone)]">{mobileProduct.name}</h3>
                  <p className="mt-3 max-w-[16rem] font-mono text-sm leading-6 text-white/72">{mobileProduct.note}</p>
                </div>
                <span className="font-mono text-sm uppercase tracking-[0.24em] text-[var(--bone)]">{mobileProduct.price}</span>
              </div>
              <a
                href={getProductPurchaseHref(mobileProduct)}
                onClick={(event) => {
                  event.preventDefault()
                  setCheckoutProduct(mobileProduct)
                }}
                className="mt-6 inline-flex w-full items-center justify-center rounded-full border border-white/15 bg-[var(--bone)] px-5 py-4 font-mono text-[11px] uppercase tracking-[0.35em] text-black"
              >
                CHECKOUT
              </a>
              <p className="mt-4 font-mono text-[10px] uppercase tracking-[0.28em] text-white/46">Pago seguro con Stripe y recogida de datos de envio.</p>
            </div>

            {carouselImages.length > 0 && (
              <div className="mt-5 overflow-hidden rounded-[1.4rem] border border-white/10 bg-black/35 py-4">
                <div className="px-4 pb-4">
                  <p className="font-mono text-[10px] uppercase tracking-[0.32em] text-white/42">Carrusel De Imagenes En The Artifacts</p>
                </div>
                <CarouselTrack images={carouselImages} compact onOpen={setLightboxImage} />
              </div>
            )}
          </div>
        </article>
      </div>

      <AnimatePresence>
        {checkoutProduct && <CheckoutModal product={checkoutProduct} onClose={() => setCheckoutProduct(null)} />}
        {lightboxImage && (
          <motion.button
            type="button"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setLightboxImage('')}
            className="fixed inset-0 z-[80] flex items-center justify-center bg-black/92 p-4 backdrop-blur-md"
          >
            <motion.img
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.98 }}
              src={lightboxImage}
              alt="Vista ampliada The Artifacts"
              className="max-h-[90vh] max-w-[92vw] rounded-[1.5rem] border border-white/10 object-contain shadow-[0_0_80px_rgba(0,0,0,0.6)]"
            />
          </motion.button>
        )}
      </AnimatePresence>
    </motion.section>
  )
}

function CarouselTrack({ images, compact = false, onOpen }) {
  const doubledImages = [...images, ...images]

  return (
    <div className="carousel-shell relative overflow-hidden">
      <div className={`carousel-marquee flex w-max gap-4 px-4 ${compact ? 'carousel-compact' : ''}`}>
        {doubledImages.map((image, index) => (
          <button
            type="button"
            key={`${image}-${index}`}
            onClick={() => onOpen(image)}
            className={`overflow-hidden rounded-[1.2rem] border border-white/10 bg-white/[0.03] ${compact ? 'w-36' : 'w-48 xl:w-56'}`}
          >
            <img
              src={image}
              alt="Carrusel The Artifacts"
              loading="lazy"
              decoding="async"
              className={`w-full object-cover ${compact ? 'h-24' : 'h-32 xl:h-36'}`}
            />
          </button>
        ))}
      </div>
      <div className="pointer-events-none absolute inset-y-0 left-0 w-12 bg-[linear-gradient(90deg,rgba(0,0,0,0.72),transparent)]" />
      <div className="pointer-events-none absolute inset-y-0 right-0 w-12 bg-[linear-gradient(270deg,rgba(0,0,0,0.72),transparent)]" />
    </div>
  )
}

export default ProductVault
