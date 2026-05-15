import { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { products } from '../data/content'
import { apparelConfigProducts } from '../data/apparelCatalog'
import { getLocalConfig, resetLocalConfig, saveLocalConfig } from '../lib/local-config'

const configurableProducts = [...products, ...apparelConfigProducts]

function AdminConfigPanel() {
  const [isLocal, setIsLocal] = useState(false)
  const [isOpen, setIsOpen] = useState(false)
  const [links, setLinks] = useState({})
  const [ga4MeasurementId, setGa4MeasurementId] = useState('')
  const [bulkInput, setBulkInput] = useState('')
  const [copied, setCopied] = useState(false)
  const [bulkStatus, setBulkStatus] = useState('')

  useEffect(() => {
    if (typeof window === 'undefined') return
    const hostname = window.location.hostname
    const localHosts = ['localhost', '127.0.0.1']
    const isPrivateIp = /^10\.|^192\.168\.|^172\.(1[6-9]|2\d|3[0-1])\./.test(hostname)
    const forceAdmin = new URLSearchParams(window.location.search).get('admin') === '1'
    const localMode = localHosts.includes(hostname) || isPrivateIp || forceAdmin
    setIsLocal(localMode)
    if (!localMode) return

    try {
      const config = getLocalConfig()
      setLinks(config.stripeLinks)
      setGa4MeasurementId(config.ga4MeasurementId)
    } catch {
      setLinks({})
      setGa4MeasurementId('')
    }
  }, [])

  const exportPayload = useMemo(
    () =>
      JSON.stringify(
        {
          ga4MeasurementId,
          stripeLinks: configurableProducts.reduce((acc, product) => {
            acc[product.id] = links[product.id] || ''
            return acc
          }, {}),
        },
        null,
        2,
      ),
    [ga4MeasurementId, links],
  )

  if (!isLocal) return null

  const saveLinks = () => {
    saveLocalConfig({ stripeLinks: links, ga4MeasurementId })
    setBulkStatus('Configuracion guardada.')
  }

  const handleReset = () => {
    resetLocalConfig()
    setLinks({})
    setGa4MeasurementId('')
    setBulkInput('')
    setBulkStatus('Configuracion reiniciada.')
  }

  const copyConfig = async () => {
    try {
      await navigator.clipboard.writeText(exportPayload)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1800)
    } catch {
      setCopied(false)
    }
  }

  const importBulkConfig = () => {
    try {
      const parsed = JSON.parse(bulkInput)
      const nextLinks = parsed.stripeLinks || parsed
      setLinks((current) => ({ ...current, ...nextLinks }))
      if (parsed.ga4MeasurementId) {
        setGa4MeasurementId(parsed.ga4MeasurementId)
      }
      setBulkStatus('Importacion aplicada. Pulsa Guardar para activarla.')
    } catch {
      setBulkStatus('El bloque pegado no es un JSON valido.')
    }
  }

  return (
    <>
      <button
        onClick={() => setIsOpen((value) => !value)}
        className="fixed bottom-4 left-4 z-[70] rounded-full border border-white/12 bg-black/75 px-4 py-3 font-mono text-[10px] uppercase tracking-[0.35em] text-[var(--bone)] backdrop-blur-xl"
      >
        Config Local
      </button>

      {isOpen && (
        <motion.aside
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="fixed inset-x-4 bottom-20 z-[70] max-h-[78vh] overflow-auto rounded-[1.75rem] border border-white/12 bg-black/90 p-5 shadow-[0_0_60px_rgba(0,0,0,0.6)] backdrop-blur-2xl sm:left-4 sm:right-auto sm:w-[34rem]"
        >
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.4em] text-white/45">Admin Config</p>
              <h3 className="mt-3 font-display text-2xl uppercase tracking-[0.08em] text-[var(--bone)]">Stripe Links Locales</h3>
              <p className="mt-3 font-mono text-xs leading-6 text-white/58">
                Pega aquí tus Payment Links de Stripe y tu ID de GA4. Se guardan en este navegador y sustituyen el fallback a WhatsApp sin tocar código.
              </p>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="rounded-full border border-white/12 px-3 py-2 font-mono text-[10px] uppercase tracking-[0.3em] text-white/60"
            >
              Cerrar
            </button>
          </div>

          <div className="mt-6 rounded-[1.25rem] border border-white/10 bg-white/[0.03] p-4">
            <p className="font-display text-sm uppercase tracking-[0.08em] text-[var(--bone)]">GA4 Measurement ID</p>
            <input
              type="text"
              value={ga4MeasurementId}
              onChange={(event) => setGa4MeasurementId(event.target.value)}
              placeholder="G-XXXXXXXXXX"
              className="mt-4 w-full rounded-xl border border-white/10 bg-black/50 px-4 py-3 font-mono text-xs text-[var(--bone)] outline-none placeholder:text-white/24"
            />
          </div>

          <div className="mt-4 rounded-[1.25rem] border border-white/10 bg-white/[0.03] p-4">
            <p className="font-display text-sm uppercase tracking-[0.08em] text-[var(--bone)]">Importacion Masiva</p>
            <p className="mt-2 font-mono text-xs leading-6 text-white/54">Pega un JSON con `ga4MeasurementId` y/o `stripeLinks`.</p>
            <p className="mt-2 font-mono text-[10px] uppercase tracking-[0.24em] text-white/34">Solo se aceptan enlaces reales de `https://buy.stripe.com/...`</p>
            <textarea
              value={bulkInput}
              onChange={(event) => setBulkInput(event.target.value)}
              placeholder={exportPayload}
              className="mt-4 min-h-36 w-full rounded-xl border border-white/10 bg-black/50 px-4 py-3 font-mono text-xs text-[var(--bone)] outline-none placeholder:text-white/20"
            />
            <button
              onClick={importBulkConfig}
              className="mt-4 rounded-full border border-white/12 px-5 py-3 font-mono text-[10px] uppercase tracking-[0.35em] text-[var(--bone)]"
            >
              Importar JSON
            </button>
          </div>

          <div className="mt-6 space-y-4">
            {configurableProducts.map((product) => (
              <div key={product.id} className="rounded-[1.25rem] border border-white/10 bg-white/[0.03] p-4">
                <div className="flex items-end justify-between gap-4">
                  <div>
                    <p className="font-display text-sm uppercase tracking-[0.08em] text-[var(--bone)]">{product.name}</p>
                    <p className="mt-2 font-mono text-[10px] uppercase tracking-[0.28em] text-white/42">{product.price}</p>
                  </div>
                </div>
                <input
                  type="text"
                  value={links[product.id] || ''}
                  onChange={(event) => setLinks((current) => ({ ...current, [product.id]: event.target.value }))}
                  placeholder={product.stripeCheckoutUrl}
                  className="mt-4 w-full rounded-xl border border-white/10 bg-black/50 px-4 py-3 font-mono text-xs text-[var(--bone)] outline-none placeholder:text-white/24"
                />
              </div>
            ))}
          </div>

          <div className="mt-6 flex flex-wrap gap-3">
            <button
              onClick={saveLinks}
              className="rounded-full border border-white/12 bg-[var(--bone)] px-5 py-3 font-mono text-[10px] uppercase tracking-[0.35em] text-black"
            >
              Guardar
            </button>
            <button
              onClick={handleReset}
              className="rounded-full border border-white/12 px-5 py-3 font-mono text-[10px] uppercase tracking-[0.35em] text-[var(--bone)]"
            >
              Reset
            </button>
            <button
              onClick={copyConfig}
              className="rounded-full border border-white/12 px-5 py-3 font-mono text-[10px] uppercase tracking-[0.35em] text-[var(--bone)]"
            >
              {copied ? 'Copiado' : 'Copiar JSON'}
            </button>
          </div>

          {bulkStatus && <p className="mt-4 font-mono text-[10px] uppercase tracking-[0.28em] text-white/46">{bulkStatus}</p>}
        </motion.aside>
      )}
    </>
  )
}

export default AdminConfigPanel
