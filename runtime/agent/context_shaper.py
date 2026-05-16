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
    query_text: str = "",
    routing_mode: str = "primary",
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
    _hard_extra: dict = {}
    if routing_mode != "primary":
        _hard_extra["routing"] = {"mode": routing_mode}
    hard_facts = _build_hard_facts(extra_json=_hard_extra if _hard_extra else None)

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

    # ── 5b. controlled cognitive recall (FASE 11.0) ──────────────────
    recall_block = ""
    recall_stats = {}
    if query_text and query_text.strip():
        try:
            from runtime.memory.recall_policy import execute_recall
            recall_result = execute_recall(query_text, task_type=task_type)
            if recall_result.get("enabled"):
                recall_block = recall_result["block"]
                recall_stats = {
                    "semantic_recall": {
                        "enabled": True,
                        "collections_used": recall_result["collections_used"],
                        "matches": recall_result["matches"],
                        "avg_score": recall_result["avg_score"],
                        "chars_injected": recall_result["chars_injected"],
                    }
                }
        except ImportError:
            pass

    # Merge with recall stats & rebuild HARD FACTS
    if recall_stats:
        _hard_extra.update(recall_stats)
        hard_facts = _build_hard_facts(extra_json=_hard_extra)

    budget_info = f"BUDGET: budget={budget} chars, used={used}/{budget} ({used/max(budget,1)*100:.0f}%) [HARD_FACTS]"
    parts = [hard_facts, budget_info]
    if recall_block:
        parts.append(recall_block)
    else:
        # Always show recall status, even if empty
        parts.append("[SEMANTIC_RECALL_BEGIN]\n  (no experiences relevantes encontradas)\n[/SEMANTIC_RECALL_END]")
    parts.append("\n\n---\n\n".join(chunks))
    return "\n\n".join(parts)


# ── HARD FACTS generator (anti-hallucination) ──────────────────────────

FORBIDDEN_REFERENCES = [
    "NVIDIA A100", "NVIDIA H100", "Tesla V100", "Tesla T4",
    "BERT", "RoBERTa", "Longformer", "GPT-4", "Claude",
    "AWS", "GCP", "Azure", "Kubernetes", "Terraform",
]

def _build_hard_facts(extra_json: dict | None = None) -> str:
    """Generate structured JSON + text HARD FACTS block from live sources.

    Returns a hybrid block:
      JSON (machine-parseable, authoritative)
      + text detail (human-readable, narrative)

    Cada sección va dentro de try/except para que fallos parciales
    no impidan que el resto del contexto se genere.
    """
    # ── helper: load inference_nodes config ─────────────────────────
    _host_to_node_info: dict[str, dict] = {}
    _node_vram: dict[str, int] = {}
    try:
        import json as _json
        _cfg_file = Path("/opt/ai-lab/config/inference_nodes.json")
        if _cfg_file.exists():
            _cfg = _json.loads(_cfg_file.read_text())
            for _nid, _nd in _cfg.get("nodes", {}).items():
                _host = _nd.get("host", "")
                _host_to_node_info[_host] = _nd
                _node_vram[_host] = _nd.get("vram_gb", 0)
    except Exception:
        pass

    import json as _json

    # ── initialize output parts ────────────────────────────────────
    text_lines: list[str] = []
    _current_mode = "plan"
    try:
        from runtime.modes.mode_manager import current_mode as _cm
        _current_mode = _cm()
    except ImportError:
        pass
    data: dict = {
        "schema_version": "1.0",
        "runtime": {
            "mode": _current_mode,
            "version": "1.1.0",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "uptime_hours": 0.0,
        },
        "gpu_nodes": [],
        "system": {},
        "services": [],
        "docker": {"total": 0, "main": [], "nginx_sites": []},
        "routing": {"total_events": 0, "cognitive_snapshots": 0, "model_performance": {}},
        "health": {},
        "pending_implementations": [
            "routing_confidence",
            "latency_per_request",
            "puppet_ansible",
            "gateway_api_write",
            "rx7900xt_diagnosis",
            "ci_cd_automation",
            "auto_scaling",
        ],
        "sites": [],
    }

    # ── 1. GPU NODES + MODELS PER NODE (combined) ───────────────────
    try:
        import json as _json
        _state_file = Path("/opt/ai-lab/runtime/state/cluster_state.json")
        _discovered = []
        if _state_file.exists():
            _state = _json.loads(_state_file.read_text())
            _discovered = _state.get("discovered_nodes", [])

        if _discovered:
            text_lines.append("GPU NODES:")
            for _n in _discovered:
                _host = _n.get("host", "0.0.0.0")
                _friendly = _host_to_node_info.get(_host, {}).get("name", _n.get("name", "unknown"))
                _vram = _node_vram.get(_host, 0)
                _online = _n.get("online", False)
                _raw_latency = _n.get("latency_ms")
                _latency = f"{_raw_latency:.0f}" if _raw_latency is not None else None
                _models_raw = _n.get("models", [])
                _status_str = "ON" if _online else "OFF"
                _models_str = ", ".join(_models_raw) if _models_raw and _online else "(no models)"
                text_lines.append(f"  {_friendly} ({_host}) {_status_str} {_vram}GB {_latency or '?'}ms models=[{_models_str}]")

                _node_models = []
                if _models_raw and _online:
                    from runtime.models.model_registry import MODEL_REGISTRY
                    for _m in _models_raw:
                        _mcfg = MODEL_REGISTRY.get(_m, {})
                        _node_models.append({
                            "id": _m,
                            "ctx": _mcfg.get("context_window", 0) if isinstance(_mcfg.get("context_window"), int) else 0,
                            "skills": _mcfg.get("skills", []),
                        })
                elif _online:
                    _node_models = [{"id": m, "ctx": 0, "skills": []} for m in _models_raw]

                data["gpu_nodes"].append({
                    "name": _n.get("name", "unknown"),
                    "host": _host,
                    "friendly_name": _friendly,
                    "online": _online,
                    "vram_gb": _vram,
                    "latency_ms": _raw_latency,
                    "models": _node_models,
                })
            text_lines.append("")
    except Exception:
        pass

    # ── 2. SYSTEM RESOURCES (192.168.1.30) ──────────────────────────
    try:
        import subprocess as _sp
        _mem_raw = _sp.run(["free", "-h"], capture_output=True, text=True, timeout=3).stdout.splitlines()
        _mem_parts = _mem_raw[1].split() if len(_mem_raw) >= 2 else ["?", "?", "?", "?", "?", "?", "?"]
        _disk_raw = _sp.run(["df", "-h", "/"], capture_output=True, text=True, timeout=3).stdout.splitlines()
        _disk_parts = _disk_raw[1].split() if len(_disk_raw) >= 2 else ["?", "?", "?", "?", "?", "?"]
        _uptime_raw = _sp.run(["uptime", "-p"], capture_output=True, text=True, timeout=3).stdout.strip()
        _load_raw = Path("/proc/loadavg").read_text().strip().split()
        _load_str = " ".join(_load_raw[:3]) if _load_raw else "?"
        _docker_count = len(_sp.run(["docker", "ps", "-q"], capture_output=True, text=True, timeout=5).stdout.strip().split())

        text_lines.append(f"SYS: {_mem_parts[1]}RAM/{_mem_parts[2]}used/{_mem_parts[6]}avail DISK:{_disk_parts[1]}/{_disk_parts[2]} ({_disk_parts[4]}) DOCKER:{_docker_count} LOAD:{_load_str}")

        def _parse_gib(s: str) -> float:
            s = s.upper().replace(",", ".")
            if "G" in s or "GI" in s:
                return float(s.replace("G", "").replace("I", "").strip())
            if "M" in s or "MI" in s:
                return float(s.replace("M", "").replace("I", "").strip()) / 1024
            return 0.0

        data["system"] = {
            "hostname": "ubuntu-ialab",
            "ram": {
                "total_gib": _parse_gib(_mem_parts[1]),
                "used_gib": _parse_gib(_mem_parts[2]),
                "available_gib": _parse_gib(_mem_parts[6]),
            },
            "disk": {
                "total_g": _parse_gib(_disk_parts[1]),
                "used_g": _parse_gib(_disk_parts[2]),
                "pct": int(_disk_parts[4].replace("%", "")) if len(_disk_parts) >= 5 else 0,
            },
            "docker_containers": _docker_count,
            "load": [float(x) for x in _load_raw[:3]] if len(_load_raw) >= 3 else [],
        }

        # uptime hours
        import re
        _hm = re.findall(r"(\d+)\s+(hour|minute)", _uptime_raw)
        _hours = 0.0
        for val, unit in _hm:
            if "hour" in unit:
                _hours += float(val)
            elif "minute" in unit:
                _hours += float(val) / 60
        data["runtime"]["uptime_hours"] = round(_hours, 1)
    except Exception:
        pass

    # ── 3. DOCKER CONTAINERS ────────────────────────────────────────
    try:
        import subprocess as _sp, json as _json
        _raw = _sp.run(["docker", "ps", "--format", "json"], capture_output=True, text=True, timeout=5)
        _containers_list = []
        for _line in _raw.stdout.strip().splitlines():
            if _line:
                _containers_list.append(_json.loads(_line))

        if _containers_list:
            _nginx_sites = []
            _main_names = []
            for _c in _containers_list:
                _name = _c.get("Names", "?")
                _image = _c.get("Image", "?")
                _ports = _c.get("Ports", "")
                if "nginx:alpine" in _image or "nginx" in _image.lower():
                    _nginx_sites.append(_name)
                else:
                    _main_names.append(_name)
            text_lines.append(f"DOCKER: {len(_containers_list)} running. Main: {', '.join(_main_names[:6])}")
            if _nginx_sites:
                text_lines.append(f"NGINX: {', '.join(_nginx_sites)}")

            data["docker"] = {
                "total": len(_containers_list),
                "main": _main_names,
                "nginx_sites": _nginx_sites,
            }
    except Exception:
        pass

    # ── 4. SYSTEMD SERVICES (live) ──────────────────────────────────
    try:
        import subprocess as _sp
        _raw = _sp.run(["systemctl", "list-units", "--type=service", "ailab-*",
                        "--no-pager", "--no-legend"], capture_output=True, text=True, timeout=3)
        _svcs = []
        for _line in _raw.stdout.strip().splitlines():
            _parts = _line.split()
            if len(_parts) >= 4:
                _name = _parts[0].replace(".service", "")
                _active = _parts[2]
                _sub = _parts[3]
                _svcs.append((_name, _active, _sub))

        if _svcs:
            _svc_strs = [f"{_name}={_active}/{_sub}" for _name, _active, _sub in _svcs]
            text_lines.append(f"SERVICES: {' '.join(_svc_strs)}")
            for _name, _active, _sub in _svcs:
                data["services"].append({
                    "name": _name,
                    "active": _active == "active",
                    "running": _sub == "running",
                })
    except Exception:
        pass

    # ── 5. CLUSTER HEALTH + METRICS (from live API) ─────────────────
    try:
        import requests as _req
        _resp = _req.get("http://127.0.0.1:8084/api/analytics", timeout=3)
        if _resp.status_code == 200:
            _jb = _resp.json()
            _health = _jb.get("health", {})
            _metrics = _jb.get("metrics", {})
            _score = _health.get("score", "?")
            _level = _health.get("level", "?")
            _reasons = _health.get("reasons", [])

            text_lines.append(f"HEALTH: score={_score} level={_level} reqs={_metrics.get('requests_total','?')} "
                         f"streams={_metrics.get('streams_total','?')} "
                         f"nodes={_metrics.get('online_nodes','?')}/{_metrics.get('total_nodes','?')} "
                         f"sessions={_metrics.get('active_sessions','?')}")

            data["health"] = {
                "score": _score if _score != "?" else None,
                "level": _level if _level != "?" else None,
                "reasons": _reasons,
                "requests_total": _metrics.get("requests_total", 0),
                "streams_total": _metrics.get("streams_total", 0),
                "errors_total": _metrics.get("errors_total", 0),
                "online_nodes": _metrics.get("online_nodes", 0),
                "total_nodes": _metrics.get("total_nodes", 0),
                "active_sessions": _active_sessions if _active_sessions != "?" else None,
            }
    except Exception:
        pass

    # ── 6. WATCHDOG ─────────────────────────────────────────────────
    try:
        import requests as _req
        _resp = _req.get("http://127.0.0.1:8084/api/watchdog", timeout=3)
        if _resp.status_code == 200:
            _wd = _resp.json()
            _wd_status = _wd.get("status", "?")
            _checks = _wd.get("checks", {})
            _ok = sum(1 for _v in _checks.values() if _v)
            _total = len(_checks)
            text_lines.append(f"WATCHDOG: {_wd_status} ({_ok}/{_total})")

            if "watchdog" not in data["health"] or not data["health"].get("watchdog"):
                data["health"]["watchdog"] = {}
            data["health"]["watchdog"] = {
                "status": _wd_status,
                "ok": _ok,
                "total": _total,
                "checks": _checks,
            }
    except Exception:
        pass

    # ── 7. MODEL PERFORMANCE (from live API) ────────────────────────
    try:
        import requests as _req
        _resp = _req.get("http://127.0.0.1:8084/api/model-performance", timeout=3)
        if _resp.status_code == 200:
            _perf = _resp.json()
            _perf_strs = []
            for _mid, _mdata in _perf.items():
                if isinstance(_mdata, dict) and "error" not in _mdata:
                    _reqs = _mdata.get("total_requests", 0)
                    _succ = _mdata.get("success_rate", 0)
                    _pi = _mdata.get("performance_index", 0)
                    _perf_strs.append(f"{_mid}:{_reqs}rq/{_succ*100:.0f}%/PI{_pi:.0f}")
                    data["routing"]["model_performance"][_mid] = {
                        "requests": _reqs,
                        "success_rate": _succ,
                        "performance_index": _pi,
                        "failover_rate": _mdata.get("failover_rate", 0),
                    }
            if _perf_strs:
                text_lines.append("MODELS: " + " ".join(_perf_strs))
    except Exception:
        pass

    # ── 8. ROUTING HISTORY ──────────────────────────────────────────
    try:
        _rh = Path("/opt/ai-lab/runtime/state/routing_history.jsonl")
        _ch = Path("/opt/ai-lab/runtime/state/cognitive_history.jsonl")
        _rh_count = len(_rh.read_text().strip().splitlines()) if _rh.exists() else 0
        _ch_count = len(_ch.read_text().strip().splitlines()) if _ch.exists() else 0
        data["routing"]["total_events"] = _rh_count
        data["routing"]["cognitive_snapshots"] = _ch_count
        text_lines.append(f"HISTORY: {_rh_count}routing {_ch_count}cognitive")
    except Exception:
        pass

    # ── 9. SITES ───────────────────────────────────────────────────
    data["sites"] = [
        {"url": "ai-lab.labrazahome.com", "access": "public", "tech": "Cloudflare Pages + Astro"},
        {"url": "blog-ai-lab.labrazahome.com", "access": "private", "tech": "Cloudflare Tunnel + Traefik"},
    ]

    # ── 11. MAINTENANCE ──────────────────────────────────────────────
    try:
        _mf = Path("/opt/ai-lab/runtime/state/maintenance_nodes.json")
        if _mf.exists():
            _mn = _json.loads(_mf.read_text()).get("maintenance", [])
            if _mn:
                text_lines.append(f"MAINTENANCE: {', '.join(_mn)}")
                text_lines.append("")
    except Exception:
        pass

    # ── 12. PENDING IMPLEMENTATIONS ────────────────────────────────
    text_lines.append("PENDING: routing_confidence latency_per_request puppet_ansible gateway_api_write rx7900xt_diagnosis ci_cd_automation auto_scaling")

    # ── Merge extra JSON (FASE 11.0 — semantic_recall stats) ───────
    if extra_json:
        for _ek, _ev in extra_json.items():
            if isinstance(_ev, dict):
                data[_ek] = {**data.get(_ek, {}), **_ev}
            else:
                data[_ek] = _ev

    # ── Serialize JSON block ────────────────────────────────────────
    try:
        _json_str = _json.dumps(data, indent=2, ensure_ascii=False)
    except Exception:
        _json_str = "{}"

    result = (
        "[HARD_FACTS_BEGIN]\n"
        "=== AI-LAB RUNTIME (HARD FACTS) ===\n"
        "\n"
        + _json_str
        + "\n\n"
        + "=== DETALLE (texto) ===\n"
        + "\n".join(text_lines)
        + "\n[HARD_FACTS_END]\n"
    )
    return result
