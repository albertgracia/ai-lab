function ThankYouPage() {
  return (
    <main className="relative z-10 flex min-h-screen items-center justify-center px-4 py-16 sm:px-6">
      <section className="circuit-border w-full max-w-4xl rounded-[2rem] px-6 py-12 sm:px-10 sm:py-16">
        <p className="font-mono text-[10px] uppercase tracking-[0.42em] text-white/45">Checkout Complete</p>
        <h1 className="bone-title mt-5 font-display text-4xl uppercase tracking-[0.12em] text-[var(--bone)] sm:text-6xl">Gracias Por Entrar Al Ritual</h1>
        <p className="mt-6 max-w-2xl font-mono text-sm leading-7 text-white/68 sm:text-base">
          Tu compra ha sido recibida. CALAVERA LAB procesara tu artefacto y el ritual de entrega comenzara en breve.
        </p>
        <div className="mt-10 grid gap-4 sm:grid-cols-2">
          <a
            href="/"
            className="inline-flex items-center justify-center rounded-full border border-white/12 bg-[var(--bone)] px-6 py-4 font-mono text-[11px] uppercase tracking-[0.35em] text-black"
          >
            Volver A La Landing
          </a>
          <a
            href="#product-vault"
            className="inline-flex items-center justify-center rounded-full border border-white/12 px-6 py-4 font-mono text-[11px] uppercase tracking-[0.35em] text-[var(--bone)]"
          >
            Seguir Explorando
          </a>
        </div>
        <p className="mt-8 font-mono text-[10px] uppercase tracking-[0.3em] text-white/42">
          Configura en Stripe la success URL como `https://tu-dominio.com/gracias`
        </p>
      </section>
    </main>
  )
}

export default ThankYouPage
