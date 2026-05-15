import React from "react";
import { motion } from "framer-motion";
import { Server, Shield, Activity, Cpu } from "lucide-react";
import { useLanguage } from "../context/LanguageContext";

const InfraGroup = ({ title, icon: Icon, items, color, delay }) => (
  <motion.div 
    initial={{ opacity: 0, y: 20 }}
    whileInView={{ opacity: 1, y: 0 }}
    viewport={{ once: true }}
    transition={{ duration: 0.6, delay }}
    className="group"
  >
    <div className={`flex items-center gap-3 mb-6 p-3 glass-panel border-r-4 rounded-l-md`} style={{ borderRightColor: color }}>
      <Icon size={24} style={{ color }} />
      <h4 className="text-lg font-bold text-white tracking-wide uppercase">{title}</h4>
    </div>
    <div className="space-y-3">
      {items.map((item, idx) => (
        <div key={idx} className="flex items-center justify-between p-3 bg-slate-900/40 border border-slate-800 rounded group-hover:border-slate-700 transition-colors">
          <span className="text-slate-300 font-mono text-sm">{item}</span>
          <div className="h-1.5 w-1.5 rounded-full bg-brand-emerald animate-pulse" />
        </div>
      ))}
    </div>
  </motion.div>
);

const InfraMap = () => {
  const { t } = useLanguage();

  return (
    <section id="infra" className="py-24 bg-brand-dark/80 relative">
      <div className="container mx-auto px-4">
        <div className="text-center mb-16">
          <h2 className="text-5xl font-bold text-white mb-4">{t('infra.tag')}</h2>
          <p className="text-slate-400 max-w-2xl mx-auto">
            {t('infra.desc')}
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 relative">
          {/* Connector SVG Background (Simplified/Abstract) */}
          <div className="hidden lg:block absolute top-1/2 left-0 w-full h-[2px] bg-gradient-to-r from-transparent via-slate-800 to-transparent -translate-y-1/2 z-0" />
          
          <InfraGroup 
            title={t('infra.groups.edge')} 
            icon={Shield} 
            items={["Nginx Proxy Manager", "Cloudflare Tunnels", "Tailscale VPN", "Pi-hole DNS"]}
            color="#ff6600"
            delay={0.1}
          />
          <InfraGroup 
            title={t('infra.groups.obs')} 
            icon={Activity} 
            items={["Prometheus & Grafana", "Unpoller (Ubiquiti)", "Uptime Kuma", "Beszel Metrics"]}
            color="#10b981"
            delay={0.2}
          />
          <InfraGroup 
            title={t('infra.groups.ai')} 
            icon={Cpu} 
            items={["ComfyUI (Workflows)", "Amuse (AMD Opt)", "DirectML Environment", "VRAM Orchestration"]}
            color="#ff4d00"
            delay={0.3}
          />
          <InfraGroup 
            title={t('infra.groups.core')} 
            icon={Server} 
            items={["n8n Automation", "PostgreSQL DB", "Portainer (Docker)", "Microservices"]}
            color="#00f3ff"
            delay={0.4}
          />
        </div>

        {/* Technical Callout */}
        <motion.div 
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          className="mt-20 p-8 glass-panel border-t-2 border-brand-orange/20 flex flex-col md:flex-row items-center justify-between gap-8"
        >
          <div className="flex items-center gap-6">
            <div className="text-4xl font-mono text-brand-orange tracking-tighter">WSL2.ENV</div>
            <div className="h-12 w-[1px] bg-slate-800 hidden md:block" />
            <div className="space-y-1">
              <p className="text-white font-bold">Unified Control Plane</p>
              <p className="text-slate-400 text-sm">{t('infra.callout')}</p>
            </div>
          </div>
          <div className="flex gap-4">
            <div className="px-4 py-2 bg-slate-800/50 rounded border border-slate-700 text-[10px] font-mono text-slate-400">
              LATENCY: 12ms
            </div>
            <div className="px-4 py-2 bg-slate-800/50 rounded border border-slate-700 text-[10px] font-mono text-slate-400">
              MTU: 1500
            </div>
            <div className="px-4 py-2 bg-slate-800/50 rounded border border-slate-700 text-[10px] font-mono text-slate-400">
              UPTIME: 99.9%
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
};

export default InfraMap;
