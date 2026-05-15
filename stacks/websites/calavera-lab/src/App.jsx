import { useEffect, useRef, useState } from 'react'
import { useScroll, useTransform } from 'framer-motion'
import Lenis from 'lenis'
import CustomCursor from './components/CustomCursor'
import AdminConfigPanel from './components/AdminConfigPanel'
import Footer from './components/Footer'
import ApparelCatalogPage from './components/ApparelCatalogPage'
import HeroSection from './components/HeroSection'
import ManifestoSection from './components/ManifestoSection'
import Navbar from './components/Navbar'
import ProductVault from './components/ProductVault'
import QualitySection from './components/QualitySection'
import ThankYouPage from './components/ThankYouPage'
import UnboxingSection from './components/UnboxingSection'
import { brandAssets, heroStats, manifestoPanels, navLinks, products, qualityPillars } from './data/content'
import { initAnalytics } from './lib/analytics'

const reveal = {
  initial: { opacity: 0, y: 48 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, amount: 0.25 },
  transition: { duration: 0.9, ease: [0.22, 1, 0.36, 1] },
}

function App() {
  const [showNav, setShowNav] = useState(false)
  const [pointer, setPointer] = useState({ x: 0, y: 0 })
  const [cursorMode, setCursorMode] = useState('default')
  const [activePanel, setActivePanel] = useState(0)
  const [pathname, setPathname] = useState('/')
  const [audioEnabled, setAudioEnabled] = useState(false)
  const [audioReady, setAudioReady] = useState(false)
  const [audioBlocked, setAudioBlocked] = useState(false)
  const audioRef = useRef(null)
  const audioFadeRef = useRef(null)
  const { scrollYProgress } = useScroll()
  const heroY = useTransform(scrollYProgress, [0, 1], ['0%', '30%'])
  const auraY = useTransform(scrollYProgress, [0, 1], ['0%', '55%'])
  const footerY = useTransform(scrollYProgress, [0, 1], ['0%', '22%'])

  useEffect(() => {
    setPathname(window.location.pathname)
    initAnalytics()
    const handlePopState = () => setPathname(window.location.pathname)
    const handleInternalNavigation = (event) => {
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
      const anchor = event.target.closest('a[href]')
      if (!anchor) return
      const href = anchor.getAttribute('href')
      const target = anchor.getAttribute('target')
      if (!href || href.startsWith('http') || href.startsWith('mailto:') || href.startsWith('tel:') || target === '_blank') return
      if (href.startsWith('#')) return

      event.preventDefault()
      window.history.pushState({}, '', href)
      setPathname(window.location.pathname)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
    window.addEventListener('popstate', handlePopState)
    window.addEventListener('click', handleInternalNavigation)

    const lenis = new Lenis({
      duration: 1.25,
      smoothWheel: true,
      touchMultiplier: 1.1,
    })

    let rafId = 0

    const raf = (time) => {
      lenis.raf(time)
      rafId = requestAnimationFrame(raf)
    }

    rafId = requestAnimationFrame(raf)

    return () => {
      cancelAnimationFrame(rafId)
      lenis.destroy()
      window.removeEventListener('popstate', handlePopState)
      window.removeEventListener('click', handleInternalNavigation)
    }
  }, [])

  useEffect(() => {
    const audio = audioRef.current
    if (!audio) {
      return undefined
    }

    audio.volume = 0.4

    const storedPreference = window.localStorage.getItem('calaveraLabAudioEnabled')
    const shouldStartEnabled = storedPreference !== 'false'

    const stopFade = () => {
      if (audioFadeRef.current) {
        window.clearInterval(audioFadeRef.current)
        audioFadeRef.current = null
      }
    }

    const fadeInAudio = () => {
      stopFade()
      audio.volume = 0.04
      audioFadeRef.current = window.setInterval(() => {
        const nextVolume = Math.min(0.4, Number((audio.volume + 0.03).toFixed(2)))
        audio.volume = nextVolume
        if (nextVolume >= 0.4) {
          stopFade()
        }
      }, 180)
    }

    const syncState = () => {
      const isPlaying = !audio.paused && !audio.ended
      setAudioEnabled(isPlaying)
      setAudioReady(true)
    }

    const playAudio = async () => {
      try {
        stopFade()
        await audio.play()
        fadeInAudio()
        setAudioBlocked(false)
        syncState()
      } catch {
        setAudioBlocked(true)
        setAudioEnabled(false)
        setAudioReady(true)
      }
    }

    const handleFirstInteraction = () => {
      if (audio.paused) {
        playAudio()
      }
      removeInteractionListeners()
    }

    const addInteractionListeners = () => {
      window.addEventListener('pointerdown', handleFirstInteraction)
      window.addEventListener('keydown', handleFirstInteraction)
      window.addEventListener('touchstart', handleFirstInteraction)
      window.addEventListener('wheel', handleFirstInteraction, { passive: true })
    }

    const removeInteractionListeners = () => {
      window.removeEventListener('pointerdown', handleFirstInteraction)
      window.removeEventListener('keydown', handleFirstInteraction)
      window.removeEventListener('touchstart', handleFirstInteraction)
      window.removeEventListener('wheel', handleFirstInteraction)
    }

    if (shouldStartEnabled) {
      playAudio().then(() => {
        if (audio.paused) {
          addInteractionListeners()
        }
      })
    } else {
      setAudioReady(true)
    }

    audio.addEventListener('play', syncState)
    audio.addEventListener('pause', syncState)

    return () => {
      removeInteractionListeners()
      audio.removeEventListener('play', syncState)
      audio.removeEventListener('pause', syncState)
      stopFade()
    }
  }, [])

  const toggleAudio = async () => {
    const audio = audioRef.current
    if (!audio) {
      return
    }

    if (!audio.paused) {
      audio.pause()
      window.localStorage.setItem('calaveraLabAudioEnabled', 'false')
      setAudioBlocked(false)
      setAudioEnabled(false)
      return
    }

    try {
      await audio.play()
      window.localStorage.setItem('calaveraLabAudioEnabled', 'true')
      setAudioBlocked(false)
      setAudioEnabled(true)
    } catch {
      setAudioBlocked(true)
      setAudioEnabled(false)
    }
  }

  const isThankYouPage = pathname === '/gracias'
  const isCollectionPage = pathname === '/coleccion' || pathname.startsWith('/coleccion/')
  const currentNavLinks = isCollectionPage
    ? [
        { label: 'Inicio', href: '/' },
        { label: 'Artifacts', href: '/#product-vault' },
        { label: 'Coleccion', href: '/coleccion' },
      ]
    : navLinks

  useEffect(() => {
    const handleScroll = () => setShowNav(window.scrollY > 120)
    const handleMove = (event) => setPointer({ x: event.clientX, y: event.clientY })
    const handlePointerOver = (event) => {
      const target = event.target.closest('a,button,[data-cursor="product"]')
      if (!target) {
        setCursorMode('default')
        return
      }

      if (target.closest('[data-cursor="product"]')) {
        setCursorMode('product')
        return
      }

      setCursorMode('interactive')
    }

    const handlePointerLeave = () => setCursorMode('default')

    handleScroll()
    window.addEventListener('scroll', handleScroll)
    window.addEventListener('pointermove', handleMove)
    window.addEventListener('pointerover', handlePointerOver)
    window.addEventListener('pointerout', handlePointerLeave)

    return () => {
      window.removeEventListener('scroll', handleScroll)
      window.removeEventListener('pointermove', handleMove)
      window.removeEventListener('pointerover', handlePointerOver)
      window.removeEventListener('pointerout', handlePointerLeave)
    }
  }, [])

  return (
    <div className="relative min-h-screen overflow-hidden bg-[var(--bg)] text-[var(--bone)] selection:bg-[var(--bone)] selection:text-black">
      <audio ref={audioRef} src="/ambient-track.mp3" loop preload="auto" />
      <div className="grain pointer-events-none fixed inset-0 z-40 opacity-40" />
      <div className="pointer-events-none fixed inset-0 z-0 bg-[radial-gradient(circle_at_top,_rgba(237,234,229,0.08),_transparent_26%),radial-gradient(circle_at_80%_20%,_rgba(237,234,229,0.06),_transparent_18%),linear-gradient(180deg,rgba(255,255,255,0.02),transparent_30%,transparent_70%,rgba(255,255,255,0.03))]" />
      <CustomCursor pointer={pointer} sealLogo={brandAssets.sealLogo} mode={cursorMode} />
      <AdminConfigPanel />
      {!isThankYouPage && <Navbar showNav={showNav || isCollectionPage} logo={brandAssets.logoCalabera} links={currentNavLinks} />}

      {isThankYouPage ? (
        <ThankYouPage />
      ) : isCollectionPage ? (
        <>
          <ApparelCatalogPage pathname={pathname} backgroundImage={brandAssets.heroSkeletonParty} auraY={auraY} />
          <Footer sealLogo={brandAssets.sealLogo} backgroundImage={brandAssets.footerSinPerderRitmo} backgroundY={footerY} />
        </>
      ) : (
        <>
          <main id="top" className="relative z-10">
            <HeroSection
              logo={brandAssets.logoCalabera}
              backgroundImage={brandAssets.heroSkeletonParty}
              heroY={heroY}
              auraY={auraY}
              reveal={reveal}
              stats={heroStats}
            />
            <ManifestoSection reveal={reveal} panels={manifestoPanels} activePanel={activePanel} setActivePanel={setActivePanel} />
            <ProductVault reveal={reveal} products={products} />
            <QualitySection reveal={reveal} qualityLabel={brandAssets.qualityLabel} detailImage={brandAssets.campaignDetail} pillars={qualityPillars} />
            <UnboxingSection reveal={reveal} image={brandAssets.collectorPackAlt} />
          </main>

          <Footer sealLogo={brandAssets.sealLogo} backgroundImage={brandAssets.footerSinPerderRitmo} backgroundY={footerY} />
        </>
      )}

      {audioReady && (
        <button
          type="button"
          onClick={toggleAudio}
          className="sound-toggle fixed bottom-5 right-5 z-50 inline-flex items-center gap-3 rounded-full px-4 py-3 font-mono text-[10px] uppercase tracking-[0.32em] text-[var(--bone)]"
        >
          <span className={`sound-toggle-dot ${audioEnabled ? 'is-active' : ''}`} />
          <span>{audioEnabled ? 'Sound On' : audioBlocked ? 'Enable Sound' : 'Sound Off'}</span>
        </button>
      )}
    </div>
  )
}

export default App
