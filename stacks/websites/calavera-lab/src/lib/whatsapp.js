import { whatsappBaseUrl, whatsappPhone } from '../data/content'

export function createWhatsAppLink(message) {
  return `${whatsappBaseUrl}?phone=${whatsappPhone}&text=${encodeURIComponent(message)}`
}
