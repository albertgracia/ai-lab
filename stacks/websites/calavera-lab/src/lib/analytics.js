import { getLocalConfig } from './local-config'

let activeMeasurementId = ''

function ensureGa4(measurementId) {
  if (typeof window === 'undefined' || !measurementId) return
  if (activeMeasurementId === measurementId && typeof window.gtag === 'function') return

  activeMeasurementId = measurementId
  window.dataLayer = window.dataLayer || []
  window.gtag = window.gtag || function gtag() { window.dataLayer.push(arguments) }

  if (!document.querySelector(`script[data-ga4="${measurementId}"]`)) {
    const script = document.createElement('script')
    script.async = true
    script.src = `https://www.googletagmanager.com/gtag/js?id=${measurementId}`
    script.dataset.ga4 = measurementId
    document.head.appendChild(script)
  }

  window.gtag('js', new Date())
  window.gtag('config', measurementId)
}

export function initAnalytics() {
  if (typeof window === 'undefined') return
  const apply = () => ensureGa4(getLocalConfig().ga4MeasurementId)
  apply()
  window.addEventListener('calavera-local-config-updated', apply)
}

export function trackEvent(name, params = {}) {
  if (typeof window === 'undefined') return

  window.dataLayer = window.dataLayer || []
  window.dataLayer.push({ event: name, ...params })

  if (typeof window.gtag === 'function') {
    window.gtag('event', name, params)
  }
}

export function trackPurchaseIntent(product, source) {
  trackEvent('begin_checkout_intent', {
    source,
    product_name: product.name,
    price: product.price,
    badge: product.badge,
  })
}

export function trackWhatsAppIntent(source, label) {
  trackEvent('whatsapp_click', {
    source,
    label,
  })
}
