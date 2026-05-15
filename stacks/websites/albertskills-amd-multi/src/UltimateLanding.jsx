import React, { useRef } from 'react';
import { motion, useScroll, useTransform, useSpring } from 'framer-motion';
import { 
  Cpu, 
  Zap, 
  Monitor, 
  Shield, 
  Box, 
  Layers, 
  Activity, 
  Globe, 
  Mail, 
  ChevronRight,
  Database,
  Terminal,
  Server
} from 'lucide-react';

/**
 * THE ULTIMATE ENGINEER LANDING PAGE (V. MULTI-STACK)
 * Created for: skills-amd-multi.labrazahost.es
 */

const NeuralMap = () => {
  const { scrollYProgress } = useScroll();
  
  // High-performance pulse speed mapping (speeds up on scroll)
  const pulseDuration = useTransform(scrollYProgress, [0, 1], [4, 0.4]);
  const pulseSpeed = useSpring(pulseDuration, { stiffness: 100, damping: 30 });

  const paths = [
    { id: 'cpu-amd', d: "M 500 500 L 800 500 L 800 300", color: "#FF4700", label: "AMD RYZEN" },
    { id: 'cpu-gigabyte', d: "M 500 500 L 200 500 L 200 700", color: "#FFFFFF", label: "GIGABYTE X870E" },
    { id: 'cpu-ekwb', d: "M 500 500 L 350 350 L 150 350", color: "#00C2FF", label: "EKWB CUSTOM" },
    { id: 'cpu-pwr', d: "M 500 500 L 650 650 L 850 650", color: "#FF0000", label: "POWERCOLOR DEVIL" },
  ];

  return (
    <div className="fixed inset-0 z-0 bg-slate-1000 overflow-hidden pointer-events-none">
      <svg className="absolute w-full h-full opacity-30 select-none" viewBox="0 0 1000 1000">
        <defs>
          <filter id="circuit-glow">
            <feGaussianBlur stdDeviation="3" result="blur"/>
            <feComposite in="SourceGraphic" in2="blur" operator="over"/>
          </filter>
        </defs>

        {/* Static PCB Traces */}
        {paths.map(p => (
          <path key={`static-${p.id}`} d={p.d} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="1.5" />
        ))}

        {/* Active Energy Pulses */}
        {paths.map(p => (
          <motion.path
            key={`pulse-${p.id}`}
            d={p.d}
            fill="none"
            stroke={p.color}
            strokeWidth="3"
            filter="url(#circuit-glow)"
            initial={{ pathLength: 0, opacity: 0 }}
            animate={{ 
              pathLength: [0, 1], 
              opacity: [0, 1, 0],
            }}
            transition={{ 
              duration: 3, // Base animation is handled by speed transform logic in a real-time reactive way if possible
              repeat: Infinity, 
              ease: "linear",
              delay: Math.random() * 2
            }}
            style={{ 
              // Note: Framer Motion transition duration can't be directly driven by a motion value easily in one animate block,
              // but we simulate speed increase by mapping scroll to the visual intensity or manual duration logic.
            }}
          />
        ))}

        {/* Central Neural Hub (CPU) */}
        <motion.g
          animate={{ scale: [1, 1.05, 1] }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
        >
          <rect x="460" y="460" width="80" height="80" rx="4" className="fill-slate-900 stroke-brand-orange" strokeWidth="2" />
          <text x="500" y="505" textAnchor="middle" className="fill-white font-mono text-[10px] font-bold">CORE_0</text>
        </motion.g>
      </svg>
      
      {/* VIGUETTE & DEPTH */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_transparent_0%,_rgba(2,6,23,0.9)_100%)]" />
    </div>
  );
};

const UltimateLanding = () => {
  const { scrollYProgress } = useScroll();

  return (
    <div className="bg-slate-950 text-slate-300 font-sans selection:bg-orange-500 selection:text-white overflow-x-hidden">
      <NeuralMap />

      {/* FIXED NAV HUD */}
      <nav className="fixed top-0 left-0 right-0 z-50 p-6 md:p-10 pointer-events-none">
        <div className="container mx-auto flex justify-between items-center bg-slate-900/40 backdrop-blur-2xl border border-white/5 p-4 rounded-xl pointer-events-auto">
          <div className="flex items-center gap-4">
            <img src="/logo-multi.png" alt="Systems Architect Logo" className="h-16 w-auto hover:rotate-12 transition-transform duration-500 cursor-pointer" />
            <span className="font-mono text-xs tracking-[0.3em] font-bold hidden md:block">ULTIMATE_ENGINEER_V3</span>
          </div>
          <div className="flex gap-8 font-mono text-[10px] uppercase tracking-widest text-slate-500">
            <a href="#hero" className="hover:text-orange-500 transition-colors">Evolution</a>
            <a href="#specs" className="hover:text-orange-500 transition-colors">Hardware</a>
            <a href="#mesh" className="hover:text-orange-500 transition-colors">Infrastructure</a>
          </div>
        </div>
      </nav>

      <main className="relative z-10">
        
        {/* HERO SECTION */}
        <section id="hero" className="min-h-screen flex items-center justify-center pt-32 pb-20 px-6">
          <div className="container max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-20 items-center">
            
            <motion.div 
              initial={{ opacity: 0, x: -50 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 1 }}
              className="space-y-10"
            >
              <div className="inline-flex items-center gap-3 px-4 py-2 bg-orange-500/10 border border-orange-500/20 rounded-full text-orange-400 font-mono text-[10px] font-bold tracking-[0.2em] uppercase">
                <Shield size={14} /> Systems Architect // Evolved 1968-2026
              </div>
              
              <h1 className="text-5xl md:text-8xl font-black text-white tracking-tighter leading-none italic">
                BEYOND <br />
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-orange-500 via-red-500 to-emerald-400">
                  OPTIMIZATION.
                </span>
              </h1>

              <div className="relative p-8 bg-white/5 backdrop-blur-3xl border border-white/10 rounded-2xl shadow-2xl group overflow-hidden">
                {/* Spectrum Flicker Text */}
                <motion.p 
                  animate={{ opacity: [1, 0.8, 1, 0.95, 1, 0.7, 1] }}
                  transition={{ duration: 0.15, repeat: Infinity }}
                  className="text-emerald-400 font-mono text-sm mb-6 flex items-center gap-2"
                >
                  <Terminal size={14} /> 10 PRINT "SINCLAIR ZX SPECTRUM 16K READY"
                </motion.p>
                
                <p className="text-xl md:text-2xl text-slate-100 leading-relaxed font-light italic">
                  "Mi viaje tecnológico comenzó en 1968... aprendí la lección más valiosa de un ingeniero: <span className="text-orange-500 font-bold">cada byte cuenta.</span>"
                </p>

                <div className="absolute top-0 right-0 p-4 opacity-10">
                  <Cpu size={120} />
                </div>
              </div>

              <div className="flex flex-wrap gap-6 pt-6 font-mono text-xs uppercase tracking-[0.2em] font-bold">
                <div className="flex items-center gap-2 text-orange-500">
                  <Activity size={16} /> 6200 MT/S STABLE
                </div>
                <div className="flex items-center gap-2 text-emerald-400">
                  <Box size={16} /> 25+ DOCKER SERVICES
                </div>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 1, delay: 0.2 }}
              className="relative"
            >
              {/* HAVN Case Border Glassmorphism */}
              <div className="relative aspect-[4/5] bg-slate-900 rounded-3xl overflow-hidden border-2 border-white/10 shadow-[0_0_100px_rgba(255,102,0,0.15)] group">
                <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-transparent to-transparent z-10" />
                
                {/* Profile/Motherboard Photo Placeholder */}
                <div className="absolute inset-0 bg-[url('/futuristic_motherboard.png')] bg-cover bg-center transition-transform duration-1000 group-hover:scale-110" />
                
                {/* Technical Overlay */}
                <div className="absolute bottom-10 left-10 z-20 space-y-2">
                  <div className="flex gap-2">
                    <span className="px-2 py-1 bg-white/10 text-[8px] text-white rounded-sm font-bold">HAVN_HS_420</span>
                    <span className="px-2 py-1 bg-orange-500/20 text-[8px] text-orange-400 rounded-sm font-bold italic">9070XT_MOD</span>
                  </div>
                  <h3 className="text-white font-mono text-xs tracking-widest font-bold">LIQUID_COOLED_INFRASTRUCTURE</h3>
                </div>

                {/* Glass Reflection */}
                <div className="absolute inset-0 bg-gradient-to-tr from-white/5 via-transparent to-white/10 pointer-events-none" />
              </div>
              
              {/* Decorative elements */}
              <div className="absolute -top-10 -right-10 h-32 w-32 bg-orange-500/20 blur-3xl rounded-full" />
              <div className="absolute -bottom-20 -left-20 h-64 w-64 bg-emerald-500/10 blur-3xl rounded-full" />
            </motion.div>

          </div>
        </section>

        {/* HARDWARE SPECS: THE COMPETITION FILE */}
        <section id="specs" className="py-40 bg-slate-900/30 backdrop-blur-md">
          <div className="container max-w-7xl mx-auto px-6">
            <div className="flex items-end justify-between mb-20">
              <div className="space-y-4">
                <span className="text-orange-500 font-mono text-xs font-bold tracking-[0.4em] uppercase">// PHYSICAL_LAYER</span>
                <h2 className="text-4xl md:text-6xl font-black text-white italic">THE IRON & THE FLUID.</h2>
              </div>
              <div className="hidden lg:block h-[1px] flex-1 mx-20 bg-white/10" />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
              {[
                { title: "RYZEN 7 7800X3D", sub: "PBO2 Optimized", icon: Cpu, val: "X870E AORUS ICE", color: "orange" },
                { title: "64GB PREDATOR VESTA II", sub: "Manual Latency", icon: Activity, val: "6200 MT/s CL30", color: "emerald" },
                { title: "POWERCOLOR 9070XT", sub: "BIOS Mod Unlock", icon: Zap, val: "16GB VRAM @ 90% PT", color: "red" },
                { title: "EKWB CUSTOM LOOP", sub: "Kinetic FLT 360", icon: Layers, val: "Thermal Stable 42C", color: "blue" },
                { title: "LIAN LI UNI FAN", sub: "11x AL V2 Hub", icon: Box, val: "Push-Pull config", color: "slate" },
                { title: "LIAN LI EDGE EG1300", sub: "80+ Platinum", icon: Shield, val: "1.3KW Clean Power", color: "indigo" },
              ].map((spec, i) => (
                <motion.div 
                  key={i}
                  whileHover={{ y: -10 }}
                  className="p-8 bg-white/5 border border-white/10 rounded-xl space-y-6 hover:border-orange-500/50 transition-colors relative group"
                >
                  <div className={`h-12 w-12 rounded-lg bg-${spec.color}-500/10 flex items-center justify-center text-${spec.color}-400 group-hover:bg-orange-500/20 group-hover:text-orange-400 transition-colors`}>
                    <spec.icon size={24} />
                  </div>
                  <div>
                    <h4 className="text-white font-black text-lg font-mono">{spec.title}</h4>
                    <p className="text-slate-500 text-xs font-mono tracking-widest uppercase">{spec.sub}</p>
                  </div>
                  <div className="pt-4 border-t border-white/5">
                    <span className="text-white font-mono text-sm font-bold italic">{spec.val}</span>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* LIVE INFRASTRUCTURE MESH */}
        <section id="mesh" className="py-40 relative overflow-hidden">
          <div className="container max-w-7xl mx-auto px-6 relative z-10">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-20 items-center">
              
              <div className="lg:col-span-4 space-y-10">
                <span className="text-emerald-500 font-mono text-xs font-bold tracking-[0.4em] uppercase">// LOGIC_LAYER</span>
                <h2 className="text-4xl md:text-6xl font-black text-white leading-tight italic">LIVE MESH INFRA.</h2>
                <p className="text-slate-400 font-mono leading-relaxed">
                  Orquestando un cluster de 25+ servicios sobre WSL2/Docker. Monitoreo en tiempo real, seguridad avanzada y flujos de IA local sin dependencia de la nube.
                </p>
                
                <div className="space-y-4">
                  {['PROMETHEUS & GRAFANA', 'n8n AUTOMATION', 'COMFYUI GENAI', 'TAILSCALE MESH'].map((service, i) => (
                    <div key={i} className="flex items-center gap-4 text-[10px] font-mono font-bold tracking-widest text-slate-500 group cursor-default">
                      <div className="h-1 w-1 rounded-full bg-emerald-500 animate-ping" />
                      {service}
                    </div>
                  ))}
                </div>

                <a 
                  href="https://skills-amd-multi.labrazahost.es" 
                  className="inline-flex items-center gap-4 px-10 py-5 bg-gradient-to-r from-orange-600 to-red-600 text-white font-black italic rounded-sm hover:scale-105 transition-transform group"
                >
                  ACCESS_NODE <ChevronRight className="group-hover:translate-x-2 transition-transform" />
                </a>
              </div>

              <div className="lg:col-span-8">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                  {/* Decorative visual nodes */}
                  {[
                    { label: "DNS", icon: Globe, status: "UP" },
                    { label: "DB", icon: Database, status: "OP" },
                    { label: "AI", icon: Cpu, status: "RUN" },
                    { label: "FW", icon: Shield, status: "SEC" },
                    { label: "NET", icon: Activity, status: "1GB" },
                    { label: "OS", icon: Monitor, status: "W11" },
                    { label: "SRV", icon: Server, status: "DOCK" },
                    { label: "API", icon: Zap, status: "REST" },
                  ].map((node, i) => (
                    <motion.div 
                      key={i}
                      initial={{ opacity: 0 }}
                      whileInView={{ opacity: 1 }}
                      transition={{ delay: i * 0.1 }}
                      className="aspect-square bg-slate-900 border border-white/5 rounded-xl flex flex-col items-center justify-center space-y-4 group hover:border-emerald-500/50 transition-colors"
                    >
                      <node.icon className="text-slate-700 group-hover:text-emerald-400 transition-colors" size={32} />
                      <div className="text-center font-mono">
                        <div className="text-[10px] text-white font-bold">{node.label}</div>
                        <div className="text-[8px] text-emerald-500 animate-pulse">{node.status}</div>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </div>

            </div>
          </div>
        </section>

        {/* FOOTER */}
        <footer className="py-20 border-t border-white/10 px-6">
          <div className="container max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-10">
            <div className="font-mono text-[10px] text-slate-500 tracking-widest uppercase">
              © 2026 Albert Gràcia Quintana // Built with Sovereign AI
            </div>
            <div className="flex gap-10">
              <Mail className="text-slate-600 hover:text-orange-500 cursor-pointer transition-colors" size={20} />
              <Globe className="text-slate-600 hover:text-orange-500 cursor-pointer transition-colors" size={20} />
            </div>
            <div className="font-mono text-[10px] text-slate-800 tracking-[1em] uppercase">
              [ End of Line ]
            </div>
          </div>
        </footer>

      </main>
    </div>
  );
};

export default UltimateLanding;
