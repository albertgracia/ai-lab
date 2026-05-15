export const LOCAL_CONFIG_KEY = 'calaveraLabLocalConfig'

function normalizeStripeLink(value) {
  const trimmed = String(value || '').trim()
  if (!trimmed) return ''
  if (trimmed.includes('STRIPE_LINK_')) return ''

  try {
    const url = new URL(trimmed)
    const allowedHosts = ['buy.stripe.com']
    if (!allowedHosts.includes(url.hostname)) return ''
    return url.toString()
  } catch {
    return ''
  }
}

function normalizeConfig(config = {}) {
  const stripeEntries = Object.entries(config.stripeLinks || {}).map(([key, value]) => [key, normalizeStripeLink(value)])
  return {
    stripeLinks: Object.fromEntries(stripeEntries),
    ga4MeasurementId: String(config.ga4MeasurementId || '').trim(),
  }
}

export function getLocalConfig() {
  if (typeof window === 'undefined') return { stripeLinks: {}, ga4MeasurementId: '' }

  try {
    const parsed = JSON.parse(window.localStorage.getItem(LOCAL_CONFIG_KEY) || '{}')
    return normalizeConfig(parsed)
  } catch {
    return { stripeLinks: {}, ga4MeasurementId: '' }
  }
}

export function saveLocalConfig(config) {
  if (typeof window === 'undefined') return
  const normalized = normalizeConfig(config)
  window.localStorage.setItem(LOCAL_CONFIG_KEY, JSON.stringify(normalized))
  window.dispatchEvent(new CustomEvent('calavera-local-config-updated', { detail: normalized }))
}

export function resetLocalConfig() {
  if (typeof window === 'undefined') return
  window.localStorage.removeItem(LOCAL_CONFIG_KEY)
  window.dispatchEvent(
    new CustomEvent('calavera-local-config-updated', {
      detail: { stripeLinks: {}, ga4MeasurementId: '' },
    }),
  )
}
