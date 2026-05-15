import { motion } from 'framer-motion'

const cursorVariants = {
  default: {
    size: 62,
    offset: 31,
    glow: '0 0 58px rgba(237,234,229,0.26)',
    inner: 'rgba(255,255,255,0.06)',
    border: 'rgba(255,255,255,0.16)',
    image: 54,
    opacity: 0.94,
  },
  interactive: {
    size: 76,
    offset: 38,
    glow: '0 0 78px rgba(237,234,229,0.34)',
    inner: 'rgba(255,255,255,0.09)',
    border: 'rgba(255,255,255,0.24)',
    image: 66,
    opacity: 1,
  },
  product: {
    size: 88,
    offset: 44,
    glow: '0 0 95px rgba(237,234,229,0.42)',
    inner: 'rgba(255,255,255,0.12)',
    border: 'rgba(255,255,255,0.3)',
    image: 76,
    opacity: 1,
  },
}

function CustomCursor({ pointer, sealLogo, mode = 'default' }) {
  const variant = cursorVariants[mode] ?? cursorVariants.default

  return (
    <div className="pointer-events-none fixed inset-0 z-50 hidden lg:block">
      <motion.div
        animate={{
          x: pointer.x - variant.offset,
          y: pointer.y - variant.offset,
          rotate: 360,
          width: variant.size,
          height: variant.size,
        }}
        transition={{
          x: { type: 'spring', stiffness: 500, damping: 40, mass: 0.2 },
          y: { type: 'spring', stiffness: 500, damping: 40, mass: 0.2 },
          width: { type: 'spring', stiffness: 260, damping: 24 },
          height: { type: 'spring', stiffness: 260, damping: 24 },
          rotate: { duration: 18, ease: 'linear', repeat: Infinity },
        }}
        className="relative flex items-center justify-center"
      >
        <motion.div
          animate={{ boxShadow: variant.glow, backgroundColor: variant.inner }}
          className="absolute inset-0 rounded-full blur-[2px]"
        />
        <motion.div
          animate={{ borderColor: variant.border }}
          className="absolute inset-[6px] rounded-full border bg-black/18 backdrop-blur-sm"
        />
        <motion.img
          src={sealLogo}
          alt=""
          aria-hidden="true"
          animate={{ width: variant.image, height: variant.image, opacity: variant.opacity }}
          className="relative z-10 mix-blend-screen drop-shadow-[0_0_24px_rgba(237,234,229,0.26)]"
        />
      </motion.div>
    </div>
  )
}

export default CustomCursor
