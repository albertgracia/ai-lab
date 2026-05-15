import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { getProductPurchaseHref } from '../lib/checkout'
import { trackEvent, trackPurchaseIntent } from '../lib/analytics'

const initialForm = {
  name: '',
  surname: '',
  size: '',
  shippingAddress: '',
  phone: '',
  observations: '',
}

const sizeOptions = ['S', 'M', 'L', 'XL', 'XXL']

function CheckoutModal({ product, onClose }) {
  const [form, setForm] = useState(initialForm)
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [checkoutConfig, setCheckoutConfig] = useState({ stripePublishableKey: '', allowedCountries: [] })

  useEffect(() => {
    let active = true
    fetch('/api/config')
      .then((response) => response.json())
      .then((payload) => {
        if (active) setCheckoutConfig(payload)
      })
      .catch(() => {
        if (active) setCheckoutConfig({ stripePublishableKey: '', allowedCountries: [] })
      })

    return () => {
      active = false
    }
  }, [])

  const updateField = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }))
  }

  const submit = async (event) => {
    event.preventDefault()
    setError('')
    setIsSubmitting(true)
    trackPurchaseIntent(product, 'checkout_modal')

    try {
      const response = await fetch('/api/create-checkout-session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          productId: product.id,
          customer: form,
          origin: window.location.origin,
        }),
      })

      const payload = await response.json()
      if (!response.ok || !payload.url) {
        throw new Error(payload.error || 'No se pudo iniciar el pago.')
      }

      trackEvent('checkout_session_created', { product_name: product.name })
      window.location.href = payload.url
    } catch (checkoutError) {
      setError(checkoutError.message)
      const fallback = getProductPurchaseHref(product)
      if (fallback) {
        window.open(fallback, '_blank', 'noopener,noreferrer')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-[85] flex items-center justify-center bg-black/88 p-4 backdrop-blur-md">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 10 }} className="w-full max-w-2xl rounded-[2rem] border border-white/12 bg-black/92 p-6 shadow-[0_0_80px_rgba(0,0,0,0.6)] sm:p-8">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.4em] text-white/45">Checkout Seguro</p>
            <h3 className="bone-title-soft mt-3 font-display text-3xl uppercase tracking-[0.08em] text-[var(--bone)]">{product.name}</h3>
            <p className="mt-3 max-w-xl font-mono text-sm leading-7 text-white/62">Antes de ir a Stripe, completa los datos del pedido. Stripe tambien te pedira direccion de envio y datos de pago en un entorno seguro.</p>
            <p className="mt-3 font-mono text-[10px] uppercase tracking-[0.28em] text-white/42">
              {checkoutConfig.stripePublishableKey
                ? `Stripe activo // Envio permitido: ${(checkoutConfig.allowedCountries || []).join(', ')}`
                : 'Stripe activo mediante configuracion del servidor'}
            </p>
          </div>
          <button onClick={onClose} className="rounded-full border border-white/12 px-4 py-2 font-mono text-[10px] uppercase tracking-[0.3em] text-white/60">Cerrar</button>
        </div>

        <form onSubmit={submit} className="mt-8 grid gap-4 sm:grid-cols-2">
          <Field label="Nombre" value={form.name} onChange={(value) => updateField('name', value)} required />
          <Field label="Apellidos" value={form.surname} onChange={(value) => updateField('surname', value)} required />
          <SelectField label="Talla" value={form.size} onChange={(value) => updateField('size', value)} options={sizeOptions} required />
          <Field label="Telefono de contacto" value={form.phone} onChange={(value) => updateField('phone', value)} required />
          <Field label="Precio" value={product.price} readOnly />
          <div className="sm:col-span-2">
            <Field label="Direccion completa de envio" value={form.shippingAddress} onChange={(value) => updateField('shippingAddress', value)} required textarea />
          </div>
          <div className="sm:col-span-2">
            <Field label="Observaciones" value={form.observations} onChange={(value) => updateField('observations', value)} textarea />
          </div>

          {error && <p className="sm:col-span-2 font-mono text-xs leading-6 text-red-300">{error}</p>}

          <div className="sm:col-span-2 flex flex-wrap gap-3 pt-2">
            <button type="submit" disabled={isSubmitting} className="inline-flex items-center justify-center rounded-full border border-white/15 bg-[var(--bone)] px-6 py-4 font-mono text-[11px] uppercase tracking-[0.35em] text-black disabled:opacity-60">
              {isSubmitting ? 'Cargando...' : 'IR A PAGO SEGURO'}
            </button>
            <button type="button" onClick={onClose} className="inline-flex items-center justify-center rounded-full border border-white/12 px-6 py-4 font-mono text-[11px] uppercase tracking-[0.35em] text-[var(--bone)]">
              Cancelar
            </button>
          </div>
        </form>
      </motion.div>
    </motion.div>
  )
}

function Field({ label, value, onChange, required = false, readOnly = false, textarea = false }) {
  const commonProps = {
    value,
    required,
    readOnly,
    onChange: onChange ? (event) => onChange(event.target.value) : undefined,
    className: 'mt-3 w-full rounded-xl border border-white/10 bg-black/50 px-4 py-3 font-mono text-sm text-[var(--bone)] outline-none placeholder:text-white/24',
  }

  return (
    <label className="block">
      <span className="font-mono text-[10px] uppercase tracking-[0.32em] text-white/46">{label}</span>
      {textarea ? <textarea rows={4} {...commonProps} /> : <input type="text" {...commonProps} />}
    </label>
  )
}

function SelectField({ label, value, onChange, options, required = false }) {
  return (
    <label className="block">
      <span className="font-mono text-[10px] uppercase tracking-[0.32em] text-white/46">{label}</span>
      <select
        value={value}
        required={required}
        onChange={(event) => onChange(event.target.value)}
        className="mt-3 w-full rounded-xl border border-white/10 bg-black/50 px-4 py-3 font-mono text-sm text-[var(--bone)] outline-none"
      >
        <option value="">Selecciona talla</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  )
}

export default CheckoutModal
