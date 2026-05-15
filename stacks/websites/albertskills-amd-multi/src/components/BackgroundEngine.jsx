import React, { useEffect, useRef, useState } from 'react';
import { motion, useScroll, useSpring, useTransform } from 'framer-motion';

const BackgroundEngine = () => {
  const canvasRef = useRef(null);
  const { scrollY } = useScroll();
  
  // Transform scroll into a "speed" multiplier (Overclocking effect)
  const scrollVelocity = useSpring(scrollY, { stiffness: 100, damping: 30 });
  const speedMult = useTransform(scrollY, [0, 5000], [1, 5]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    let animationFrameId;
    let width, height;
    
    // Configuration
    const TRACE_COUNT = 15;
    const PULSE_COUNT = 25;
    const COLORS = {
      bg: '#020617',
      trace: 'rgba(71, 85, 105, 0.15)',
      amd: '#ff6600',
      ekwb: '#00f3ff'
    };

    const nodes = [
      { name: 'Ryzen 7 7800X3D', x: 0.5, y: 0.3, isMain: true },
      { name: 'Gigabyte X870E', x: 0.2, y: 0.2 },
      { name: 'PowerColor RX 9070', x: 0.8, y: 0.5 },
      { name: 'EKWB', x: 0.3, y: 0.7 },
      { name: 'HAVN', x: 0.7, y: 0.8 }
    ];

    class Pulse {
      constructor(path) {
        this.path = path;
        this.reset();
      }

      reset() {
        this.progress = 0;
        this.speed = 0.002 + Math.random() * 0.005;
        this.color = Math.random() > 0.5 ? COLORS.amd : COLORS.ekwb;
        this.size = 2 + Math.random() * 3;
      }

      update(multiplier) {
        this.progress += this.speed * multiplier;
        if (this.progress >= 1) this.reset();
      }

      draw(ctx, w, h) {
        if (!this.path || this.path.length < 2) return;
        
        const segmentCount = this.path.length - 1;
        const totalProgress = this.progress * segmentCount;
        const currentSegment = Math.floor(totalProgress);
        const segmentProgress = totalProgress % 1;
        
        if (currentSegment >= segmentCount) return;

        const start = this.path[currentSegment];
        const end = this.path[currentSegment + 1];

        const x = (start.x + (end.x - start.x) * segmentProgress) * w;
        const y = (start.y + (end.y - start.y) * segmentProgress) * h;

        // Draw Glow
        ctx.shadowBlur = 15;
        ctx.shadowColor = this.color;
        ctx.fillStyle = this.color;
        ctx.beginPath();
        ctx.arc(x, y, this.size, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;
      }
    }

    const traces = [];
    const pulses = [];

    const init = () => {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
      
      traces.length = 0;
      pulses.length = 0;

      // Create paths from main node to others
      const main = nodes.find(n => n.isMain);
      nodes.forEach(node => {
        if (node.isMain) return;
        
        // Generate a 2-bend PCB path
        const path = [
          { x: main.x, y: main.y },
          { x: node.x, y: main.y }, // First bend (horizontal)
          { x: node.x, y: node.y }  // Second bend (vertical)
        ];
        traces.push(path);
        
        // Add multiple pulses per trace
        for (let i = 0; i < 3; i++) {
          const p = new Pulse(path);
          p.progress = Math.random();
          pulses.push(p);
        }
      });
    };

    const render = () => {
      ctx.fillStyle = COLORS.bg;
      ctx.fillRect(0, 0, width, height);

      const currentMultiplier = speedMult.get();

      // Draw Traces
      ctx.lineWidth = 1;
      ctx.strokeStyle = COLORS.trace;
      traces.forEach(path => {
        ctx.beginPath();
        ctx.moveTo(path[0].x * width, path[0].y * height);
        for(let i = 1; i < path.length; i++) {
          ctx.lineTo(path[i].x * width, path[i].y * height);
        }
        ctx.stroke();
      });

      // Draw Nodes
      nodes.forEach(node => {
        const x = node.x * width;
        const y = node.y * height;
        
        ctx.fillStyle = node.isMain ? COLORS.amd : COLORS.trace;
        ctx.beginPath();
        ctx.rect(x - 5, y - 5, 10, 10);
        ctx.fill();
        
        // Label
        ctx.fillStyle = 'rgba(255,255,255,0.3)';
        ctx.font = '9px JetBrains Mono';
        ctx.fillText(node.name.toUpperCase(), x + 12, y + 4);
      });

      // Draw Pulses
      pulses.forEach(pulse => {
        pulse.update(currentMultiplier);
        pulse.draw(ctx, width, height);
      });

      animationFrameId = requestAnimationFrame(render);
    };

    window.addEventListener('resize', init);
    init();
    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', init);
    };
  }, []);

  return (
    <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden bg-[#020617]">
      <canvas 
        ref={canvasRef} 
        className="w-full h-full opacity-40 select-none"
      />
      {/* Heavy Bokeh Overlay */}
      <div className="absolute inset-0 bg-transparent backdrop-blur-[120px] opacity-10" />
      <div className="absolute inset-0 bg-gradient-to-b from-brand-dark via-transparent to-brand-dark opacity-60" />
    </div>
  );
};

export default BackgroundEngine;
