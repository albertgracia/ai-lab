import React, { createContext, useContext, useState } from 'react';

const LanguageContext = createContext();

const translations = {
  enCode: "ENG",
  esCode: "ESP",
  en: {
    nav: {
      evolution: "// EVOLUTION",
      legacy: "Legacy_DNA",
      ai: "AI_Core",
      beast: "The_Beast",
      gallery: "Gallery"
    },
    hero: {
      status: "// DEPLOY_STATUS: ACTIVE_NODE",
      title1: "Systems Architect:",
      title2: "Multi-Stack Infrastructure",
      subtitle: "From Sinclair BASIC to Neural Networks",
      description: "In 1968, the journey began. From managing bits on a ZX Spectrum to orchestrating 64GB @ 6200 MT/s and Local GenAI on custom AMD hardware. Precision engineering for a multi-service future.",
      handshake: "INIT_HANDSHAKE",
      bridge: "VIEW_INFRA"
    },
    legacy: {
      tag: "1968 // ORIGINS",
      title: "OVER HALF A CENTURY OF PRECISION",
      quote: "The same obsession with optimizing 16KB of RAM in the 80s as I apply today to exprimir 64GB @ 6200 MT/s in a multi-container environment.",
      modernTitle: "Multi-Threaded Mastery",
      modernDesc: "Today, I leverage that 'Legacy DNA' to orchestrate high-availability multi-stack clusters. From hardware modding to local AI workflows, my infrastructure is built for absolute technical sovereignty.",
      tuning: {
        dram: "X870E AORUS PRO ICE",
        dramSub: "Manual Latency @ 6200 MT/s",
        gpu: "RX 9070 BIOS MOD",
        gpuSub: "Unlocked to 9070XT Inference",
        loop: "EKWB CUSTOM LOOP",
        loopSub: "Lian Li Edge EG1300 / Stable 42C"
      },
      button: "EXPLORE MULTI-STACK"
    },
    ai: {
      tag: "Workflows & Local Optimization",
      title: "Generative AI & Local Sovereignty",
      desc: "Demonstrating the power of local GenAI outside the CUDA monopoly. Infrastructure tuned for AMD hardware using DirectML and ROCm paths, ensuring 100% data privacy and high-performance inference.",
      optimized: "AMD OPTIMIZED ⚡",
      cards: {
        comfy: { title: "ComfyUI Clusters", desc: "Highly complex node-based workflows for professional image generation." },
        amuse: { title: "Amuse Integration", desc: "Leveraging Amuse for seamless image generation on AMD hardware." },
        privacy: { title: "Data Sovereignty", desc: "Zero-cloud dependency. All models and assets remain within local encrypted infra." },
        orchestration: { title: "Model Orchestration", desc: "Containerized LLMs and Diffusion models managed via Portainer." },
        edge: { title: "Edge Inference", desc: "Secure exposure of local AI services via Nginx and Cloudflare." },
        metrics: { title: "Performance Metrics", desc: "Real-time GPU/VRAM monitoring for peak inference efficiency." }
      }
    },
    infra: {
      tag: "Multi-Service Mesh Map",
      desc: "A high-availability production environment orchestrated on Windows 11 / WSL2. Designed for observability, security, and local AI performance.",
      groups: {
        edge: "Edge & Security",
        obs: "Observability",
        ai: "AI Engine",
        core: "Logic & Data"
      },
      callout: "Managing a complex mesh of 25+ Docker containers across segregated VLANs."
    },
    status: {
      title: "Physical Layer: \"The Beast\"",
      subtitle: "DRAM & BIOS Level Optimization",
      footer: "Custom Loop EKWB + Lian Li Edge EG1300",
      metrics: {
        clock: "Memory Clock",
        proc: "Processor",
        gpu: "Graphics",
        tune: "Manual Tune",
        cooling: "Cooling",
        os: "OS Engine"
      },
      legacyNote: "SINCLAIR MODE"
    },
    gallery: {
      items: {
        dram: { title: "Acer Predator Vesta II", desc: "64GB DDR5 tuned to 6200 MT/s CL30." },
        pbo: { title: "Ryzen 7 7800X3D", desc: "Manual PBO2 Curve Optimization on X870E Ice." },
        cooling: { title: "Custom EKWB Loop", desc: "Thermal equilibrium at 42C under heavy load." },
        mod: { title: "RX 9070 BIOS Mod", desc: "Unlocked to 9070XT specs for high-performance inference." },
        build: { title: "Build Architecture", desc: "Lian Li Edge EG1300 ATX 3.1 Platinum Power." },
        thermal: { title: "Thermal Interconnects", desc: "Liquid metal application and cold plate seating." }
      }
    },
    evolution: {
      tag: "1968 - 2026 // The Precision Evolution",
      title: "From 8 Bits to Neural Networks:",
      subtitle: "A Lifetime of Optimization.",
      p1: "My technological journey began in 1968, an era where silicon was a promise and the Sinclair ZX Spectrum was my first canvas. There, programming in BASIC and navigating BBS through copper modems, I learned the most valuable lesson for an engineer: every byte counts.",
      p2: "Today, that same obsession with efficiency flows through an AMD Ryzen 7 7800X3D architecture and 64GB of RAM manually optimized to 6200 MT/s. My Home Lab is not just a set of Docker containers and GenAI nodes (ComfyUI); it is a living ecosystem, cooled by a custom EKWB loop where hardware and software operate in perfect symbiosis.",
      p3: "From portfolio.labrazahome.es, I manage a multi-stack infrastructure that combines old-school resilience with the power of modern Artificial Intelligence. I don't just deploy solutions; I build the iron that makes them possible."
    }
  },
  es: {
    nav: {
      evolution: "// EVOLUCIÓN",
      legacy: "ADN_Legado",
      ai: "Núcleo_IA",
      beast: "La_Bestia",
      gallery: "Galería"
    },
    hero: {
      status: "// ESTADO_DESPLIEGUE: NODO_ACTIVO",
      title1: "Arquitecto de Sistemas:",
      title2: "Infraestructura Multi-Stack",
      subtitle: "Del Sinclair BASIC a las Redes Neuronales",
      description: "En 1968 comenzó el viaje. De gestionar bits en un ZX Spectrum a orquestar 64GB @ 6200 MT/s e IA Generativa local en hardware AMD. Ingeniería de precisión para un futuro multi-servicio.",
      handshake: "INICIAR_CONEXIÓN",
      bridge: "VER_INFRA"
    },
    legacy: {
      tag: "1968 // ORÍGENES",
      title: "MÁS DE MEDIO SIGLO DE PRECISIÓN",
      quote: "La misma obsesión por optimizar 16KB de RAM en los 80 es la que hoy aplico para exprimir 64GB @ 6200 MT/s en un entorno multi-contenedor.",
      modernTitle: "Maestría Multi-Hilo",
      modernDesc: "Hoy, utilizo ese 'ADN de Legado' para orquestar clusters multi-stack de alta disponibilidad. Desde el modding de hardware hasta flujos de IA local, mi infraestructura está construida para la soberanía técnica absoluta.",
      tuning: {
        dram: "X870E AORUS PRO ICE",
        dramSub: "Latencia Manual @ 6200 MT/s",
        gpu: "MOD DE BIOS RX 9070",
        gpuSub: "Desbloqueada a 9070XT para Inferencia",
        loop: "BUCLE PERSONALIZADO EKWB",
        loopSub: "Lian Li Edge EG1300 / Estable 42C"
      },
      button: "EXPLORAR MULTI-STACK"
    },
    ai: {
      tag: "Flujos de Trabajo y Optimización Local",
      title: "IA Generativa y Soberanía Local",
      desc: "Demostrando el poder de la IA Generativa local fuera del monopolio de CUDA. Mi infraestructura está ajustada para hardware AMD utilizando rutas DirectML y ROCm, garantizando 100% de privacidad de datos.",
      optimized: "OPTIMIZADO PARA AMD ⚡",
      cards: {
        comfy: { title: "Clusters ComfyUI", desc: "Flujos complejos basados en nodos para generación de imágenes profesional." },
        amuse: { title: "Integración Amuse", desc: "Uso de Amuse para generación fluida de imágenes en hardware AMD." },
        privacy: { title: "Soberanía de Datos", desc: "Dependencia cero de la nube. Todos los modelos y activos permanecen en infra local cifrada." },
        orchestration: { title: "Orquestación de Modelos", desc: "LLMs y modelos de Difusión contenedorizados y gestionados vía Portainer." },
        edge: { title: "Inferencia en el Edge", desc: "Exposición segura de servicios de IA local mediante Nginx y Cloudflare." },
        metrics: { title: "Métricas de Rendimiento", desc: "Monitoreo en tiempo real de GPU/VRAM para máxima eficiencia de inferencia." }
      }
    },
    infra: {
      tag: "Mapa de Malla Multi-Servicio",
      desc: "Un entorno de producción de alta disponibilidad orquestado en Windows 11 / WSL2. Diseñado para observabilidad, seguridad y rendimiento de IA local.",
      groups: {
        edge: "Edge y Seguridad",
        obs: "Observability",
        ai: "Motor de IA",
        core: "Lógica y Datos"
      },
      callout: "Gestionando una malla compleja de más de 25 contenedores Docker en VLANs segregadas."
    },
    status: {
      title: "Capa Física: \"La Bestia\"",
      subtitle: "Optimización a Nivel de DRAM y BIOS",
      footer: "Bucle EKWB + Lian Li Edge EG1300",
      metrics: {
        clock: "Reloj de Memoria",
        proc: "Procesador",
        gpu: "Gráficos",
        tune: "Ajuste Manual",
        cooling: "Refrigeración",
        os: "Motor de SO"
      },
      legacyNote: "MODO SINCLAIR"
    },
    gallery: {
      items: {
        dram: { title: "Acer Predator Vesta II", desc: "64GB DDR5 ajustado a 6200 MT/s CL30." },
        pbo: { title: "Ryzen 7 7800X3D", desc: "Optimización manual de curva PBO2 en X870E Ice." },
        cooling: { title: "Bucle EKWB Personalizado", desc: "Equilibrio térmico a 42C bajo carga pesada." },
        mod: { title: "Mod de BIOS RX 9070", desc: "Desbloqueada a especificaciones 9070XT para inferencia de alto rendimiento." },
        build: { title: "Arquitectura del Equipo", desc: "Potencia Lian Li Edge EG1300 ATX 3.1 Platinum." },
        thermal: { title: "Interconexiones Térmicas", desc: "Aplicación de metal líquido y asentamiento de placa fría." }
      }
    },
    evolution: {
      tag: "1968 - 2026 // La Evolución de la Precisión",
      title: "De 8 Bits a Redes Neuronales:",
      subtitle: "Una Vida de Optimización.",
      p1: "Mi viaje tecnológico comenzó en 1968, una era donde el silicio era una promesa y el Sinclair ZX Spectrum mi primer lienzo. Allí, programando en BASIC y navegando por BBS a través de módems de cobre, aprendí la lección más valiosa de un ingeniero: cada byte cuenta.",
      p2: "Hoy, esa misma obsesión por la eficiencia fluye a través de una arquitectura AMD Ryzen 7 7800X3D y 64GB de RAM optimizados manualmente a 6200 MT/s. Mi Home Lab no es solo un conjunto de contenedores Docker y nodos de IA Generativa (ComfyUI); es un ecosistema vivo, refrigerado por un loop custom de EKWB donde el hardware y el software operan en perfecta simbiosis.",
      p3: "Desde portfolio.labrazahome.es, gestiono una infraestructura multi-stack que combina la resiliencia de la vieja escuela con la potencia de la Inteligencia Artificial moderna. No solo despliego soluciones; construyo el hierro que las hace posibles."
    }
  }
};

export const LanguageProvider = ({ children }) => {
  const [lang, setLang] = useState('en');

  const t = (path) => {
    const keys = path.split('.');
    let result = translations[lang];
    for (const key of keys) {
      if (result[key]) {
        result = result[key];
      } else {
        return path;
      }
    }
    return result;
  };

  const toggleLanguage = () => {
    setLang(prev => (prev === 'en' ? 'es' : 'en'));
  };

  const currentLangLabel = translations[`${lang}Code`];

  return (
    <LanguageContext.Provider value={{ t, lang, toggleLanguage, currentLangLabel }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => useContext(LanguageContext);
