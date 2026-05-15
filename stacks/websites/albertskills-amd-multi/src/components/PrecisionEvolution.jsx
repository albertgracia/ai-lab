import React from 'react';
import { motion } from 'framer-motion';
import { useLanguage } from '../context/LanguageContext';

const PrecisionEvolution = () => {
  const { t } = useLanguage();

  return (
    <section id="evolution" className="relative w-full py-32 min-h-[80vh] flex items-center justify-center z-10 px-4 md:px-0">
      <div className="container mx-auto px-4 lg:px-20 max-w-6xl">
        <motion.div 
          initial={{ opacity: 0, y: 50 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.8 }}
          className="relative bg-slate-950/40 backdrop-blur-[40px] border border-white/10 p-8 md:p-20 rounded-3xl shadow-[0_0_80px_rgba(0,0,0,0.6)] group overflow-hidden"
        >
          {/* HAVN Case inspired "Glass Reflection" effect */}
          <div className="absolute inset-0 bg-gradient-to-br from-white/5 via-transparent to-transparent pointer-events-none" />
          <div className="absolute -top-[50%] -left-[50%] w-[200%] h-[200%] bg-[radial-gradient(circle_at_center,_rgba(255,255,255,0.03)_0%,_transparent_50%)] pointer-events-none group-hover:animate-pulse" />
          
          {/* Premium Border Highlight */}
          <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-green-500/40 to-brand-orange/40" />
          
          <div className="relative z-10 space-y-10">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
              <div className="inline-block px-4 py-1.5 bg-green-500/10 border border-green-500/20 rounded-full">
                <span className="text-green-400 font-mono text-[10px] uppercase tracking-[0.3em] font-bold">
                  {t('evolution.tag')}
                </span>
              </div>
              <div className="flex gap-2">
                <div className="w-12 h-1 bg-green-500/40 rounded-full" />
                <div className="w-8 h-1 bg-brand-orange/40 rounded-full" />
                <div className="w-4 h-1 bg-white/20 rounded-full" />
              </div>
            </div>
            
            <h2 className="text-4xl md:text-7xl font-bold text-white tracking-tighter leading-tight italic">
              {t('evolution.title')} <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-green-400 via-emerald-400 to-brand-orange">
                {t('evolution.subtitle')}
              </span>
            </h2>
            
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 text-slate-300 font-mono leading-relaxed text-sm md:text-lg">
              <div className="lg:col-span-12 space-y-8">
                <p className="border-l-2 border-green-500/30 pl-6 py-2 bg-green-500/5 rounded-r-lg">
                  {t('evolution.p1')}
                </p>
                
                <p className="border-l-2 border-brand-orange/30 pl-6 py-2 bg-brand-orange/5 rounded-r-lg">
                  {t('evolution.p2')}
                </p>
                
                <p className="border-l-2 border-white/30 pl-6 py-2 bg-white/5 rounded-r-lg font-bold text-white">
                  {t('evolution.p3')}
                </p>
              </div>
            </div>

            <div className="pt-8 flex items-center gap-4 text-[10px] font-mono text-slate-500 uppercase tracking-widest">
              <span className="animate-pulse">●</span> SYSTEM_READY: 6200_MT/S_STABLE
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
};

export default PrecisionEvolution;
