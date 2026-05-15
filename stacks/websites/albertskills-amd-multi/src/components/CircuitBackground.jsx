import React from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';

const CircuitBackground = () => {
  const { scrollYProgress } = useScroll();
  
  // Retro Green to modern component colors
  const retroGreen = "#39ff14";
  
  const color1 = useTransform(scrollYProgress, [0, 0.4], [retroGreen, "#FF4700"]); // AMD
  const color2 = useTransform(scrollYProgress, [0, 0.4], [retroGreen, "#00C2FF"]); // EKWB / RAM
  const color3 = useTransform(scrollYProgress, [0, 0.4], [retroGreen, "#FFFFFF"]); // IO / Ice
  const color4 = useTransform(scrollYProgress, [0, 0.4], [retroGreen, "#00C2FF"]); // EKWB
  
  const nodeStroke = useTransform(scrollYProgress, [0, 0.4], [retroGreen, "#FF4700"]); // Ryzen
  
  const paths = [
    { id: 'cpu-to-gpu', d: "M 500 400 L 800 400 L 800 600", color: color1, label: "RX 9070 XT" },
    { id: 'cpu-to-ram', d: "M 500 400 L 500 200 L 650 200", color: color2, label: "6200 MT/s" },
    { id: 'cpu-to-io', d: "M 500 400 L 200 400 L 200 700", color: color3, label: "Gigabyte X870E" },
    { id: 'cpu-to-ekwb', d: "M 500 400 L 350 250 L 200 250", color: color4, label: "EK-Quantum" },
  ];

  return (
    <div className="fixed inset-0 z-0 bg-slate-950 overflow-hidden pointer-events-none">
      <svg className="absolute w-full h-full opacity-40" viewBox="0 0 1000 1000">
        <defs>
          <filter id="glow">
            <feGaussianBlur stdDeviation="2.5" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>
        
        {paths.map((path) => (
          <path
            key={`base-${path.id}`}
            d={path.d}
            fill="none"
            stroke="rgba(255,255,255,0.05)"
            strokeWidth="2"
          />
        ))}
        
        {paths.map((path) => (
          <motion.path
            key={`pulse-${path.id}`}
            d={path.d}
            fill="none"
            stroke={path.color}
            strokeWidth="3"
            filter="url(#glow)"
            initial={{ pathLength: 0, opacity: 0 }}
            animate={{ 
              pathLength: [0, 1], 
              opacity: [0, 1, 0],
              transition: { 
                duration: 3, 
                repeat: Infinity, 
                ease: "linear",
                delay: Math.random() * 2 
              }
            }}
          />
        ))}

        <motion.rect
          x="460" y="360" width="80" height="80"
          className="fill-slate-900"
          stroke={nodeStroke}
          strokeWidth="2"
          animate={{ strokeOpacity: [0.2, 1, 0.2] }}
          transition={{ duration: 2, repeat: Infinity }}
        />
        <text x="500" y="405" textAnchor="middle" className="fill-white text-[10px] font-mono">RYZEN</text>
      </svg>

      <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-transparent to-slate-950 opacity-80" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_transparent_0%,_rgba(2,6,23,0.8)_100%)]" />
    </div>
  );
};

export default CircuitBackground;
