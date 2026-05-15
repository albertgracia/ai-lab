import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Activity, ShieldCheck, Globe, Cpu, Database, Zap } from "lucide-react";
import { useLanguage } from "../context/LanguageContext";

const StatusLine = ({ label, value, status = "active" }) => (
  <div className="flex items-center justify-between py-2 border-b border-white/5 last:border-0 hover:bg-white/5 transition-colors px-2">
    <div className="flex items-center gap-3">
      <div className={`h-1.5 w-1.5 rounded-full ${status === "active" ? "bg-brand-emerald shadow-[0_0_8px_#10b981]" : "bg-brand-amber"}`} />
      <span className="text-slate-400 text-xs font-mono tracking-widest uppercase">{label}</span>
    </div>
    <span className="text-white font-mono text-xs">{value}</span>
  </div>
);

const LiveStatus = () => {
  const { t } = useLanguage();
  const [logs, setLogs] = useState([
    "BOOT_SEQUENCE: THE_BEAST_V2_LOADED",
    "PHYSICAL_LAYER: 7800X3D_STABLE_OC",
    "VRAM_ALLOCATION: RX_9070XT_MOD_ACTIVE",
    "DRAM_VALIDATION: 6200MT/s_QUALIFIED",
  ]);

  useEffect(() => {
    const interval = setInterval(() => {
      const newLog = `METRIC_SYNC_${Math.floor(Math.random() * 1000)}: 7800X3D_TEMP_STABLE_42C_${new Date().toLocaleTimeString()}`;
      setLogs(prev => [newLog, ...prev.slice(0, 3)]);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <section id="beast" className="py-24 bg-brand-dark relative">
      <div className="container mx-auto px-4">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Main Status Panel */}
          <div className="lg:col-span-2 glass-panel p-8 border-t-2 border-brand-orange relative overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-brand-orange/5 rounded-full blur-[50px]" />
            
            <div className="flex items-center justify-between mb-8">
              <div>
                <h4 className="text-brand-orange font-mono text-xs tracking-[0.4em] uppercase mb-2">{t('status.title')}</h4>
                <p className="text-2xl font-bold text-white tracking-tight leading-none mb-1">{t('status.subtitle')}</p>
                <p className="text-slate-500 text-[10px] font-mono tracking-tight uppercase">{t('status.footer')}</p>
              </div>
              <div className="flex items-center gap-4">
              <div className="flex flex-col items-end gap-1">
                <span className="text-white font-mono text-[10px] uppercase opacity-50 tracking-widest whitespace-nowrap">{t('status.metrics.clock')}</span>
                <span className="text-brand-orange font-mono text-xl font-bold leading-none">6200 MT/s</span>
              </div>
                <div className="h-10 w-10 rounded-full border border-brand-orange flex items-center justify-center text-brand-orange">
                  <Zap size={20} className="animate-pulse" />
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div className="space-y-1">
                <StatusLine label={t('status.metrics.proc')} value="Ryzen 7 7800X3D" />
                <StatusLine label={t('status.metrics.gpu')} value="RX 9070 (BIOS Mod 9070XT)" />
                <StatusLine label={t('status.metrics.tune')} value="PBO2 / Curve Opt" />
                <StatusLine label={t('status.metrics.cooling')} value="EKWB / 11x Lian Li" />
                <StatusLine label={t('status.metrics.os')} value="WSL2 / Windows 11" />
              </div>
              <div className="space-y-1">
                <StatusLine label="DRAM Config" value="64GB DDR5 CL30" />
                <StatusLine label="Manual OC" value="6200 MT/s Verified" />
                <StatusLine label="AI Threads" value="Optimized Local" />
                <StatusLine label="Storage" value="NVMe Gen5 RAID" />
                <StatusLine label="Kernel" value="Custom Linux v6.x" />
              </div>
            </div>
            
            {/* Live Console */}
            <div className="mt-8 bg-black/60 p-4 rounded border border-white/5 font-mono text-[10px] text-brand-orange/60 space-y-1 h-32 overflow-hidden shadow-inner crt-overlay">
              <AnimatePresence>
                {logs.map((log, i) => (
                  <motion.p 
                    key={log} 
                    initial={{ opacity: 0, x: -10 }} 
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.3 }}
                    className="truncate"
                  >
                    <span className="text-slate-600 mr-2">[{new Date().toISOString().split('T')[1].split('.')[0]}]</span> 
                    {log}
                  </motion.p>
                ))}
              </AnimatePresence>
              <p className="animate-pulse">_</p>
            </div>
          </div>

          <div className="space-y-6">
            <div className="glass-panel p-6 border-l-2 border-red-500 bg-red-500/5">
              <div className="flex justify-between items-start mb-4">
                <h5 className="text-white font-bold text-xs font-mono uppercase">{t('status.legacyNote')}</h5>
                <span className="text-[10px] font-mono text-red-500 px-2 border border-red-500 animate-pulse">LEGACY_DNA</span>
              </div>
              <p className="text-[10px] font-mono text-slate-400 leading-relaxed italic border-t border-white/5 pt-2">
                "{t('legacy.quote')}"
              </p>
            </div>

            <div className="glass-panel p-6 border-l-2 border-brand-orange">
              <div className="flex items-center gap-3 mb-4">
                <Activity size={20} className="text-brand-orange" />
                <h5 className="text-white font-bold text-sm tracking-widest uppercase">Node Health</h5>
              </div>
              <div className="flex items-end justify-between">
                <span className="text-2xl font-mono text-white">100% OK</span>
                <span className="text-[10px] text-brand-orange font-mono bg-brand-orange/10 px-2 py-0.5 rounded uppercase">Verified</span>
              </div>
            </div>

            <div className="glass-panel p-6 border-l-2 border-brand-blue bg-brand-blue/5">
              <div className="flex items-center gap-3 mb-4">
                <ShieldCheck size={20} className="text-brand-blue" />
                <h5 className="text-white font-bold text-sm tracking-widest uppercase">Service Mesh</h5>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-brand-emerald text-sm font-bold uppercase tracking-widest">Active Lock</span>
                <div className="h-4 w-4 rounded-full bg-brand-emerald animate-ping" />
              </div>
            </div>
          </div>

        </div>
      </div>
    </section>
  );
};

export default LiveStatus;
