import React from "react";
import { motion } from "framer-motion";
import { Cpu, Zap, Database, Layers, ExternalLink, Shield, BarChart3, Globe } from "lucide-react";
import { useLanguage } from "../context/LanguageContext";

const WorkflowCard = ({ title, tech, description, icon: Icon, color, link }) => (
  <motion.div 
    whileHover={{ y: -5 }}
    className="glass-panel p-6 border-l-4 rounded-r-lg group relative overflow-hidden"
    style={{ borderLeftColor: color }}
  >
    <div className="absolute top-0 right-0 p-3 opacity-10 group-hover:opacity-20 transition-opacity">
      <Icon size={80} />
    </div>
    <div className="flex items-start justify-between mb-4">
      <div className={`p-2 rounded bg-slate-800/50 text-${color}`}>
        <Icon size={20} className="text-white" style={{ color }} />
      </div>
      <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">{tech}</span>
    </div>
    <h3 className="text-xl font-bold text-white mb-2">{title}</h3>
    <p className="text-slate-400 text-sm leading-relaxed mb-4">
      {description}
    </p>
    <a 
      href={link} 
      target="_blank" 
      rel="noopener noreferrer" 
      className="flex items-center gap-2 text-xs font-mono text-brand-cyan opacity-0 group-hover:opacity-100 transition-opacity"
    >
      <span>VIEW NODE GRAPH</span>
      <ExternalLink size={12} />
    </a>
  </motion.div>
);

const AIShowcase = () => {
  const { t } = useLanguage();

  return (
    <section id="ai" className="py-24 relative overflow-hidden bg-brand-dark/50">
      <div className="container mx-auto px-4 relative z-10">
        <div className="flex flex-col md:flex-row justify-between items-end mb-16 gap-6">
          <div className="max-w-2xl">
            <h2 className="text-brand-orange font-mono text-sm mb-4 tracking-[0.3em] uppercase underline decoration-brand-orange/30 underline-offset-8">
              {t('ai.tag')}
            </h2>
            <h3 className="text-4xl font-bold text-white mb-6">
              {t('ai.title')}
            </h3>
            <p className="text-slate-400 leading-relaxed">
              {t('ai.desc')}
            </p>
          </div>
          <div className="p-4 glass-panel border-brand-orange/30 rounded-md">
            <p className="text-brand-orange text-xs font-mono">{t('ai.optimized')}</p>
            <p className="text-white text-lg font-bold">Radeon™ Pro // Amuse</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-6 gap-6">
          <WorkflowCard 
            title={t('ai.cards.comfy.title')}
            tech="Stable Diffusion XL"
            description={t('ai.cards.comfy.desc')}
            icon={Layers}
            color="#ff6600"
            link="https://github.com/comfyanonymous/ComfyUI"
          />
          <WorkflowCard 
            title={t('ai.cards.amuse.title')}
            tech="AMD / DirectML"
            description={t('ai.cards.amuse.desc')}
            icon={Zap}
            color="#ff4d00"
            link="https://www.amd.com/en/technologies/radeon-pro-software"
          />
          <WorkflowCard 
            title={t('ai.cards.privacy.title')}
            tech="Privacy Layer"
            description={t('ai.cards.privacy.desc')}
            icon={Shield}
            color="#10b981"
            link="https://www.privacyguides.org/en/os/linux/"
          />
          <WorkflowCard 
            title={t('ai.cards.orchestration.title')}
            tech="Docker / WSL2"
            description={t('ai.cards.orchestration.desc')}
            icon={Database}
            color="#00f3ff"
            link="https://docs.docker.com/desktop/wsl/"
          />
          <WorkflowCard 
            title={t('ai.cards.edge.title')}
            tech="Nginx Proxy"
            description={t('ai.cards.edge.desc')}
            icon={Globe}
            color="#ec4899"
            link="https://nginxproxymanager.com/"
          />
          <WorkflowCard 
            title={t('ai.cards.metrics.title')}
            tech="Grafana / Beszel"
            description={t('ai.cards.metrics.desc')}
            icon={BarChart3}
            color="#8b5cf6"
            link="https://grafana.com/docs/grafana/latest/getting-started/get-started-grafana-prometheus/"
          />
        </div>
      </div>
      
      {/* Decorative Blur */}
      <div className="absolute -bottom-24 -left-24 w-96 h-96 bg-brand-orange/10 rounded-full blur-[100px]" />
    </section>
  );
};

export default AIShowcase;
