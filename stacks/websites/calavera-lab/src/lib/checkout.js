import { createWhatsAppLink } from './whatsapp'
import { getLocalConfig } from './local-config'

function getResolvedStripeUrl(product) {
  const localLinks = getLocalConfig().stripeLinks
  const localLink = product?.id ? localLinks[product.id] : ''
  const candidate = localLink || product?.stripeCheckoutUrl || ''

  if (!candidate || candidate.includes('STRIPE_LINK_')) return ''

  try {
    const url = new URL(candidate)
    if (url.hostname !== 'buy.stripe.com') return ''
    return url.toString()
  } catch {
    return ''
  }
}

export function hasStripeCheckout(product) {
  return Boolean(getResolvedStripeUrl(product))
}

export function getProductPurchaseHref(product) {
  const checkoutUrl = getResolvedStripeUrl(product)

  if (checkoutUrl) {
    return checkoutUrl
  }

  return createWhatsAppLink(product.whatsappText)
}

export function getProductPurchaseLabel(product) {
  return hasStripeCheckout(product) ? 'CHECKOUT' : 'ADQUIRIR'
}
