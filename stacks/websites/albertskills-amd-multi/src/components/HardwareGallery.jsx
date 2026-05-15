import React from "react";
import { motion } from "framer-motion";
import { Lock, Eye, Cpu, Zap, Activity, Thermometer } from "lucide-react";
import { useLanguage } from "../context/LanguageContext";

// Import Hardware Assets
import dramImg from "../assets/1529-acer-predator-vesta-ii-rgb-ddr5-6000mhz-64gb-2x32gb-cl30.webp";
import pboImg from "../assets/IMG_20250716_202924.jpg";
import coolingImg from "../assets/IMG_20250706_015320.jpg";
import modImg from "../assets/IMG_20250706_015327.jpg";
import buildImg from "../assets/IMG_20250716_202912 - copia.jpg";
import thermalImg from "../assets/IMG_20250706_015334.jpg";

const GalleryItem = ({ title, desc, img, icon: Icon, colorClass }) => (
  <motion.div 
    whileHover={{ scale: 1.05 }}
    className="group relative aspect-[4/3] overflow-hidden rounded-xl border-2 border-white/5 bg-slate-900/40 cursor-pointer shadow-2xl"
  >
    {/* Hardware Image */}
    <img 
      src={img} 
      alt={title} 
      className="w-full h-full object-cover opacity-50 group-hover:opacity-100 transition-all duration-700 grayscale group-hover:grayscale-0 scale-110 group-hover:scale-100"
    />
    
    {/* Scanline Effect Overlay */}
    <div className="absolute inset-0 opacity-20 pointer-events-none bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,255,0.06))] bg-[size:100%_2px,3px_100%] z-20" />
    
    {/* Content Overlay */}
    <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/20 to-transparent p-10 flex flex-col justify-end transform translate-y-6 group-hover:translate-y-0 transition-transform duration-500">
      <div className="flex items-center gap-5 mb-4">
        <div className={`p-3 rounded-md bg-black/70 border border-white/10 ${colorClass} electric-icon`}>
          <Icon size={24} />
        </div>
        <h4 className="text-white font-bold text-xl tracking-tight electric-text">{title}</h4>
      </div>
      <p className="text-slate-300 text-xs font-mono leading-relaxed opacity-0 group-hover:opacity-100 transition-opacity delay-100 uppercase tracking-[0.2em]">
        {desc}
      </p>
    </div>

    {/* Status Badge */}
    <div className="absolute top-4 right-4 px-2 py-1 bg-black/80 border border-white/10 rounded-sm backdrop-blur-md opacity-0 group-hover:opacity-100 transition-opacity">
      <span className="text-brand-orange font-mono text-[8px] tracking-[0.2em] font-bold">VERIFIED_HARDWARE</span>
    </div>
  </motion.div>
);

const HardwareGallery = () => {
  const { t } = useLanguage();

  const galleryItems = [
    { title: t('gallery.items.pbo.title'), desc: t('gallery.items.pbo.desc'), img: modImg, icon: Activity, colorClass: "text-brand-orange" },
    { title: t('gallery.items.dram.title'), desc: t('gallery.items.dram.desc'), img: dramImg, icon: Zap, colorClass: "text-brand-blue" },
    { title: t('gallery.items.cooling.title'), desc: t('gallery.items.cooling.desc'), img: coolingImg, icon: Thermometer, colorClass: "text-brand-emerald" },
    { title: t('gallery.items.mod.title'), desc: t('gallery.items.mod.desc'), img: pboImg, icon: Cpu, colorClass: "text-brand-orange" },
    { title: t('gallery.items.build.title'), desc: t('gallery.items.build.desc'), img: buildImg, icon: Lock, colorClass: "text-brand-red" },
    { title: t('gallery.items.thermal.title'), desc: t('gallery.items.thermal.desc'), img: thermalImg, icon: Eye, colorClass: "text-brand-emerald" },
  ];

  return (
    <section id="gallery" className="py-24 relative overflow-hidden bg-slate-950">
      <div className="container mx-auto px-6">
        <div className="flex flex-col md:flex-row justify-between items-end mb-16 gap-6">
          <div className="max-w-2xl">
            <div className="inline-block px-3 py-1 bg-brand-orange/10 border border-brand-orange/20 rounded-full mb-4">
              <span className="text-brand-orange font-mono text-[10px] tracking-[0.4em] font-bold uppercase">
                {t('nav.gallery')} // CAPTURED_HARDWARE
              </span>
            </div>
            <h3 className="text-4xl lg:text-5xl font-bold text-white mb-6">
              Visualizing the <span className="text-brand-orange italic">Physical Layer</span>
            </h3>
            <p className="text-slate-400 leading-relaxed text-sm md:text-base max-w-xl">
              Macro photography of the custom EKWB loop, BIOS-modded silicon, 
              and the high-speed interconnects that power this sovereign infrastructure.
            </p>
          </div>
          <div className="flex items-center gap-4 text-slate-500 font-mono text-[10px]">
            <div className="flex items-center gap-2 px-4 py-2 bg-slate-900/50 border border-white/5 rounded-sm">
              <Lock size={12} className="text-slate-400" />
              SECURE_ENCRYPTION: AES-256
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-12 lg:gap-16">
          {galleryItems.map((item, index) => (
            <GalleryItem key={index} {...item} />
          ))}
        </div>
      </div>
    </section>
  );
};

export default HardwareGallery;
