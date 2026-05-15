import React from "react";
import { motion } from "framer-motion";
import { Languages } from "lucide-react";
import { useLanguage } from "../context/LanguageContext";

const LanguageSwitch = () => {
  const { lang, toggleLanguage } = useLanguage();

  return (
    <div className="flex items-center gap-6">
      <div 
        onClick={toggleLanguage}
        className="relative w-28 h-10 bg-black/60 backdrop-blur-xl border-2 border-white/10 rounded-full cursor-pointer flex items-center px-1.5 group hover:border-brand-orange/50 transition-colors shadow-[0_0_15px_rgba(255,102,0,0.1)] electric-border"
      >
        {/* Sliding Indicator */}
        <motion.div
          animate={{ x: lang === 'en' ? 0 : 64 }}
          transition={{ type: "spring", stiffness: 300, damping: 30 }}
          className="absolute w-10 h-8 bg-brand-orange rounded-full shadow-[0_0_20px_rgba(255,102,0,0.6)] z-0 electric-icon"
        />
        
        {/* Labels Overlay */}
        <div className="relative z-10 w-full flex justify-between px-3.5">
          <span className={`text-[11px] font-black font-mono transition-colors duration-300 ${lang === 'en' ? 'text-brand-dark' : 'text-slate-500'}`}>
            ENG
          </span>
          <span className={`text-[11px] font-black font-mono transition-colors duration-300 ${lang === 'es' ? 'text-brand-dark' : 'text-slate-500'}`}>
            ESP
          </span>
        </div>
      </div>
      
      <Languages size={20} className="text-slate-500 group-hover:text-brand-orange transition-colors hidden md:block electric-icon" />
    </div>
  );
};

export default LanguageSwitch;
