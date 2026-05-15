import express from 'express'
import path from 'path'
import fs from 'fs/promises'
import Stripe from 'stripe'
import { fileURLToPath } from 'url'
import { productCatalog } from './server/product-catalog.js'
import { getApparelProduct } from './server/apparel-catalog.js'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const distDir = path.join(__dirname, 'dist')
const carouselDir = path.join(__dirname, 'public', 'artifacts-carousel')
const app = express()
const stripeSecretKey = process.env.STRIPE_SECRET_KEY || ''
const stripePublishableKey = process.env.STRIPE_PUBLISHABLE_KEY || ''
const stripe = stripeSecretKey ? new Stripe(stripeSecretKey) : null
const allowedCountries = (process.env.STRIPE_ALLOWED_COUNTRIES || 'ES')
  .split(',')
  .map((value) => value.trim().toUpperCase())
  .filter(Boolean)

app.use(express.json())
app.use((_req, res, next) => {
  res.setHeader('X-Content-Type-Options', 'nosniff')
  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin')
  res.setHeader('X-Frame-Options', 'SAMEORIGIN')
  next()
})
app.use('/artifacts-carousel', express.static(carouselDir))
app.use(express.static(distDir))

app.get('/api/config', (_req, res) => {
  res.json({
    stripePublishableKey,
    allowedCountries,
  })
})

app.get('/api/artifacts-carousel', async (_req, res) => {
  try {
    const entries = await fs.readdir(carouselDir, { withFileTypes: true })
    const images = entries
      .filter((entry) => entry.isFile() && /\.(png|jpg|jpeg|webp)$/i.test(entry.name))
      .map((entry) => `/artifacts-carousel/${entry.name}`)
      .sort((a, b) => a.localeCompare(b))

    res.json({ images })
  } catch {
    res.json({ images: [] })
  }
})

app.post('/api/create-checkout-session', async (req, res) => {
  if (!stripe) {
    res.status(500).json({ error: 'Stripe no esta configurado en el servidor.' })
    return
  }

  const { productId, customer = {}, origin } = req.body || {}
  const product = productCatalog[productId] || getApparelProduct(productId)

  if (!product) {
    res.status(400).json({ error: 'Producto no valido.' })
    return
  }

  const requiredFields = ['name', 'surname', 'size', 'shippingAddress', 'phone']
  const missingField = requiredFields.find((field) => !String(customer[field] || '').trim())
  if (missingField) {
    res.status(400).json({ error: 'Faltan datos obligatorios del comprador.' })
    return
  }

  const baseUrl = origin || req.get('origin') || process.env.PUBLIC_BASE_URL || 'http://localhost:91'
  const metadata = {
    product_id: productId,
    product_name: product.name,
    customer_name: String(customer.name).trim(),
    customer_surname: String(customer.surname).trim(),
    size: String(customer.size).trim(),
    shipping_address_text: String(customer.shippingAddress).trim(),
    phone: String(customer.phone).trim(),
    observations: String(customer.observations || '').trim().slice(0, 500),
  }

  try {
    const session = await stripe.checkout.sessions.create({
      mode: 'payment',
      billing_address_collection: 'required',
      shipping_address_collection: { allowed_countries: allowedCountries },
      phone_number_collection: { enabled: true },
      customer_creation: 'always',
      success_url: `${baseUrl}/gracias?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${baseUrl}/#product-vault`,
      locale: 'es',
      line_items: [
        {
          quantity: 1,
          price_data: {
            currency: product.currency,
            unit_amount: product.amount,
            product_data: {
              name: product.name,
            },
          },
        },
      ],
      metadata,
      payment_intent_data: {
        metadata,
      },
      custom_fields: [
        {
          key: 'observaciones',
          label: { type: 'custom', custom: 'Observaciones del pedido' },
          type: 'text',
          optional: true,
        },
      ],
    })

    res.json({ url: session.url })
  } catch (error) {
    res.status(500).json({ error: error?.message || 'No se pudo crear la sesion de pago.' })
  }
})

app.get('/{*splat}', (_req, res) => {
  res.sendFile(path.join(distDir, 'index.html'))
})

const port = Number(process.env.PORT || 80)
app.listen(port, () => {
  console.log(`CALAVERA LAB server listening on ${port}`)
})
