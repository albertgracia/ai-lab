"""Context Shaper — dynamic, task-aware context assembly.

Replaces the hard 40K-char limit of ``selective_context`` with:
  • token budgeting based on model context window (chars ≈ tokens × 2.8)
  • priority scoring per source file (intent-based relevance)
  • context aging (low-priority files lose relevance over time)
  • optional working-memory digest appended at the end

Designed to plug into ``router_api.py`` via try/except ImportError fallback.
"""

import time
from pathlib import Path

# ── source context files (ordered by default priority) ───────────────────
_SOURCE_FILES = [
    Path("/opt/ai-lab/OPENCODE.md"),
    Path("/opt/ai-lab/config/opencode/AI_LAB_CONTEXT.md"),
    Path("/opt/ai-lab/config/opencode/POLICY.md"),
    Path("/opt/ai-lab/config/opencode/MODEL_STRATEGY.md"),
    Path("/opt/ai-lab/.agent/OPENCODE_PROMPT.md"),
]

# ── intent → source-file relevance weights ──────────────────────────────
# Higher weight = more relevant for that task type.
_INTENT_WEIGHTS: dict[str, dict[str, float]] = {
    "coding":    {"OPENCODE": 0.3, "AI_LAB_CONTEXT": 0.5, "POLICY": 0.1, "MODEL_STRATEGY": 0.6, "OPENCODE_PROMPT": 0.4},
    "reasoning":{"OPENCODE": 0.5, "AI_LAB_CONTEXT": 0.8, "POLICY": 0.3, "MODEL_STRATEGY": 0.4, "OPENCODE_PROMPT": 0.3},
    "fast":      {"OPENCODE": 0.2, "AI_LAB_CONTEXT": 0.3, "POLICY": 0.05, "MODEL_STRATEGY": 0.1, "OPENCODE_PROMPT": 0.2},
    "general":   {"OPENCODE": 0.3, "AI_LAB_CONTEXT": 0.4, "POLICY": 0.2, "MODEL_STRATEGY": 0.3, "OPENCODE_PROMPT": 0.3},
    "architecture": {"OPENCODE": 0.6, "AI_LAB_CONTEXT": 1.0, "POLICY": 0.3, "MODEL_STRATEGY": 0.7, "OPENCODE_PROMPT": 0.4},
    "security":  {"OPENCODE": 0.4, "AI_LAB_CONTEXT": 0.5, "POLICY": 0.8, "MODEL_STRATEGY": 0.3, "OPENCODE_PROMPT": 0.2},
}

# ── limits ───────────────────────────────────────────────────────────────
_CHARS_PER_TOKEN_ESTIMATE = 2.8   # user's adjustment to avoid under-use
_MAX_FILE_CHARS = 12_000
_EFFECTIVE_MAX_CONTEXT = 16384   # LM Studio n_ctx actual


def _file_key(path: Path) -> str:
    """Return a short key for a source file (used in intent weights)."""
    stem = path.stem.upper()
    for kw in ["OPENCODE", "AI_LAB_CONTEXT", "POLICY", "MODEL_STRATEGY", "OPENCODE_PROMPT"]:
        if kw in stem or kw in path.name.upper():
            return kw
    return stem


def _read_source(path: Path) -> str:
    """Read a source file returning its text (or empty string)."""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


# ── public API ───────────────────────────────────────────────────────────

def shape_context(
    task_type: str,
    model_id: str = "",
    working_memory=None,
) -> str:
    """Return a context string optimised for *task_type* and *model_id*.

    Parameters
    ----------
    task_type : str
        e.g. "coding", "reasoning", "fast", "general".
    model_id : str
        Key in MODEL_REGISTRY (used to determine the context budget).
    working_memory : WorkingMemory | None
        Optional per-session state for conversation digest and file aging.

    Returns
    -------
    str
        Assembled context ready to be injected into the system prompt.
    """
    # ── 1. determine token budget ────────────────────────────────────
    _start = time.time()   # cognitive telemetry start

    # ── 0. HARD FACTS block (always first) ───────────────────────────
    hard_facts = _build_hard_facts()

    context_window = 32_000   # default fallback
    try:
        from runtime.models.model_registry import MODEL_REGISTRY
        ctx_cfg = MODEL_REGISTRY.get(model_id, {})
        context_window = ctx_cfg.get("context_window", 32_000)
    except ImportError:
        pass

    # Capped to LM Studio's actual n_ctx (16384) regardless of model registry value
    context_window = min(context_window, _EFFECTIVE_MAX_CONTEXT)
    budget = int(context_window * _CHARS_PER_TOKEN_ESTIMATE)

    # ── 2. load source files ─────────────────────────────────────────
    sources = []
    for sp in _SOURCE_FILES:
        text = _read_source(sp)
        if not text:
            continue
        key = _file_key(sp)
        sources.append({"name": key, "path": str(sp), "text": text, "size": len(text)})

    # ── 3. priority scoring per source ───────────────────────────────
    weights = _INTENT_WEIGHTS.get(task_type, _INTENT_WEIGHTS["general"])

    scored = []
    for s in sources:
        base = weights.get(s["name"], 0.3)

        # context aging: last-access time via working memory
        if working_memory:
            last_access = working_memory.context_aging.get(s["name"], time.time())
            age_hours = max(0, (time.time() - last_access) / 3600.0)
            age_factor = max(0.3, 1.0 - age_hours / 48.0)   # decay over 48 h
            base *= age_factor
            working_memory.context_aging[s["name"]] = time.time()

        scored.append((s, base))

    scored.sort(key=lambda x: x[1], reverse=True)

    # ── 4. fill budget ───────────────────────────────────────────────
    chunks: list[str] = []
    used = 0

    for s, priority in scored:
        if used >= budget:
            break
        remaining = budget - used
        text = s["text"]
        if len(text) > min(_MAX_FILE_CHARS, remaining):
            text = text[: min(_MAX_FILE_CHARS, remaining)] + "\n-- [truncated]"
        chunks.append(f"## {s['name']}\n{text}")
        used += len(text)

    # ── 5. append conversation digest (if working memory available) ───
    if working_memory:
        digest = working_memory.digest()
        if used + len(digest) <= budget:
            chunks.append(f"## Conversation Context\n{digest}")
            used += len(digest)

    # ── cognitive telemetry hook (FASE 8.9) ──────────────────────────
    try:
        from runtime.cognitive.cognitive_metrics import set_metric, store_context_debug, increment
        from runtime.cognitive.cognitive_history import record_snapshot
        elapsed = int((time.time() - _start) * 1000)
        set_metric("avg_shaping_latency_ms", elapsed)
        set_metric("avg_context_size", used)
        set_metric("avg_context_budget_used", round(used / max(budget, 1), 3))
        set_metric("last_files_used", len(chunks))
        set_metric("last_files_names", [s["name"] for s, _ in scored[:len(chunks)]])
        increment("context_shaping_total")
        store_context_debug({
            "task": task_type, "model": model_id, "budget": budget, "used": used,
            "files_used": len(chunks),
            "files_names": [s["name"] for s, _ in scored[:len(chunks)]],
            "digest_size": len(digest) if working_memory else 0,
            "shaping_latency_ms": elapsed,
        })
        record_snapshot(
            task_type=task_type, model=model_id, context_size=used,
            budget_used=round(used / max(budget, 1), 3),
            shaping_latency_ms=elapsed, files_used=len(chunks),
            files_used_names=[s["name"] for s, _ in scored[:len(chunks)]],
            digest_size=len(digest) if working_memory else 0,
            working_memory_used=bool(working_memory),
        )
    except ImportError:
        pass

    budget_info = f"BUDGET: budget={budget} chars, used={used}/{budget} ({used/max(budget,1)*100:.0f}%) [HARD_FACTS]"
    return hard_facts + "\n\n" + budget_info + "\n\n---\n\n" + "\n\n---\n\n".join(chunks)


# ── HARD FACTS generator (anti-hallucination) ──────────────────────────

FORBIDDEN_REFERENCES = [
    "NVIDIA A100", "NVIDIA H100", "Tesla V100", "Tesla T4",
    "BERT", "RoBERTa", "Longformer", "GPT-4", "Claude",
    "AWS", "GCP", "Azure", "Kubernetes", "Terraform",
]

def _build_hard_facts() -> str:
    """Generate the CURRENT AI-LAB RUNTIME block from live data sources.
    
    Cada sección va dentro de try/except para que fallos parciales
    no impidan que el resto del contexto se genere.
    """
    lines = ["[HARD_FACTS_BEGIN]", "=== AI-LAB RUNTIME (HARD FACTS) ===", ""]

    # ── helper: load inference_nodes config ─────────────────────────
    _host_to_node_info: dict[str, dict] = {}
    _node_vram: dict[str, int] = {}
    try:
        import json
        cfg_file = Path("/opt/ai-lab/config/inference_nodes.json")
        if cfg_file.exists():
            cfg = json.loads(cfg_file.read_text())
            for nid, nd in cfg.get("nodes", {}).items():
                host = nd.get("host", "")
                _host_to_node_info[host] = nd
                _node_vram[host] = nd.get("vram_gb", 0)
    except Exception:
        pass

    # ── 1. GPU NODES + MODELS PER NODE (combined) ───────────────────
    try:
        import json
        state_file = Path("/opt/ai-lab/runtime/state/cluster_state.json")
        discovered = []
        if state_file.exists():
            state = json.loads(state_file.read_text())
            discovered = state.get("discovered_nodes", [])

        if discovered:
            lines.append("GPU NODES:")
            for n in discovered:
                host = n.get("host", "0.0.0.0")
                friendly = _host_to_node_info.get(host, {}).get("name", n.get("name", "unknown"))
                vram = _node_vram.get(host, 0)
                status = "ONLINE" if n.get("online") else "OFFLINE"
                raw_latency = n.get("latency_ms")
                latency = f"{raw_latency:.0f}" if raw_latency is not None else "?"
                models = n.get("models", [])
                status_icon = "🟢" if n.get("online") else "🔴"
                lines.append(f"  {status_icon} {friendly} → {host} ({status}, {vram}GB VRAM, {latency}ms)")
                if models and n.get("online"):
                    from runtime.models.model_registry import MODEL_REGISTRY
                    lines.append("     Models:")
                    for m in models:
                        cfg = MODEL_REGISTRY.get(m, {})
                        skills = cfg.get("skills", [])
                        ctx = cfg.get("context_window", "?")
                        lines.append(f"       · {m} ({ctx} ctx, {skills})")
                else:
                    lines.append("     No models available (node offline)")
            lines.append("")
    except Exception:
        pass

    # ── 2. SYSTEM RESOURCES (192.168.1.30) ──────────────────────────
    try:
        import subprocess
        mem_raw = subprocess.run(["free", "-h"], capture_output=True, text=True, timeout=3).stdout.splitlines()
        mem_parts = mem_raw[1].split() if len(mem_raw) >= 2 else ["?", "?", "?", "?", "?", "?", "?"]
        disk_raw = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=3).stdout.splitlines()
        disk_parts = disk_raw[1].split() if len(disk_raw) >= 2 else ["?", "?", "?", "?", "?", "?"]
        uptime_raw = subprocess.run(["uptime", "-p"], capture_output=True, text=True, timeout=3).stdout.strip()
        load_raw = Path("/proc/loadavg").read_text().strip().split()
        load_str = " ".join(load_raw[:3]) if load_raw else "?"
        docker_count = len(subprocess.run(["docker", "ps", "-q"], capture_output=True, text=True, timeout=5).stdout.strip().split())

        lines.append("SYSTEM RESOURCES (192.168.1.30):")
        lines.append(f"  · RAM: {mem_parts[1]} total / {mem_parts[2]} used / {mem_parts[6]} available")
        lines.append(f"  · Disk: {disk_parts[1]} total / {disk_parts[2]} used ({disk_parts[4]})")
        lines.append(f"  · Uptime: {uptime_raw}")
        lines.append(f"  · Load: {load_str}")
        lines.append(f"  · Docker: {docker_count} containers running")
        lines.append("")
    except Exception:
        pass

    # ── 3. DOCKER CONTAINERS ────────────────────────────────────────
    try:
        import subprocess, json
        raw = subprocess.run(["docker", "ps", "--format", "json"], capture_output=True, text=True, timeout=5)
        containers = []
        for line in raw.stdout.strip().splitlines():
            if line:
                containers.append(json.loads(line))

        if containers:
            # Agrupar nginx sites
            nginx_sites = []
            main_containers = []
            for c in containers:
                name = c.get("Names", "?")
                image = c.get("Image", "?")
                ports = c.get("Ports", "")
                status = c.get("Status", "?")
                if "nginx:alpine" in image or "nginx" in image.lower():
                    nginx_sites.append(name)
                else:
                    port_str = ports.split(",")[0].strip() if ports and ports != "" else ""
                    main_containers.append(f"  · {name} ({image}) → {port_str} [{status.split()[0]}]")

            lines.append("DOCKER CONTAINERS:")
            for c in main_containers:
                lines.append(c)
            if nginx_sites:
                lines.append(f"  · {len(nginx_sites)} nginx websites: {', '.join(nginx_sites)}")
            lines.append("")
    except Exception:
        pass

    # ── 4. SYSTEMD SERVICES (live) ──────────────────────────────────
    try:
        import subprocess
        raw = subprocess.run(["systemctl", "list-units", "--type=service", "ailab-*",
                              "--no-pager", "--no-legend"], capture_output=True, text=True, timeout=3)
        services = []
        for line in raw.stdout.strip().splitlines():
            parts = line.split()
            if len(parts) >= 4:
                name = parts[0].replace(".service", "")
                active = parts[2]  # active / inactive / failed
                sub = parts[3]     # running / exited / dead
                services.append((name, active, sub))

        if services:
            lines.append("SYSTEMD SERVICES (live — 192.168.1.30):")
            for name, active, sub in services:
                icon = "🟢" if active == "active" else "🔴"
                lines.append(f"  {icon} {name} → {active} ({sub})")
            lines.append("")
    except Exception:
        pass

    # ── 5. CLUSTER HEALTH + METRICS (from live API) ─────────────────
    try:
        import requests as _req
        resp = _req.get("http://127.0.0.1:8084/api/analytics", timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            health = data.get("health", {})
            metrics = data.get("metrics", {})
            score = health.get("score", "?")
            level = health.get("level", "?")
            reasons = health.get("reasons", [])

            lines.append("CLUSTER HEALTH:")
            lines.append(f"  · Score: {score}/100 ({level})")
            for r in reasons:
                lines.append(f"    → {r}")
            lines.append(f"  · Requests: {metrics.get('requests_total', '?')} total, "
                         f"{metrics.get('streams_total', '?')} streaming, "
                         f"{metrics.get('errors_total', '?')} errors")
            lines.append(f"  · Nodes: {metrics.get('online_nodes', '?')}/{metrics.get('total_nodes', '?')} online")
            lines.append(f"  · Active sessions: {metrics.get('active_sessions', '?')}")
            lines.append("")
    except Exception:
        pass

    # ── 6. WATCHDOG ─────────────────────────────────────────────────
    try:
        import requests as _req
        resp = _req.get("http://127.0.0.1:8084/api/watchdog", timeout=3)
        if resp.status_code == 200:
            wd = resp.json()
            status = wd.get("status", "?")
            checks = wd.get("checks", {})
            ok = sum(1 for v in checks.values() if v)
            total = len(checks)
            lines.append("WATCHDOG:")
            lines.append(f"  · Status: {status} ({ok}/{total} checks pass)")
            for name, passed in checks.items():
                icon = "🟢" if passed else "🔴"
                lines.append(f"  {icon} {name}")
            lines.append("")
    except Exception:
        pass

    # ── 7. MODEL PERFORMANCE (from live API) ────────────────────────
    try:
        import requests as _req
        resp = _req.get("http://127.0.0.1:8084/api/model-performance", timeout=3)
        if resp.status_code == 200:
            perf = resp.json()
            lines.append("MODEL PERFORMANCE:")
            for mid, mdata in perf.items():
                if isinstance(mdata, dict) and "error" not in mdata:
                    reqs = mdata.get("total_requests", 0)
                    succ = mdata.get("success_rate", 0)
                    pi = mdata.get("performance_index", 0)
                    fail = mdata.get("failover_rate", 0)
                    lines.append(f"  · {mid}: {reqs} req, {succ*100:.0f}% success, PI {pi:.0f}, failover {fail*100:.0f}%")
            lines.append("")
    except Exception:
        pass

    # ── 8. ROUTING HISTORY ──────────────────────────────────────────
    try:
        rh = Path("/opt/ai-lab/runtime/state/routing_history.jsonl")
        ch = Path("/opt/ai-lab/runtime/state/cognitive_history.jsonl")
        rh_count = len(rh.read_text().strip().splitlines()) if rh.exists() else 0
        ch_count = len(ch.read_text().strip().splitlines()) if ch.exists() else 0
        lines.append("HISTORY:")
        lines.append(f"  · Routing events: {rh_count}")
        lines.append(f"  · Cognitive snapshots: {ch_count}")
        lines.append("")
    except Exception:
        pass

    # ── 9. ROUTER MODELS ────────────────────────────────────────────
    lines.append("ROUTER MODELS (available via :8083/v1/models):")
    lines.append("  · ailab-router/auto       → automatic capability-based routing")
    lines.append("  · ailab-router/fast       → fast responses (Llama 3.1 8B)")
    lines.append("  · ailab-router/coding     → code generation (Qwen 2.5 Coder)")
    lines.append("  · ailab-router/reasoning  → heavy reasoning (Qwen 2.5 Coder)")
    lines.append("")

    # ── 10. SITES ───────────────────────────────────────────────────
    lines.append("SITES:")
    lines.append("  · ai-lab.labrazahome.com       → Público (Astro portal :4322 via Traefik)")
    lines.append("  · blog-ai-lab.labrazahome.com  → Privado (Cloudflare Tunnel + Traefik)")
    lines.append("")

    # ── 11. MAINTENANCE ──────────────────────────────────────────────
    try:
        mf = Path("/opt/ai-lab/runtime/state/maintenance_nodes.json")
        if mf.exists():
            mn = json.loads(mf.read_text()).get("maintenance", [])
            if mn:
                lines.append(f"MAINTENANCE: {', '.join(mn)}")
                lines.append("")
    except Exception:
        pass

    # ── 12. PENDING IMPLEMENTATIONS ────────────────────────────────
    lines.append("PENDING IMPLEMENTATIONS (funcionalidades no cubiertas aún en runtime):")
    lines.append("  · routing_confidence: PENDIENTE — métrica no implementada en runtime")
    lines.append("  · latencia por request: PENDIENTE — no se mide individualmente")
    lines.append("  · Puppet/Ansible: NO IMPLEMENTADO — infraestructura se gestiona manualmente")
    lines.append("  · Gateway/NAS-N5 Hyper-V: solo lectura SSH (sin API write)")
    lines.append("  · RX7900XT (192.168.1.60): nodo OFFLINE, pendiente diagnosis")
    lines.append("  · CI/CD automático: esqueletos YAML preparados, no activos")
    lines.append("  · Auto-escalado de workers: NO IMPLEMENTADO")
    lines.append("")

    # ── 13. FORBIDDEN REFERENCES ────────────────────────────────────
    lines.append("FORBIDDEN REFERENCES (never mention):")
    lines.append("  " + ", ".join(FORBIDDEN_REFERENCES))
    lines.append("")
    lines.append("[HARD_FACTS_END]")
    lines.append("")
    lines.append("REGLAS:")
    lines.append("1. Los datos entre [HARD_FACTS_BEGIN] y [HARD_FACTS_END] son la fuente de verdad del runtime.")
    lines.append("2. Si un campo no aparece aquí y NO está en PENDING IMPLEMENTATIONS, di '[no disponible en runtime]'.")
    lines.append("3. Si un campo aparece en PENDING IMPLEMENTATIONS, menciónalo como 'pendiente de implementar'.")
    lines.append("4. No infieras valores de campos no listados — el runtime no los expone.")

    return "\n".join(lines)
