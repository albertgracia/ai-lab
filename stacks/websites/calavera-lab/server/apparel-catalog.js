export const apparelTitleMap = {
  amor: 'Amor',
  calavera: 'Calavera',
  colectividad: 'Colectividad',
  contigo: 'Contigo',
  cuandoseagrande: 'Cuando Sea Grande',
  elobjetivo: 'El Objetivo',
  'esqueletos-de-fiesta': 'Esqueletos de Fiesta',
  estasconmigo: 'Estas Conmigo',
  gavetadehistoria: 'Gaveta de Historia',
  herencia: 'Herencia',
  'la-ceremonia': 'La Ceremonia',
  'la-suerte': 'La Suerte',
  lapesca: 'La Pesca',
  llevame: 'Llevame',
  origen: 'Origen',
  ritual: 'Ritual',
  'sin-perder-elritmo': 'Sin Perder El Ritmo',
  tebusco: 'Te Busco',
  virgenes: 'Virgenes',
  virjenes: 'Virgenes',
}

export function canonicalizeApparelSlug(slug) {
  if (slug === 'virjenes') return 'virgenes'
  return slug
}

export function getApparelProduct(productId) {
  const match = /^(.*)-(camiseta|sudadera)$/.exec(productId || '')
  if (!match) return null

  const [, rawSlug, variant] = match
  const slug = canonicalizeApparelSlug(rawSlug)
  const title = apparelTitleMap[slug]
  if (!title) return null

  return {
    name: `${title} ${variant === 'sudadera' ? 'Sudadera' : 'Camiseta'}`,
    amount: variant === 'sudadera' ? 6900 : 3900,
    currency: 'eur',
  }
}
