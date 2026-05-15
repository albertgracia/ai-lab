import React from "react";
import { useLanguage } from "./context/LanguageContext";
import Hero from "./components/Hero";
import LegacyBridge from "./components/LegacyBridge";
import AIShowcase from "./components/AIShowcase";
import InfraMap from "./components/InfraMap";
import LiveStatus from "./components/LiveStatus";
import HardwareGallery from "./components/HardwareGallery";
import LanguageSwitch from "./components/LanguageSwitch";
import CircuitBackground from "./components/CircuitBackground";
import PrecisionEvolution from "./components/PrecisionEvolution";
import { Globe, Activity, Mail, Shield, Languages } from "lucide-react";

function App() {
  const { t, toggleLanguage, currentLangLabel } = useLanguage();

  return (
    <main className="bg-brand-dark min-h-screen text-slate-300 font-sans selection:bg-brand-orange selection:text-brand-dark flex flex-col items-center overflow-x-hidden relative">
      <CircuitBackground />
      
      {/* Content Layer */}
      <div className="relative z-10 w-full flex flex-col items-center">
        {/* Navigation HUD */}
      <nav className="fixed top-0 left-0 right-0 z-50 py-10 px-4 md:px-14 flex justify-center items-center bg-brand-dark/60 backdrop-blur-xl border-b-2 border-brand-orange/10 electric-border">
        <div className="w-full container flex justify-between items-center text-white">
          <div className="flex items-center gap-4 group cursor-pointer shrink-0">
            <img src="/logo-multi.png" alt="Logo" className="h-12 w-auto drop-shadow-[0_0_15px_rgba(255,102,0,0.4)] group-hover:scale-110 transition-transform"></img>
            <span className="font-mono text-sm md:text-base text-white tracking-[0.2em] md:tracking-[0.3em] font-bold group-hover:text-brand-orange transition-colors truncate max-w-[200px] md:max-w-none electric-text">
              SKILLS-AMD-MULTI.LABRAZAHOME.ES
            </span>
          </div>
          <div className="hidden lg:flex items-center gap-10 xl:gap-14 text-sm font-mono tracking-widest text-slate-400 px-6">
            <a href="#hero" className="hover:text-brand-orange transition-colors italic uppercase whitespace-nowrap electric-hover">{t('nav.evolution')}</a>
            <a href="#legacy" className="hover:text-brand-orange transition-colors uppercase whitespace-nowrap electric-hover">{t('nav.legacy')}</a>
            <a href="#ai" className="hover:text-brand-orange transition-colors uppercase whitespace-nowrap electric-hover">{t('nav.ai')}</a>
            <a href="#beast" className="hover:text-brand-orange transition-colors uppercase whitespace-nowrap electric-hover">{t('nav.beast')}</a>
            <a href="#gallery" className="hover:text-brand-orange transition-colors uppercase whitespace-nowrap electric-hover">{t('nav.gallery')}</a>
          </div>
          <div className="flex items-center gap-6 md:gap-10 shrink-0">
            <LanguageSwitch />
            <a href="mailto:albertgraciaquintana@gmail.com" title="Email Contact" className="electric-icon">
              <Mail size={24} className="text-slate-500 hover:text-brand-orange cursor-pointer transition-colors" />
            </a>
            <a href="http://portfolio.labrazahome.es" target="_blank" rel="noopener noreferrer" className="electric-icon">
              <Globe size={24} className="text-slate-500 hover:text-brand-orange cursor-pointer transition-colors" />
            </a>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <div className="w-full flex justify-center mt-32">
        <Hero />
      </div>

      {/* Precision Evolution Narrative */}
      <div className="w-full flex justify-center relative z-20">
        <PrecisionEvolution />
      </div>

      {/* Legacy Bridge: 1982 -> 2026 */}
      <div className="w-full flex justify-center">
        <LegacyBridge />
      </div>

      {/* AI Showcase */}
      <div className="w-full flex justify-center">
        <AIShowcase />
      </div>

      {/* Infrastructure Map */}
      <div className="w-full flex justify-center">
        <InfraMap />
      </div>

      {/* Hardware Gallery */}
      <div className="w-full flex justify-center">
        <HardwareGallery />
      </div>

      {/* Live Status Dashboard */}
      <div className="w-full flex justify-center">
        <LiveStatus />
      </div>

      {/* Enhanced Premium Footer */}
      <footer className="w-full pt-48 pb-32 border-t-2 border-brand-orange/20 bg-slate-950 relative overflow-hidden electric-border">
        {/* Decorative ambient light */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-[2px] bg-gradient-to-r from-transparent via-brand-orange/60 to-transparent electric-text" />
        <div className="absolute -top-32 left-1/2 -translate-x-1/2 w-[900px] h-[300px] bg-brand-orange/10 blur-[150px] rounded-full pointer-events-none" />
        
        <div className="container mx-auto px-10 relative z-10">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-20 lg:gap-12 items-start">
            
            {/* Brand Column */}
            <div className="lg:col-span-5 space-y-12">
              <div className="flex items-center gap-6 group">
                <img src="/logo-multi.png" alt="Logo" className="h-16 w-auto drop-shadow-[0_0_20px_rgba(255,102,0,0.4)] group-hover:scale-110 transition-transform"></img>
                <div>
                  <h4 className="text-white font-bold text-2xl tracking-tight electric-text">Albert Gràcia Quintana</h4>
                  <p className="text-brand-orange font-mono text-xs uppercase tracking-[0.4em] font-bold">Systems Architect // Evolved 1968-2026</p>
                </div>
              </div>
              
              <p className="text-slate-400 text-lg leading-relaxed max-w-xl italic">
                {t('hero.description')}
              </p>
              
              <div className="flex items-center gap-6 pt-6">
                <Shield size={24} className="text-brand-orange/60 electric-icon" />
                <span className="text-xs font-mono text-slate-500 uppercase tracking-widest italic line-through decoration-brand-orange/40">unoptimized_systems_detected</span>
              </div>
            </div>

            {/* Links Column */}
            <div className="lg:col-span-3 space-y-8">
              <h5 className="text-white font-mono text-sm uppercase tracking-[0.4em] font-bold border-b-2 border-white/10 pb-4 electric-text">Quick Access</h5>
              <div className="grid grid-cols-1 gap-6 text-slate-500 font-mono text-xs uppercase tracking-widest">
                <a href="#hero" className="hover:text-brand-orange transition-colors flex items-center gap-3 electric-hover">
                  <span className="h-[1px] w-6 bg-brand-orange/40" /> {t('nav.evolution')}
                </a>
                <a href="#legacy" className="hover:text-brand-orange transition-colors flex items-center gap-3 electric-hover">
                  <span className="h-[1px] w-6 bg-brand-orange/40" /> {t('nav.legacy')}
                </a>
                <a href="#ai" className="hover:text-brand-orange transition-colors flex items-center gap-3 electric-hover">
                  <span className="h-[1px] w-6 bg-brand-orange/40" /> {t('nav.ai')}
                </a>
                <a href="#infra" className="hover:text-brand-orange transition-colors flex items-center gap-3 electric-hover">
                  <span className="h-[1px] w-6 bg-brand-orange/40" /> Infrastructure
                </a>
                <a href="#beast" className="hover:text-brand-orange transition-colors flex items-center gap-3 electric-hover">
                  <span className="h-[1px] w-6 bg-brand-orange/40" /> {t('nav.beast')}
                </a>
              </div>
            </div>

            {/* Terminal Column */}
            <div className="lg:col-span-4 space-y-8">
              <h5 id="contact" className="text-white font-mono text-sm uppercase tracking-[0.4em] font-bold border-b-2 border-white/10 pb-4 electric-text">Contact Protocol</h5>
              <div className="glass-panel p-8 bg-black/50 border-slate-700/50 rounded-md space-y-6 electric-border">
                <div className="flex items-center gap-4">
                  <Mail className="text-brand-orange electric-icon" size={24} />
                  <a href="mailto:albertgraciaquintana@gmail.com" className="text-white font-mono text-sm hover:text-brand-orange transition-colors underline underline-offset-4 decoration-brand-orange/40">
                    albertgraciaquintana@gmail.com
                  </a>
                </div>
                <div className="flex items-center gap-4">
                  <Globe className="text-brand-orange electric-icon" size={24} />
                  <span className="text-slate-400 font-mono text-xs uppercase tracking-tighter">LabrazaHost // Spain</span>
                </div>
                <div className="pt-6 border-t border-white/10 mt-6">
                  <p className="text-xs font-mono text-slate-500 block mb-3 underline">SYSTEM_UPTIME:</p>
                  <p className="text-brand-emerald font-mono text-lg font-bold glow-text">99.999% STABLE_ORCHESTRATION</p>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-40 pt-16 border-t border-white/5 flex flex-col md:flex-row justify-between items-center gap-10">
            <p className="text-slate-500 font-mono text-xs uppercase tracking-[0.2em] electric-text">
              © 2026 Albert Gràcia Quintana // Built with Sovereign AI
            </p>
            <div className="flex gap-10">
              <Activity size={20} className="text-slate-600 hover:text-brand-emerald cursor-pointer transition-colors electric-icon" />
              <Languages size={20} className="text-slate-600 hover:text-brand-orange cursor-pointer transition-colors electric-icon" onClick={toggleLanguage} />
            </div>
            <div className="font-mono text-xs text-slate-700 tracking-[0.6em] uppercase electric-text">
              [ End of Line ]
            </div>
          </div>
        </div>
      </footer>
      </div>
    </main>
  );
}

export default App;
