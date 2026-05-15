import React from "react";
import { motion } from "framer-motion";
import { Terminal, Cpu, Zap, Database, Layers, ExternalLink, Globe } from "lucide-react";
import { useLanguage } from "../context/LanguageContext";

const Hero = () => {
  const { t } = useLanguage();
  return (
    <section id="hero" className="relative min-h-[90vh] flex items-center justify-center overflow-hidden py-20 px-4">
      {/* Background Effects */}
      <div className="absolute inset-0 z-0">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(14,165,233,0.1),transparent_70%)]" />
        <div className="absolute inset-0 bg-[linear-gradient(rgba(15,23,42,0.8)_1px,transparent_1px),linear-gradient(90deg,rgba(15,23,42,0.8)_1px,transparent_1px)] bg-[size:40px_40px] [mask-image:radial-gradient(ellipse_at_center,black,transparent_80%)]" />
        <div className="scanline" />
      </div>

      <div className="container mx-auto z-10 grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
        {/* Left Content */}
        <motion.div 
          initial={{ opacity: 0, x: -50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8 }}
          className="space-y-8"
        >
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full border border-brand-orange/30 bg-brand-orange/5 text-brand-orange text-[10px] font-mono tracking-widest uppercase mb-4">
            <span>{t('hero.status')}</span>
          </div>

          <h1 className="text-4xl lg:text-7xl font-bold tracking-tight text-white leading-[1.15] font-sans">
            {t('hero.title1')} <br />
            <span className="text-brand-orange glow-text italic">{t('hero.title2')}</span> <br />
            <span className="text-xl lg:text-3xl text-slate-400 font-mono mt-2 block opacity-80 uppercase tracking-widest">
              {t('hero.subtitle')}
            </span>
          </h1>

          <p className="text-lg text-slate-400 max-w-xl font-sans leading-relaxed">
            {t('hero.description')}
          </p>

          <div className="flex flex-wrap gap-6 pt-6 italic">
            <a href="#contact" className="px-8 py-3 bg-brand-orange text-brand-dark font-bold rounded-sm border-2 border-brand-orange hover:bg-transparent hover:text-brand-orange transition-all duration-300 flex items-center gap-3 tracking-[0.25em] font-mono text-xs shadow-[0_0_20px_rgba(255,102,0,0.2)]">
              <Terminal size={14} />
              {t('hero.handshake')}
            </a>
            <a href="#infra" className="px-8 py-3 border border-brand-blue/30 text-white font-medium hover:bg-brand-blue/5 transition-colors duration-300 flex items-center gap-3 tracking-[0.25em] font-mono text-xs">
              <Globe size={14} className="text-brand-blue" />
              {t('hero.bridge')}
            </a>
          </div>
        </motion.div>

        {/* Right Content - Profile Frame */}
        <motion.div 
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1, delay: 0.2 }}
          className="relative flex justify-center"
        >
          <div className="relative w-80 h-80 lg:w-[450px] lg:h-[450px] xl:w-[550px] xl:h-[550px] 2xl:w-[650px] 2xl:h-[650px]">
            {/* Geometric Frames */}
            <div className="absolute inset-0 border-2 border-brand-orange/20 animate-[spin_20s_linear_infinite] rounded-lg rotate-12" />
            <div className="absolute inset-8 border border-white/10 animate-[spin_15s_linear_infinite_reverse] rounded-sm -rotate-6" />
            
            <div className="absolute inset-12 overflow-hidden glass-panel border-brand-orange/40 shadow-[0_0_50px_rgba(255,102,0,0.1)]">
              <img 
                src="/profile.jpg" 
                alt="Systems Architect" 
                className="w-full h-full object-cover grayscale hover:grayscale-0 transition-all duration-700"
              />
              <div className="absolute bottom-4 left-4 right-4 p-5 bg-black/90 border-l-4 border-brand-orange backdrop-blur-xl shadow-2xl">
                <p className="font-mono text-[10px] text-brand-orange font-bold uppercase tracking-[0.2em]">
                  Multi-Stack Infrastructure Optimized
                </p>
                <div className="flex justify-between items-center mt-2 border-t border-white/5 pt-2">
                  <span className="font-mono text-[10px] text-slate-500 uppercase tracking-tighter italic">Timeline evolution</span>
                  <span className="font-mono text-[10px] text-slate-400 font-bold">1968 [0] {" → "} 2026 [64GB]</span>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
};

export default Hero;
