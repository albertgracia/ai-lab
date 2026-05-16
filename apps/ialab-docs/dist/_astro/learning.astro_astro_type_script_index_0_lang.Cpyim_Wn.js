const o="http://127.0.0.1:8083",l="https://blog-ai-lab.labrazahome.com",d={"CF-Access-Client-Id":"3093bf6c93d1c8dbb6ab65db21941ac0.access","CF-Access-Client-Secret":"e54c05bb3496e0ff55c55b6af63c456aa6b7d5171a74f42aeebd3facefe30a1c"};function a(){const t=window.location.hostname;return t==="ai-lab.labrazahome.com"||t.includes("pages.dev")||t.includes("cloudflare")}function r(){return a()?l:o}async function i(t){const n=r(),e=a()?{}:d,s=n+t;return await(await fetch(s,{cache:"no-store",headers:e})).json()}const p={critical:"text-red-400",warning:"text-yellow-400",info:"text-blue-400"},x={critical:"bg-red-950/40 border-red-900/50",warning:"bg-yellow-950/40 border-yellow-900/50",info:"bg-zinc-900 border-zinc-800"},m={high:"text-red-400",medium:"text-yellow-400",low:"text-emerald-400"};function f(t){const n=document.getElementById("patterns-section");if(document.getElementById("patterns-count").textContent=t.length+" patrones",!t.length){n.innerHTML='<p class="text-zinc-500 italic">Sin patrones detectados</p>';return}n.innerHTML=t.map(e=>{const s=p[e.severity]||"text-zinc-400";return`<div class="rounded-xl border ${x[e.severity]||"bg-zinc-900 border-zinc-800"} p-4 text-sm">
        <div class="flex items-center justify-between mb-2">
          <div class="flex items-center gap-2">
            <span class="${s} text-xs font-mono uppercase">${e.severity}</span>
            <span class="text-zinc-300 font-medium">${e.type}</span>
            <span class="text-zinc-500">→ ${e.target||""}</span>
          </div>
          <span class="text-zinc-500 text-xs">${(e.confidence*100).toFixed(0)}%</span>
        </div>
        <p class="text-zinc-400 text-xs">${e.evidence||""}</p>
        ${e.recommendation?`<p class="text-sky-400 text-xs mt-1">💡 ${e.recommendation}</p>`:""}
      </div>`}).join("")}function u(t){const n=document.getElementById("recommendations-section");if(document.getElementById("rec-count").textContent=t.length,!t.length){n.innerHTML='<p class="text-zinc-500 italic">Sin recomendaciones activas</p>';return}n.innerHTML=t.map(e=>{const s=m[e.risk]||"text-zinc-400";return`<div class="rounded-xl border border-zinc-800 bg-zinc-900 p-4 text-sm">
        <div class="flex items-center justify-between mb-2">
          <div class="flex items-center gap-2">
            <span class="text-emerald-400 text-xs font-mono">${e.action}</span>
            <span class="text-zinc-300">→ ${e.target}</span>
            <span class="${s} text-xs">${e.risk}</span>
          </div>
          <span class="text-zinc-500 text-xs">${(e.confidence*100).toFixed(0)}%</span>
        </div>
        <p class="text-zinc-400 text-xs">${e.reason||""}</p>
        ${e.evidence?e.evidence.map(c=>`<p class="text-zinc-500 text-xs ml-2">• ${c}</p>`).join(""):""}
        <div class="mt-2 flex gap-4 text-xs">
          <span class="text-zinc-600">Impacto: ${e.expected_impact||"?"}</span>
          <span class="text-zinc-600">Rollback: ${e.rollback||"?"}</span>
        </div>
        <div class="mt-2 flex gap-2">
          <a href="/ops/commands" class="text-sky-400 text-xs hover:underline">Ver en Command Pipeline →</a>
        </div>
      </div>`}).join("")}function v(t){const n=document.getElementById("efficiency-section");if(!t||!t.summary){n.innerHTML='<p class="text-zinc-500 italic">Sin datos de eficiencia</p>';return}const e=t.summary;n.innerHTML=`<div class="space-y-2 text-sm">
      <div class="flex justify-between"><span class="text-zinc-500">Avg Efficiency:</span><span class="text-zinc-300">${e.avg_efficiency}</span></div>
      <div class="flex justify-between"><span class="text-zinc-500">Avg Cost:</span><span class="text-zinc-300">${e.avg_cost}</span></div>
      <div class="flex justify-between"><span class="text-zinc-500">Avg Utility:</span><span class="text-zinc-300">${e.avg_utility}</span></div>
      <div class="flex justify-between"><span class="text-zinc-500">Good:</span><span class="text-emerald-400">${e.pct_good}%</span></div>
      <div class="flex justify-between"><span class="text-zinc-500">Poor:</span><span class="text-red-400">${e.pct_poor}%</span></div>
      <div class="border-t border-zinc-800 pt-2 mt-2">
        <span class="text-zinc-500 text-xs">Detections:</span>
        <div class="flex flex-wrap gap-1 mt-1">
          ${Object.entries(e.detections||{}).map(([s,c])=>`<span class="px-2 py-0.5 rounded bg-zinc-800 text-zinc-400 text-xs">${s}: ${c}</span>`).join("")}
        </div>
      </div>
    </div>`}function b(t){const n=document.getElementById("threshold-section");if(!t||!t.threshold_optimization){n.innerHTML='<p class="text-zinc-500 italic">Sin datos de threshold</p>';return}const e=t.threshold_optimization;t.quality,n.innerHTML=`<div class="space-y-2 text-sm">
      <div class="flex justify-between"><span class="text-zinc-500">Current:</span><span class="text-zinc-300">${e.current_threshold}</span></div>
      <div class="flex justify-between"><span class="text-zinc-500">Suggested:</span><span class="text-sky-400 font-bold">${e.suggested_threshold}</span></div>
      <div class="flex justify-between"><span class="text-zinc-500">Expected Precision:</span><span class="text-zinc-300">${e.expected_precision}</span></div>
      <div class="flex justify-between"><span class="text-zinc-500">Contamination:</span><span class="${e.contamination_at_current>.2?"text-red-400":"text-zinc-300"}">${e.contamination_at_current}</span></div>
      <div class="border-t border-zinc-800 pt-2 mt-2">
        <span class="text-zinc-500 text-xs">Collection: </span><span class="text-zinc-400">${t.collection}</span>
      </div>
    </div>`}document.addEventListener("DOMContentLoaded",async()=>{const[t,n,e,s]=await Promise.all([i("/api/learning/patterns"),i("/api/learning/recommendations"),i("/api/learning/context-efficiency"),i("/api/learning/recall-threshold?collection=incidents&q=node+failure&limit=20")]);f(t.patterns||[]),u(n.recommendations||[]),v(e),b(s)});
