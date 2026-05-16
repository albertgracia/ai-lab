const f="http://127.0.0.1:8083",h="https://blog-ai-lab.labrazahome.com",v={"CF-Access-Client-Id":"3093bf6c93d1c8dbb6ab65db21941ac0.access","CF-Access-Client-Secret":"e54c05bb3496e0ff55c55b6af63c456aa6b7d5171a74f42aeebd3facefe30a1c"};function u(){const t=window.location.hostname;return t==="ai-lab.labrazahome.com"||t.includes("pages.dev")||t.includes("cloudflare")}function z(){return u()?h:f}async function $(t){const l=z(),n=u()?{}:v,c=l+t;return await(await fetch(c,{cache:"no-store",headers:n})).json()}const m={pending:{dot:"bg-yellow-400",label:"text-yellow-400"},executed:{dot:"bg-emerald-400",label:"text-emerald-400"},failed:{dot:"bg-red-500",label:"text-red-400"},rejected:{dot:"bg-zinc-500",label:"text-zinc-400"}},y={low:"text-emerald-400",medium:"text-yellow-400",high:"text-red-400"};let s=[],p="";function x(){const t=p?s.filter(e=>e.status===p):s,l=s.length;document.getElementById("total-count").textContent=l;const n={pending:s.filter(e=>e.status==="pending").length,executed:s.filter(e=>e.status==="executed").length,failed:s.filter(e=>e.status==="failed").length,rejected:s.filter(e=>e.status==="rejected").length};if(document.getElementById("status-breakdown").textContent=`${n.pending} pend · ${n.executed} ok · ${n.failed} fail · ${n.rejected} rej`,t.length===0){document.getElementById("commands-table").innerHTML='<p class="text-zinc-500 italic text-center py-8">No hay comandos con este estado</p>';return}let c='<div class="space-y-2">';for(const e of t){const a=m[e.status]||m.pending,d=y[e.risk]||"text-zinc-400",o=e.created_at?new Date(e.created_at*1e3).toLocaleString():"--",i=e.approved_at?new Date(e.approved_at*1e3).toLocaleString():"",b=e.command.length>60?e.command.slice(0,60)+"...":e.command,r=e.result?.success,g=e.result?.exit_code;c+=`<div class="rounded-xl border border-zinc-800 bg-zinc-900 p-4 text-sm hover:border-zinc-700 transition-colors">
        <div class="flex items-center justify-between cursor-pointer toggle-detail" data-id="${e.id}">
          <div class="flex items-center gap-3 min-w-0 flex-1">
            <span class="inline-block w-2.5 h-2.5 rounded-full ${a.dot} shrink-0"></span>
            <span class="${a.label} text-xs font-mono uppercase shrink-0">${e.status}</span>
            <span class="text-zinc-300 font-mono truncate">${b}</span>
            <span class="text-zinc-500 text-xs shrink-0 ${d}">${e.risk}</span>
          </div>
          <div class="flex items-center gap-4 shrink-0 ml-4">
            <span class="text-zinc-500 text-xs">${o}</span>
            ${e.reason?`<span class="text-zinc-500 text-xs italic hidden md:inline">${e.reason}</span>`:""}
            <span class="text-zinc-600 text-xs toggle-icon">▶</span>
          </div>
        </div>
        <div id="detail-${e.id}" class="hidden mt-3 pt-3 border-t border-zinc-800 text-xs space-y-2">
          <div class="grid grid-cols-2 gap-4">
            <div><span class="text-zinc-500">Comando:</span> <code class="text-zinc-200 ml-1">${e.command}</code></div>
            <div><span class="text-zinc-500">ID:</span> <span class="text-zinc-400 ml-1 font-mono">${e.id}</span></div>
            ${e.reason?`<div><span class="text-zinc-500">Razon:</span> <span class="text-zinc-400 ml-1">${e.reason}</span></div>`:""}
            ${i?`<div><span class="text-zinc-500">Aprobado:</span> <span class="text-zinc-400 ml-1">${i}</span></div>`:""}
          </div>
          ${e.result?`
          <div class="mt-2 p-3 rounded-lg ${r?"bg-emerald-950/40 border border-emerald-900/50":"bg-red-950/40 border border-red-900/50"}">
            <div class="flex gap-4 mb-1">
              <span class="${r?"text-emerald-400":"text-red-400"} font-bold">${r?"EXIT 0":"EXIT "+(g??"?")}</span>
            </div>
            ${e.result.output?`<pre class="text-zinc-300 mt-1 whitespace-pre-wrap max-h-24 overflow-y-auto">${e.result.output}</pre>`:""}
            ${e.result.errors?`<pre class="text-red-400 mt-1 whitespace-pre-wrap max-h-16 overflow-y-auto">${e.result.errors}</pre>`:""}
          </div>`:`
          <div class="text-zinc-600 italic">Sin ejecutar</div>`}
        </div>
      </div>`}c+="</div>",document.getElementById("commands-table").innerHTML=c,document.querySelectorAll(".toggle-detail").forEach(e=>{e.addEventListener("click",()=>{const a=e.dataset.id,d=document.getElementById("detail-"+a),o=e.querySelector(".toggle-icon");if(d){const i=d.classList.contains("hidden");d.classList.toggle("hidden"),o&&(o.textContent=i?"▼":"▶")}})}),document.querySelectorAll(".filter-btn").forEach(e=>{e.addEventListener("click",()=>{document.querySelectorAll(".filter-btn").forEach(a=>{a.className="filter-btn rounded-lg px-4 py-2 text-sm text-zinc-400 bg-zinc-900 border border-zinc-800 hover:bg-zinc-800"}),e.className="filter-btn rounded-lg px-4 py-2 text-sm font-bold bg-amber-700 text-white",p=e.dataset.status,x()})})}document.addEventListener("DOMContentLoaded",async()=>{s=(await $("/api/commands/history?limit=200")).proposals||[],x()});
