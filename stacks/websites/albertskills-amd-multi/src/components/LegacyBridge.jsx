import React from "react";
import { motion } from "framer-motion";
import { Cpu, History, Zap, Monitor } from "lucide-react";
import { useLanguage } from "../context/LanguageContext";

const LegacyBridge = () => {
  const { t } = useLanguage();

  return (
    <section id="legacy" className="py-24 relative overflow-hidden bg-slate-950">
      {/* Retro Grid Background */}
      <div className="absolute inset-0 opacity-10 pointer-events-none">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]"></div>
      </div>

      <div className="container mx-auto px-4 relative z-10">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          
          {/* Legacy Side (1982) */}
          <motion.div 
            initial={{ opacity: 0, x: -50 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            className="space-y-8"
          >
            <div className="inline-block p-2 spectrum-border bg-black mb-4">
              <span className="pixel-text text-white text-2xl tracking-[0.2em]">{t('legacy.tag')}</span>
            </div>
            
            <h3 className="text-4xl font-bold text-white pixel-text leading-tight">
              {t('legacy.title')}
            </h3>
            
            <div className="p-6 bg-slate-900/80 border-l-4 border-red-500 font-mono text-sm space-y-4">
              <p className="text-slate-300">
                <span className="text-red-500 mr-2">10</span> PRINT "DNA DE PIONERO"
              </p>
              <p className="text-slate-300 leading-relaxed italic">
                "{t('legacy.quote')}"
              </p>
              <p className="text-slate-300">
                <span className="text-red-500 mr-2">20</span> GOTO 10
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 glass-panel border-slate-800">
                <History className="text-brand-orange mb-2" size={20} />
                <p className="text-white font-bold text-xs font-mono uppercase">BBS & Modems</p>
                <p className="text-slate-500 text-[10px] font-mono">Protocol Handshakes (56k)</p>
              </div>
              <div className="p-4 glass-panel border-slate-800">
                <Monitor className="text-brand-blue mb-2" size={20} />
                <p className="text-white font-bold text-xs font-mono uppercase">ZX Spectrum</p>
                <p className="text-slate-500 text-[10px] font-mono">Origins of Precision</p>
              </div>
            </div>
          </motion.div>

          {/* AI Future Side (2026) */}
          <motion.div 
            initial={{ opacity: 0, x: 50 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            className="relative"
          >
            <div className="absolute -inset-4 bg-brand-orange/20 blur-3xl rounded-full" />
            <div className="relative glass-panel p-8 border-t-2 border-brand-orange space-y-6">
              <div className="flex items-center justify-between">
                <div className="h-2 w-32 bg-slate-800 rounded-full overflow-hidden">
                  <motion.div 
                    initial={{ width: 0 }}
                    whileInView={{ width: "95%" }}
                    transition={{ duration: 2 }}
                    className="h-full bg-brand-orange"
                  />
                </div>
                <span className="text-brand-orange font-mono text-xs">MULTI-STACK // 99.9%</span>
              </div>

              <div className="space-y-4">
                <h4 className="text-2xl font-bold text-white">{t('legacy.modernTitle')}</h4>
                <p className="text-slate-400 text-sm leading-relaxed">
                  {t('legacy.modernDesc')}
                </p>
              </div>

              <div className="grid grid-cols-1 gap-4">
                <div className="p-5 bg-black/40 border border-slate-800 rounded-lg hover:border-brand-orange/50 transition-colors group">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="p-2 bg-brand-orange/10 rounded-sm">
                      <Zap className="text-brand-orange group-hover:animate-pulse" size={18} />
                    </div>
                    <div>
                      <span className="text-white font-mono text-xs uppercase tracking-widest block font-bold">{t('legacy.tuning.dram')}</span>
                      <span className="text-slate-500 text-[10px] uppercase font-mono tracking-tighter">{t('legacy.tuning.dramSub')}</span>
                    </div>
                    <span className="ml-auto text-brand-orange font-mono text-sm font-bold">6200 MT/s</span>
                  </div>
                  <div className="h-1 w-full bg-slate-900 rounded-full overflow-hidden">
                    <div className="h-full bg-brand-orange w-[92%]" />
                  </div>
                </div>

                <div className="p-5 bg-black/40 border border-slate-800 rounded-lg hover:border-brand-red/50 transition-colors group">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="p-2 bg-brand-red/10 rounded-sm">
                      <Monitor className="text-brand-red group-hover:animate-pulse" size={18} />
                    </div>
                    <div>
                      <span className="text-white font-mono text-xs uppercase tracking-widest block font-bold">{t('legacy.tuning.gpu')}</span>
                      <span className="text-slate-500 text-[10px] uppercase font-mono tracking-tighter">{t('legacy.tuning.gpuSub')}</span>
                    </div>
                    <span className="ml-auto text-brand-red font-mono text-sm font-bold">UNLOCKED</span>
                  </div>
                  <div className="h-1 w-full bg-slate-900 rounded-full overflow-hidden">
                    <div className="h-full bg-brand-red w-[100%]" />
                  </div>
                </div>

                <div className="p-5 bg-black/40 border border-slate-800 rounded-lg hover:border-brand-blue/50 transition-colors group">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-brand-blue/10 rounded-sm">
                      <Cpu className="text-brand-blue group-hover:rotate-12 transition-transform" size={18} />
                    </div>
                    <div>
                      <span className="text-white font-mono text-xs uppercase tracking-widest block font-bold">{t('legacy.tuning.loop')}</span>
                      <span className="text-slate-500 text-[10px] uppercase font-mono tracking-tighter">{t('legacy.tuning.loopSub')}</span>
                    </div>
                    <div className="ml-auto flex gap-1">
                      <div className="w-1 h-3 bg-brand-blue/40" />
                      <div className="w-1 h-3 bg-brand-blue/60" />
                      <div className="w-1 h-3 bg-brand-blue" />
                    </div>
                  </div>
                </div>
              </div>
              
              <a href="#ai" className="block text-center w-full py-3 bg-brand-orange text-brand-dark font-bold text-xs tracking-[0.2em] rounded-sm hover:scale-[1.02] transition-transform">
                {t('legacy.button')}
              </a>
            </div>
          </motion.div>

        </div>
      </div>
    </section>
  );
};

export default LegacyBridge;
