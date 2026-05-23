import time
from typing import Any

COGNITIVE_CONTRACT_VERSION = "31C"

SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}
MAX_IMPORTANT_SIGNALS = 5


def build_runtime_cognitive_summary(
    sensor_snapshot: dict[str, Any],
    extra_ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not sensor_snapshot:
        return _fallback_summary("NO DISPONIBLE — sensor snapshot empty")

    all_signals: list[dict[str, Any]] = []
    unavailable: list[str] = []

    gpu_signals = compress_gpu_signals(sensor_snapshot, extra_ctx)
    all_signals.extend(gpu_signals)

    route_signals = compress_route_signals(sensor_snapshot, extra_ctx)
    all_signals.extend(route_signals)

    governance_signals = compress_governance_signals(sensor_snapshot, extra_ctx)
    all_signals.extend(governance_signals)

    storage_signals = compress_storage_signals(sensor_snapshot, extra_ctx)
    all_signals.extend(storage_signals)

    observability_signals = compress_observability_signals(sensor_snapshot, extra_ctx)
    all_signals.extend(observability_signals)

    live_obs_signals = compress_live_observability_signals(sensor_snapshot, extra_ctx)
    all_signals.extend(live_obs_signals)

    validation_signals = compress_validation_signals(sensor_snapshot, extra_ctx)
    all_signals.extend(validation_signals)

    execution_signals = compress_execution_governance_signals(sensor_snapshot, extra_ctx)
    all_signals.extend(execution_signals)

    hardening_signals = compress_hardening_signals(sensor_snapshot, extra_ctx)
    all_signals.extend(hardening_signals)

    topology_signals = compress_topology_signals(sensor_snapshot, extra_ctx)
    all_signals.extend(topology_signals)

    performance_signals = compress_performance_signals(sensor_snapshot, extra_ctx)
    all_signals.extend(performance_signals)

    infrastructure_signals = compress_infrastructure_signals(sensor_snapshot, extra_ctx)
    all_signals.extend(infrastructure_signals)

    semantic_signals = compress_semantic_signals(sensor_snapshot, extra_ctx)
    all_signals.extend(semantic_signals)

    authority_signals = compress_authority_signals(sensor_snapshot, extra_ctx)
    all_signals.extend(authority_signals)

    fastpath_signals = compress_fastpath_signals(sensor_snapshot, extra_ctx)
    all_signals.extend(fastpath_signals)

    incident_signals = compress_incident_signals(sensor_snapshot, extra_ctx)
    all_signals.extend(incident_signals)

    if not all_signals:
        unavailable.append("all_domains")

    important_signals = rank_operational_signals(all_signals)
    summary = build_actionable_summary(important_signals, sensor_snapshot, extra_ctx)
    summary["important_signals"] = important_signals

    # FASE 35D: expose raw signals for operational UX/debug (compact consumers can ignore).
    summary["signals"] = all_signals[:25]

    if unavailable:
        summary["unavailable_data"] = unavailable

    summary["contract_version"] = COGNITIVE_CONTRACT_VERSION
    summary["_runtime_generation"] = "30I-F"

    return summary


def compress_gpu_signals(
    sensor_snapshot: dict[str, Any],
    extra_ctx: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    gpu_summaries = sensor_snapshot.get("gpu_operational_summaries", [])
    if not gpu_summaries:
        return signals

    for gpu in gpu_summaries:
        gpu_id = gpu.get("gpu_id", "?")
        observed_state = gpu.get("observed_state", "unavailable")
        operational_state = gpu.get("operational_state", "inactive")
        freshness = gpu.get("freshness", {})
        confidence = gpu.get("confidence", "low")
        evidence = gpu.get("source_of_truth", ["inventory"])
        inventory_expected = gpu.get("inventory_expected_offline", False)
        metrics = gpu.get("observed_metrics", {}) or {}

        if observed_state == "online" and operational_state == "active":
            temp_c = metrics.get("temperature_c")
            vram_free_gb = metrics.get("vram_free_gb")
            gpu_load = metrics.get("gpu_load_percent")
            power_w = metrics.get("power_watts")

            parts = [f"{gpu_id} active"]
            if temp_c is not None:
                parts.append(f"temp={temp_c}C")
                if temp_c > 80:
                    signals.append({
                        "domain": "gpu", "severity": "warning",
                        "message": f"{gpu_id} temperature {temp_c}C exceeds safe threshold",
                        "evidence": evidence, "confidence": confidence,
                        "freshness": freshness.get("status", "unknown"),
                    })
            if vram_free_gb is not None:
                vram_total = metrics.get("vram_total_gb", 16)
                vram_used = metrics.get("vram_used_gb", vram_total - vram_free_gb)
                parts.append(f"VRAM {vram_used}/{vram_total}GB free={vram_free_gb}GB")
                if vram_free_gb < 1:
                    signals.append({
                        "domain": "gpu", "severity": "warning",
                        "message": f"{gpu_id} VRAM pressure — only {vram_free_gb}GB free",
                        "evidence": evidence, "confidence": confidence,
                        "freshness": freshness.get("status", "unknown"),
                    })
            if gpu_load is not None:
                parts.append(f"load={gpu_load}%")
            if power_w is not None:
                parts.append(f"power={power_w}W")
            parts.append(f"freshness={freshness.get('status', 'unknown')}")
            parts.append(f"confidence={confidence}")
            signals.append({
                "domain": "gpu", "severity": "info",
                "message": ", ".join(parts),
                "evidence": evidence, "confidence": confidence,
                "freshness": freshness.get("status", "unknown"),
            })

        elif observed_state == "expected_offline" and inventory_expected:
            signals.append({
                "domain": "gpu", "severity": "info",
                "message": f"{gpu_id} expected_offline — nodo inventariado apagado, no afecta runtime activo",
                "evidence": evidence, "confidence": confidence,
                "freshness": freshness.get("status", "unavailable"),
            })

        elif observed_state in ("unavailable", "down"):
            if inventory_expected:
                severity = "info"
            else:
                severity = "warning"
            signals.append({
                "domain": "gpu", "severity": severity,
                "message": f"{gpu_id} {observed_state} — no responde",
                "evidence": evidence, "confidence": confidence,
                "freshness": freshness.get("status", "unknown"),
            })

    return signals


def compress_route_signals(
    sensor_snapshot: dict[str, Any],
    extra_ctx: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    observed_data = sensor_snapshot.get("observed_data", {})
    gateway_data = observed_data.get("gateway", {})
    route_families_raw = gateway_data.get("route_families") if isinstance(gateway_data, dict) else None
    derived = sensor_snapshot.get("derived_state", {})
    gateway_derived = derived.get("gateway", {}) if isinstance(derived, dict) else {}

    if isinstance(route_families_raw, list) and route_families_raw:
        active_families = set()
        for entry in route_families_raw:
            if isinstance(entry, dict):
                fam = entry.get("metric", {}).get("family")
                if fam:
                    active_families.add(fam)
        if active_families:
            signals.append({
                "domain": "routing", "severity": "info",
                "message": f"route families activas: {', '.join(sorted(active_families))}",
                "evidence": ["prometheus"], "confidence": "high",
                "freshness": "fresh",
            })
        else:
            signals.append({
                "domain": "routing", "severity": "info",
                "message": "route families registradas pero sin tráfico",
                "evidence": ["prometheus"], "confidence": "medium",
                "freshness": "fresh",
            })
    else:
        signals.append({
            "domain": "routing", "severity": "info",
            "message": "métricas de route families no disponibles",
            "evidence": ["prometheus"], "confidence": "low",
            "freshness": "unknown",
        })

    if isinstance(gateway_derived, dict) and gateway_derived.get("health") == "down":
        signals.append({
            "domain": "routing", "severity": "critical",
            "message": "gateway health is DOWN",
            "evidence": ["prometheus"], "confidence": "high",
            "freshness": "fresh",
        })

    return signals


def compress_governance_signals(
    sensor_snapshot: dict[str, Any],
    extra_ctx: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    evidence_catalog = {}
    if extra_ctx and isinstance(extra_ctx, dict):
        evidence_catalog = extra_ctx.get("evidence_catalog", {}) or {}

    gpu_online = evidence_catalog.get("gpu_online")
    if gpu_online is None:
        signals.append({
            "domain": "governance", "severity": "info",
            "message": "evidence guard activo — datos de GPU no verificados en evidence_catalog",
            "evidence": ["inventory", "code"], "confidence": "medium",
            "freshness": "unknown",
        })
    elif gpu_online is True:
        signals.append({
            "domain": "governance", "severity": "info",
            "message": "evidence guard OK — GPU online verificada en evidence_catalog",
            "evidence": ["inventory", "code"], "confidence": "high",
            "freshness": "fresh",
        })

    prom_targets = evidence_catalog.get("prometheus_targets", {})
    if isinstance(prom_targets, dict):
        unexpected = prom_targets.get("unexpected_down", [])
        if unexpected:
            signals.append({
                "domain": "governance", "severity": "warning",
                "message": f"unexpected down targets detectados: {', '.join(unexpected)}",
                "evidence": ["prometheus"], "confidence": "high",
                "freshness": "fresh",
            })

    governance_blocked = 0
    if extra_ctx and isinstance(extra_ctx, dict):
        governance_blocked = extra_ctx.get("governance_blocked", 0)
    if governance_blocked > 0:
        signals.append({
            "domain": "governance", "severity": "warning",
            "message": f"governance bloqueó {governance_blocked} acciones",
            "evidence": ["code"], "confidence": "high",
            "freshness": "fresh",
        })

    # FASE 33A: governance registry signals
    try:
        from runtime.governance import build_runtime_governance_registry
        _reg = build_runtime_governance_registry(extra_ctx, sensor_snapshot)
        _score = _reg.get("governance_score_info", {})
        _score_val = _score.get("score", 0)
        _level = _score.get("level", "unknown")
        _degraded = _reg.get("degraded_domains", [])

        signals.append({
            "domain": "governance", "severity": "info",
            "message": f"governance score: {_score_val}/100 ({_level}), {len(_degraded)} dominios degradados",
            "evidence": ["runtime_governance_33a"], "confidence": "high",
            "freshness": "fresh",
        })

        _risks = _reg.get("risks", [])
        for r in _risks:
            if r.get("severity") in ("high", "critical"):
                signals.append({
                    "domain": "governance", "severity": "warning",
                    "message": f"governance risk [{r.get('severity')}]: {r.get('description', '')}",
                    "evidence": ["runtime_governance_33a"], "confidence": r.get("confidence", "medium"),
                    "freshness": "fresh",
                })

        _drift = [d for d in _reg.get("drift", []) if d.get("drift_type") != "no_drift"]
        if _drift:
            signals.append({
                "domain": "governance", "severity": "warning",
                "message": f"{len(_drift)} governance drift events detectados",
                "evidence": ["runtime_governance_33a"], "confidence": "high",
                "freshness": "fresh",
            })

    except ImportError:
        signals.append({
            "domain": "governance", "severity": "info",
            "message": "governance registry module no disponible — FASE 33A no integrada",
            "evidence": ["code"], "confidence": "low",
            "freshness": "unavailable",
        })

    return signals


def compress_storage_signals(
    sensor_snapshot: dict[str, Any],
    extra_ctx: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    observed_data = sensor_snapshot.get("observed_data", {})
    system_node = observed_data.get("system_node", {})
    fs_usage = None
    if isinstance(system_node, dict):
        fs_usage = system_node.get("fs_usage_pct")
    if fs_usage is not None:
        msg = f"root disk usage {fs_usage}%"
        severity = "info"
        if fs_usage > 85:
            severity = "warning"
        elif fs_usage > 95:
            severity = "critical"
        signals.append({
            "domain": "storage", "severity": severity,
            "message": msg,
            "evidence": ["prometheus"], "confidence": "high",
            "freshness": "fresh",
        })
    else:
        signals.append({
            "domain": "storage", "severity": "info",
            "message": "uso de disco raíz NO DISPONIBLE",
            "evidence": ["prometheus"], "confidence": "low",
            "freshness": "unknown",
        })

    if extra_ctx and isinstance(extra_ctx, dict):
        archive_state = extra_ctx.get("storage_archive_state")
        if archive_state:
            signals.append({
                "domain": "storage", "severity": "info",
                "message": f"archive: {archive_state}",
                "evidence": ["code"], "confidence": "high",
                "freshness": "fresh",
            })
        rec_risk = extra_ctx.get("recursive_backup_risk")
        if rec_risk:
            signals.append({
                "domain": "storage", "severity": "warning",
                "message": "snapshot recursion risk detected — ejecutar archive relocation taxonomy",
                "evidence": ["code"], "confidence": "high",
                "freshness": "fresh",
            })

    return signals


def compress_observability_signals(
    sensor_snapshot: dict[str, Any],
    extra_ctx: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    observed_count = sensor_snapshot.get("observed_sources_count", 0)
    missing_count = sensor_snapshot.get("missing_sources_count", 0)
    domain_confidence = sensor_snapshot.get("domain_confidence", {}) or {}
    freshness = sensor_snapshot.get("freshness", {}) or {}
    stale = sensor_snapshot.get("stale_sources")
    if stale is None and extra_ctx and isinstance(extra_ctx, dict):
        stale = extra_ctx.get("stale_sources")
    stale = stale or []

    total = observed_count + missing_count
    if total > 0:
        ratio = observed_count / total
        freshness_status = "fresh"
        if any("stale" in str(v).lower() or "expired" in str(v).lower() for v in freshness.values()):
            freshness_status = "stale"
        elif not freshness:
            freshness_status = "unknown"

        confidence_values = set(domain_confidence.values())
        overall_conf = "high"
        if "low" in confidence_values:
            overall_conf = "low"
        elif "medium" in confidence_values:
            overall_conf = "medium"

        msg_parts = [
            f"Prometheus: {observed_count}/{total} sources up",
        ]
        if stale:
            msg_parts.append(f"stale: {', '.join(stale[:3])}")
        msg_parts.append(f"confidence={overall_conf}")
        msg_parts.append(f"freshness={freshness_status}")

        signals.append({
            "domain": "observability", "severity": "info",
            "message": ", ".join(msg_parts),
            "evidence": ["prometheus", "code"], "confidence": overall_conf,
            "freshness": freshness_status,
        })

        if ratio < 0.5:
            signals.append({
                "domain": "observability", "severity": "warning",
                "message": f"Prometheus: menos del 50% de fuentes accesibles ({observed_count}/{total})",
                "evidence": ["prometheus"], "confidence": "low",
                "freshness": "stale",
            })
        if "low" in confidence_values:
            signals.append({
                "domain": "observability", "severity": "warning",
                "message": "confianza baja en uno o más dominios — verificar conectividad Prometheus",
                "evidence": ["prometheus", "code"], "confidence": "low",
                "freshness": freshness_status,
            })
    else:
        signals.append({
            "domain": "observability", "severity": "warning",
            "message": "Prometheus: ninguna fuente de datos accesible",
            "evidence": ["prometheus"], "confidence": "low",
            "freshness": "unavailable",
        })

    # FASE OBS-31A: Observability source-of-truth audit signal
    obs_audit = sensor_snapshot.get("observability_audit")
    if obs_audit and isinstance(obs_audit, dict):
        targets = obs_audit.get("prometheus_targets", {})
        healthy = targets.get("healthy", 0)
        total = targets.get("total", 0)
        alignment = obs_audit.get("critical_targets_alignment_pct", 0.0)
        audit_confidence = "high"
        audit_severity = "info"

        if alignment < 100.0 or (total > 0 and healthy < total):
            if alignment < 50.0:
                audit_confidence = "low"
                audit_severity = "warning"
            else:
                audit_confidence = "medium"

        signals.append({
            "domain": "observability",
            "severity": audit_severity,
            "message": (
                f"OBS-31A audit: {healthy}/{total} targets healthy, "
                f"{alignment}% critical alignment"
            ),
            "evidence": ["observability_audit", "code"],
            "confidence": audit_confidence,
            "freshness": "fresh",
        })

    return signals


def compress_hardening_signals(
    sensor_snapshot: dict[str, Any],
    extra_ctx: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    extra_ctx = extra_ctx or {}

    try:
        from runtime.hardening import build_runtime_hardening_report
        rep = build_runtime_hardening_report(sensor_snapshot=sensor_snapshot, extra_ctx=extra_ctx)
        score = float(rep.get("hardening_score", 0.0) or 0.0)
        level = rep.get("hardening_level", "unknown")
        esc = rep.get("escalation", {}) or {}
        esc_state = esc.get("escalation_state", "unknown")
        cont = rep.get("containment", {}) or {}
        containment = bool(cont.get("containment_mode"))
        watchdogs = rep.get("watchdogs", []) or []
        critical = [w.get("watchdog") for w in watchdogs if w.get("state") == "critical"]
        degraded = [w.get("watchdog") for w in watchdogs if w.get("state") == "degraded"]

        if containment:
            signals.append({
                "domain": "hardening",
                "severity": "critical",
                "message": "containment_mode active (operational containment)",
                "evidence": ["runtime_hardening_34a"],
            })
        elif esc_state in ("critical", "degraded"):
            signals.append({
                "domain": "hardening",
                "severity": "warning" if esc_state == "degraded" else "critical",
                "message": f"hardening escalation_state={esc_state}",
                "evidence": ["runtime_hardening_34a"],
            })

        if critical:
            signals.append({
                "domain": "hardening",
                "severity": "critical",
                "message": f"critical watchdogs: {', '.join(sorted([c for c in critical if c])[:3])}",
                "evidence": ["runtime_hardening_34a"],
            })
        elif degraded and score < 85:
            signals.append({
                "domain": "hardening",
                "severity": "warning",
                "message": f"degraded watchdogs: {', '.join(sorted([d for d in degraded if d])[:3])}",
                "evidence": ["runtime_hardening_34a"],
            })

        if score < 65:
            signals.append({
                "domain": "hardening",
                "severity": "warning" if score >= 40 else "critical",
                "message": f"hardening score {score}/100 ({level})",
                "evidence": ["runtime_hardening_34a"],
            })

    except Exception:
        # Unknown > inventado.
        return signals

    return signals


def compress_topology_signals(
    sensor_snapshot: dict[str, Any],
    extra_ctx: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    try:
        from runtime.topology import (
            build_runtime_topology,
            build_dependency_graph,
            build_authority_graph,
            detect_topology_drift,
            calculate_topology_confidence,
        )
        _topo = build_runtime_topology(sensor_snapshot, extra_ctx)
        _dep = build_dependency_graph(sensor_snapshot, extra_ctx)
        _auth = build_authority_graph(sensor_snapshot, extra_ctx)
        _drift = detect_topology_drift(sensor_snapshot, extra_ctx)
        _conf = calculate_topology_confidence(sensor_snapshot, extra_ctx)

        nodes = _topo.get("nodes", [])
        edges = _topo.get("edges", [])
        degraded_paths = _topo.get("degraded_paths", [])
        active_nodes = sum(1 for n in nodes if n.get("active"))
        inventory_nodes = sum(1 for n in nodes if n.get("inventory_only"))
        total_deps = _dep.get("total_dependencies", 0)
        total_chains = _auth.get("total_chains", 0)
        conf_score = _conf.get("overall_score", 0)

        parts = [
            f"topology: {len(nodes)} nodos, {len(edges)} aristas, {active_nodes} activos",
            f"{inventory_nodes} inventario, {total_deps} dependencias, {total_chains} cadenas autoridad",
            f"confianza topologica: {conf_score}%",
        ]
        signals.append({
            "domain": "topology", "severity": "info",
            "message": ", ".join(parts),
            "evidence": ["runtime_topology_31d"], "confidence": "high" if conf_score >= 80 else "medium",
            "freshness": "fresh",
        })

        if degraded_paths:
            signals.append({
                "domain": "topology", "severity": "warning",
                "message": f"{len(degraded_paths)} rutas degradadas en topologia",
                "evidence": ["runtime_topology_31d"], "confidence": "high",
                "freshness": "fresh",
            })

        if _drift:
            _drift_severity = "warning"
            if any(d.get("severity") == "medium" for d in _drift):
                _drift_severity = "warning"
            signals.append({
                "domain": "topology", "severity": _drift_severity,
                "message": f"{len(_drift)} desviaciones topologicas detectadas",
                "evidence": ["runtime_topology_31d"], "confidence": "high",
                "freshness": "fresh",
            })

        if conf_score < 50:
            signals.append({
                "domain": "topology", "severity": "warning",
                "message": f"confianza topologica baja ({conf_score}%) — verificar consistencia de relaciones observadas",
                "evidence": ["runtime_topology_31d"], "confidence": "low",
                "freshness": "fresh",
            })

    except ImportError:
        signals.append({
            "domain": "topology", "severity": "info",
            "message": "topology module no disponible — FASE 31D no integrada",
            "evidence": ["code"], "confidence": "low",
            "freshness": "unavailable",
        })

    return signals


def compress_performance_signals(
    sensor_snapshot: dict[str, Any],
    extra_ctx: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """FASE 34C: surface runtime friction/latency signals (non-invasive)."""
    signals: list[dict[str, Any]] = []
    extra_ctx = extra_ctx or {}
    try:
        from runtime.performance import profile_governance_latency, profile_validation_latency, get_performance_cache_state
        g = profile_governance_latency(extra_ctx=extra_ctx, sensor_snapshot=sensor_snapshot)
        v = profile_validation_latency(extra_ctx=extra_ctx, sensor_snapshot=sensor_snapshot)
        cache = get_performance_cache_state()

        gov_ms = float(g.get("governance_ms", 0.0) or 0.0)
        val_ms = float(v.get("validation_ms", 0.0) or 0.0)

        sev = "info"
        if bool(g.get("friction_detected")) or bool(v.get("overhead_detected")):
            sev = "warning"

        signals.append({
            "domain": "performance",
            "severity": sev,
            "message": f"perf: governance_ms={gov_ms} validation_ms={val_ms} cache_hits={cache.get('cache_hits', 0)} cache_misses={cache.get('cache_misses', 0)}",
            "evidence": ["runtime_performance_34c"],
            "confidence": "high",
            "freshness": "fresh",
        })
    except Exception:
        # Unknown > inventado.
        return signals
    return signals


def compress_infrastructure_signals(
    sensor_snapshot: dict[str, Any],
    extra_ctx: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """FASE 35A: surface infrastructure identity/authority-root state."""
    signals: list[dict[str, Any]] = []
    extra_ctx = extra_ctx or {}
    try:
        from runtime.infrastructure import build_infrastructure_identity_registry
        reg = build_infrastructure_identity_registry(extra_ctx=extra_ctx)
        score = float(reg.get("score", 0.0) or 0.0)
        roots = reg.get("authority_roots", []) or []
        inv = reg.get("inventory", {}) or {}
        unknown = inv.get("unknown_nodes", []) or []
        orphans = inv.get("discoverable_nodes", []) or []

        sev = "info"
        if "192.168.1.40" not in roots or score < 65:
            sev = "warning"

        msg = f"infra: score={score} prometheus_root={'yes' if '192.168.1.40' in roots else 'no'} unknown={len(unknown)} orphans={len(orphans)}"
        signals.append({
            "domain": "infrastructure",
            "severity": sev,
            "message": msg,
            "evidence": ["infrastructure_registry_35a"],
            "confidence": "high" if score >= 85 else "medium" if score >= 65 else "low",
            "freshness": "fresh",
        })
    except Exception:
        return signals
    return signals


def compress_semantic_signals(
    sensor_snapshot: dict[str, Any],
    extra_ctx: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """FASE 35B: semantic contamination + hygiene signals."""
    signals: list[dict[str, Any]] = []
    extra_ctx = extra_ctx or {}
    try:
        from runtime.semantic import build_semantic_integrity_report
        sem = build_semantic_integrity_report(extra_ctx=extra_ctx)
        score = float(sem.get("semantic_integrity_score", 0.0) or 0.0)
        sev = "info" if score >= 85 else "warning" if score >= 65 else "critical"
        msg = (
            f"semantic: score={score} legacy={sem.get('legacy_leakage_total', 0)} "
            f"phantom={sem.get('phantom_entities_total', 0)} unknown_operational={sem.get('unknown_operational_entities_total', 0)}"
        )
        signals.append({
            "domain": "semantic",
            "severity": sev,
            "message": msg,
            "evidence": ["semantic_sterilization_35b"],
            "confidence": "high",
            "freshness": "fresh",
        })
    except Exception:
        return signals
    return signals


def compress_authority_signals(
    sensor_snapshot: dict[str, Any],
    extra_ctx: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """FASE 35C: authority freshness/gaps signals."""
    signals: list[dict[str, Any]] = []
    extra_ctx = extra_ctx or {}
    try:
        from runtime.authority import build_authority_cognition_summary
        summ = build_authority_cognition_summary(extra_ctx=extra_ctx)
        fresh_score = float(summ.get("authority_freshness_score", 0.0) or 0.0)
        gaps = int(summ.get("authority_gaps_total", 0) or 0)
        sev = "info" if fresh_score >= 80 and gaps == 0 else "warning" if fresh_score >= 50 else "critical"
        signals.append({
            "domain": "authority",
            "severity": sev,
            "message": f"authority: freshness_score={fresh_score} gaps={gaps} stale={summ.get('stale_authority_total', 0)}",
            "evidence": ["authority_35c"],
            "confidence": "high" if fresh_score >= 80 else "medium" if fresh_score >= 50 else "low",
            "freshness": "fresh",
        })
    except Exception:
        return signals
    return signals


def compress_fastpath_signals(
    sensor_snapshot: dict[str, Any],
    extra_ctx: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """FASE 35D: operational fast-path UX pressure signals."""
    signals: list[dict[str, Any]] = []
    extra_ctx = extra_ctx or {}
    try:
        from runtime.fastpath import build_fastpath_response
        fp = build_fastpath_response("estado runtime", extra_ctx={"enable_network": False}, sensor_snapshot=sensor_snapshot or {}, verbosity="operational")
        q = float(fp.get("response_quality_score", 0.0) or 0.0)
        deep = bool((fp.get("routing", {}) or {}).get("deep_path"))
        auth = fp.get("authority", {}) or {}
        auth_fresh = (auth.get("freshness", {}) or {}).get("status", "unknown") if isinstance(auth, dict) else "unknown"
        # If authority is unavailable, surface fast-path as warning (operational impact).
        if auth_fresh in ("partial", "unavailable"):
            sev = "warning"
        else:
            sev = "info" if q >= 80 and not deep else "warning" if q >= 55 else "critical"
        signals.append({
            "domain": "fastpath",
            "severity": sev,
            "message": f"fastpath: quality={q} deep_path={deep} authority={auth_fresh}",
            "evidence": ["fastpath_35d"],
            "confidence": "high" if q >= 80 else "medium" if q >= 55 else "low",
            "freshness": "fresh",
        })
    except Exception:
        return signals
    return signals


def compress_live_observability_signals(
    sensor_snapshot: dict[str, Any],
    extra_ctx: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Signals derived from OBS-34B live diagnostics.

    Network calls are disabled by default unless AI_LAB_ENABLE_LIVE_OBSERVABILITY_NETWORK=true.
    """
    _ = sensor_snapshot
    extra_ctx = extra_ctx or {}
    signals: list[dict[str, Any]] = []

    try:
        from runtime.observability import run_live_observability_diagnostics
        rep = run_live_observability_diagnostics(extra_ctx=extra_ctx)
        score = rep.get("score", {}) or {}
        incidents = rep.get("incidents", {}) or {}
        exporters = rep.get("exporters", {}) or {}
        st = rep.get("authority_staleness", {}) or {}

        lvl = score.get("live_observability_level", "unknown")
        val = float(score.get("live_observability_score", 0.0) or 0.0)
        if lvl in ("critical", "low") or val < 65:
            signals.append({
                "domain": "observability",
                "severity": "critical" if val < 40 else "warning",
                "message": f"live observability score {val}/100 ({lvl})",
                "evidence": ["prometheus_authority", "obs-34b"],
            })

        if st.get("authority_freshness") in ("stale", "degraded"):
            signals.append({
                "domain": "observability",
                "severity": "warning",
                "message": f"authority freshness={st.get('authority_freshness')} stale={st.get('authority_staleness_total', 0)} down={st.get('scrape_down_total', 0)}",
                "evidence": ["prometheus_authority"],
            })

        summ = exporters.get("summary", {}) or {}
        flap = (summ.get("flapping", {}) or {}).get("flapping_total", 0) or 0
        if int(flap) > 0:
            signals.append({
                "domain": "observability",
                "severity": "warning",
                "message": f"exporter flapping detected: {flap}",
                "evidence": ["obs-34b"],
            })

        highest = incidents.get("highest_severity", "info")
        if highest in ("critical", "high"):
            signals.append({
                "domain": "observability",
                "severity": "critical" if highest == "critical" else "warning",
                "message": f"observability incidents active (highest={highest})",
                "evidence": ["obs-34b"],
            })

    except Exception:
        return signals

    return signals


def compress_validation_signals(
    sensor_snapshot: dict[str, Any],
    extra_ctx: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """FASE 33B: Surface pre-pilot validation state in cognitive summary."""
    signals: list[dict[str, Any]] = []
    try:
        from runtime.validation import build_runtime_validation_report
        report = build_runtime_validation_report(sensor_snapshot=sensor_snapshot, extra_ctx=extra_ctx)
        score = report.get("validation_score", 0.0)
        level = report.get("validation_level", "unknown")
        failures = report.get("failures", []) or []
        pilot = report.get("pilot_readiness", {}) or {}
        readiness = pilot.get("pilot_readiness_score", 0.0)
        readiness_level = pilot.get("readiness_level", "unknown")

        severity = "info"
        if readiness_level == "not_ready" or any(f.get("blocking") for f in failures):
            severity = "warning"

        signals.append({
            "domain": "validation",
            "severity": severity,
            "message": f"pre-pilot validation: score={score}/100 ({level}), readiness={readiness}/100 ({readiness_level}), failures={len(failures)}",
            "evidence": ["validation_framework_33b"],
            "confidence": "high" if score >= 85 else "medium" if score >= 65 else "low",
            "freshness": "fresh",
        })

        blocking_inv = pilot.get("blocking_invariants", []) or []
        if blocking_inv:
            signals.append({
                "domain": "validation",
                "severity": "warning",
                "message": f"blocking invariants: {', '.join(blocking_inv[:3])}",
                "evidence": ["validation_framework_33b"],
                "confidence": "high",
                "freshness": "fresh",
            })

        failed_gates = pilot.get("failed_gates", []) or []
        if failed_gates:
            signals.append({
                "domain": "validation",
                "severity": "warning",
                "message": f"failed gates: {', '.join(failed_gates[:3])}",
                "evidence": ["validation_framework_33b"],
                "confidence": "high",
                "freshness": "fresh",
            })

    except ImportError:
        signals.append({
            "domain": "validation",
            "severity": "info",
            "message": "validation framework no disponible — FASE 33B no integrada",
            "evidence": ["code"],
            "confidence": "low",
            "freshness": "unavailable",
        })
    except Exception as exc:
        signals.append({
            "domain": "validation",
            "severity": "warning",
            "message": f"validation framework error: {exc}",
            "evidence": ["validation_framework_33b"],
            "confidence": "low",
            "freshness": "unknown",
        })

    return signals


def compress_execution_governance_signals(
    sensor_snapshot: dict[str, Any],
    extra_ctx: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """FASE 28.4: Tool/Plan/GC governance signals."""
    signals: list[dict[str, Any]] = []

    try:
        from runtime.tools import calculate_tool_governance_score, detect_invalid_tool_contracts, detect_orphan_tools
        tool_gov = calculate_tool_governance_score()
        invalid = detect_invalid_tool_contracts()
        orphan_tools = detect_orphan_tools()
        score = tool_gov.get("tool_governance_score", 0.0)
        severity = "info" if score >= 85 and not invalid else "warning" if invalid else "info"
        signals.append({
            "domain": "execution",
            "severity": severity,
            "message": f"tool governance: score={score}/100 invalid={len(invalid)} orphan_tools={len(orphan_tools)}",
            "evidence": ["tool_registry_28_4"],
            "confidence": "high" if score >= 85 else "medium" if score >= 65 else "low",
            "freshness": "fresh",
        })
        if invalid:
            signals.append({
                "domain": "execution",
                "severity": "warning",
                "message": f"invalid tool contracts detected: {len(invalid)}",
                "evidence": ["tool_registry_28_4"],
                "confidence": "high",
                "freshness": "fresh",
            })
    except Exception:
        pass

    try:
        from runtime.plans.plan_registry import detect_orphan_plans
        orphan_plans = detect_orphan_plans()
        if orphan_plans:
            signals.append({
                "domain": "execution",
                "severity": "warning",
                "message": f"orphan plans detected: {len(orphan_plans)}",
                "evidence": ["plan_registry_28_4"],
                "confidence": "high",
                "freshness": "fresh",
            })
    except Exception:
        pass

    try:
        from runtime.gc.crossplan_gc import (
            build_gc_inventory,
            protect_governance_artifacts,
            protect_active_validation_artifacts,
            protect_runtime_authority_artifacts,
            detect_gc_candidates,
            calculate_gc_safety_score,
        )
        inv = build_gc_inventory()
        inv = protect_governance_artifacts(inv)
        inv = protect_active_validation_artifacts(inv)
        inv = protect_runtime_authority_artifacts(inv)
        cand = detect_gc_candidates(inv)
        safety = calculate_gc_safety_score(inv, cand)
        score = safety.get("gc_safety_score", 0.0)
        level = safety.get("gc_safety_level", "unknown")
        sev = "info" if level in ("high", "medium") else "warning"
        signals.append({
            "domain": "execution",
            "severity": sev,
            "message": f"gc: safety={score}/100 ({level}) candidates={len(cand)} dry_run_only",
            "evidence": ["crossplan_gc_28_4"],
            "confidence": "high" if score >= 85 else "medium" if score >= 65 else "low",
            "freshness": "fresh",
        })
    except Exception:
        pass

    if not signals:
        signals.append({
            "domain": "execution",
            "severity": "info",
            "message": "execution governance signals NO DISPONIBLE",
            "evidence": ["code"],
            "confidence": "low",
            "freshness": "unavailable",
        })

    return signals


def rank_operational_signals(signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not signals:
        return []
    ranked = sorted(signals, key=lambda s: SEVERITY_ORDER.get(s.get("severity", "info"), 99))
    critical_or_warning = [s for s in ranked if s.get("severity") in ("critical", "warning")]
    info = [s for s in ranked if s.get("severity") == "info"]
    result = critical_or_warning + info
    return result[:MAX_IMPORTANT_SIGNALS]


def build_actionable_summary(
    important_signals: list[dict[str, Any]],
    sensor_snapshot: dict[str, Any],
    extra_ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    severities = {s.get("severity", "info") for s in important_signals}
    domain_confs = sensor_snapshot.get("domain_confidence", {}) or {}
    freshness = sensor_snapshot.get("freshness", {}) or {}

    if "critical" in severities:
        overall_state = "critical"
    elif "warning" in severities:
        overall_state = "degraded"
    elif severities == {"info"} and important_signals:
        overall_state = "healthy"
    else:
        overall_state = "unknown"

    topology_mode = sensor_snapshot.get("topology", {}).get("mode", "unknown")
    if topology_mode == "degraded_single_gpu" and overall_state == "healthy":
        overall_state = "healthy_degraded"

    expected_offline = sensor_snapshot.get("expected_offline", [])
    unexpected_down = sensor_snapshot.get("unexpected_down", [])

    # FASE 31B: Runtime maturity context
    runtime_maturity = None
    try:
        from runtime.semantics.runtime_maturity import calculate_runtime_maturity
        runtime_maturity = calculate_runtime_maturity(sensor_snapshot, extra_ctx)
    except ImportError:
        pass

    summary_parts = []
    if overall_state == "critical":
        summary_parts.append("Runtime en estado CRITICO")
    elif overall_state == "degraded":
        summary_parts.append("Runtime degradado")
    elif overall_state == "healthy_degraded":
        summary_parts.append("Runtime estable en modo degraded_single_gpu")
    elif overall_state == "healthy":
        summary_parts.append("Runtime estable")
    else:
        summary_parts.append("Estado del runtime desconocido")

    active_gpus = sensor_snapshot.get("topology", {}).get("active_gpus", [])
    inventory_gpus = sensor_snapshot.get("topology", {}).get("inventory_gpus", [])
    n_active = len(active_gpus)
    n_inventory = len(inventory_gpus)
    gpu_summary = f"{n_active} GPU activa"
    if n_inventory:
        gpu_summary += f" + {n_inventory} inventariada"
    summary_parts.append(gpu_summary)

    if unexpected_down:
        summary_parts.append(f"{len(unexpected_down)} unexpected down")
    if expected_offline:
        summary_parts.append("RX7900XT expected_offline no afecta runtime activo")

    # FASE 31B: Add degradation context
    if runtime_maturity:
        degraded = runtime_maturity.get("degraded_domains", [])
        unknown = runtime_maturity.get("unknown_domains", [])
        if degraded:
            summary_parts.append(f"degradado: {', '.join(degraded[:3])}")
        if unknown:
            summary_parts.append(f"desconocido: {', '.join(unknown[:2])}")

    summary_text = ", ".join(set(summary_parts))

    risks: list[str] = []
    for s in important_signals:
        if s.get("severity") in ("critical", "warning"):
            risks.append(s.get("message", ""))
    # FASE 31B: Add maturity degradation reasons to risks
    if runtime_maturity:
        for r in runtime_maturity.get("degradation_reason", []):
            if r not in risks:
                risks.append(f"[maturity] {r}")
    if not risks:
        risks.append("ningún riesgo activo detectado")

    recommendations: list[str] = []
    has_gpu_warning = any(
        s.get("domain") == "gpu" and s.get("severity") == "warning"
        for s in important_signals
    )
    has_vram_pressure = any(
        "VRAM pressure" in s.get("message", "")
        for s in important_signals
    )

    if has_vram_pressure:
        recommendations.append("revisar VRAM — considerar reducir parallel requests o liberar modelos no críticos")
    if has_gpu_warning and not has_vram_pressure:
        recommendations.append("verificar métricas GPU — temperatura/carga anómala detectada")
    if "critical" in severities:
        recommendations.append("intervención inmediata requerida — revisar señales críticas")

    has_prometheus_warning = any(
        s.get("domain") == "observability" and s.get("severity") == "warning"
        for s in important_signals
    )
    if has_prometheus_warning:
        recommendations.append("verificar conectividad Prometheus antes de confiar en métricas live")

    has_storage_warning = any(
        s.get("domain") == "storage" and s.get("severity") == "warning"
        for s in important_signals
    )
    if has_storage_warning:
        recommendations.append("revisar uso de disco — riesgo de saturación de storage")

    has_recursion_risk = any(
        "recursion" in s.get("message", "").lower()
        for s in important_signals
    )
    if has_recursion_risk:
        recommendations.append("ejecutar archive relocation taxonomy para resolver recursion de snapshots")

    gpu_info_signals = [s for s in important_signals if s.get("domain") == "gpu" and s.get("severity") == "info"]
    rx7900xt_expected = any(
        "expected_offline" in s.get("message", "")
        for s in gpu_info_signals
    )
    if rx7900xt_expected and not has_gpu_warning and "critical" not in severities:
        recommendations.append("continuar validación de sensor fusion antes de Multi-GPU")

    # FASE 31B: Confidence-aware recommendations
    if runtime_maturity:
        mat_conf = runtime_maturity.get("confidence", "unknown")
        mat_state = runtime_maturity.get("runtime_state", "unknown")
        if mat_conf == "low" and mat_state in ("degraded", "critical", "stale"):
            if "verificar conectividad Prometheus" not in recommendations:
                recommendations.append("confianza baja - verificar fuentes de datos antes de operaciones")
        if runtime_maturity.get("operational_impact") in ("high", "critical"):
            if "intervención inmediata" not in str(recommendations):
                recommendations.append("impacto operacional alto - revisar dominios degradados")
        if mat_state == "partially_observed":
            recommendations.append("observabilidad parcial - algunas fuentes no accesibles")
        if runtime_maturity.get("uncertainty_level") == "stale_evidence":
            if "datos stale - considerar refresh de sensores" not in recommendations:
                recommendations.append("datos stale - considerar refresh de sensores")

    # FASE 31D: topology-aware recommendations
    _has_topology_warning = any(
        s.get("domain") == "topology" and s.get("severity") == "warning"
        for s in important_signals
    )
    if _has_topology_warning:
        recommendations.append("revisar topologia — rutas degradadas o desviaciones detectadas")

    if not recommendations:
        recommendations.append("ninguna acción necesaria — runtime estable")

    confidence_values = {s.get("confidence", "low") for s in important_signals}
    if "low" in confidence_values:
        overall_confidence = "low"
    elif "medium" in confidence_values:
        overall_confidence = "medium"
    else:
        overall_confidence = "high"

    freshness_statuses = {s.get("freshness", "unknown") for s in important_signals}
    if "expired" in freshness_statuses:
        overall_freshness = "expired"
    elif "stale" in freshness_statuses:
        overall_freshness = "stale"
    elif "fresh" in freshness_statuses:
        overall_freshness = "fresh"
    elif "unavailable" in freshness_statuses:
        overall_freshness = "unavailable"
    else:
        overall_freshness = "mixed"

    result = {
        "overall_state": overall_state,
        "topology_mode": topology_mode,
        "summary": summary_text,
        "risks": risks,
        "recommended_actions": recommendations,
        "unavailable_data": [],
        "confidence": overall_confidence,
        "freshness": overall_freshness,
    }

    # FASE 31B: Inject runtime maturity context
    if runtime_maturity:
        result["runtime_maturity"] = {
            "runtime_state": runtime_maturity.get("runtime_state"),
            "maturity_score": runtime_maturity.get("maturity_score"),
            "confidence": runtime_maturity.get("confidence"),
            "uncertainty_level": runtime_maturity.get("uncertainty_level"),
            "operational_impact": runtime_maturity.get("operational_impact"),
            "degraded_domains": runtime_maturity.get("degraded_domains", []),
        }

    return result


def compress_incident_signals(
    sensor_snapshot: dict[str, Any],
    extra_ctx: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """FASE 36A: surface incident intelligence signals."""
    signals: list[dict[str, Any]] = []
    extra_ctx = extra_ctx or {}
    _ = sensor_snapshot

    try:
        from runtime.incidents import build_incident_intelligence_report
        rep = build_incident_intelligence_report(extra_ctx=extra_ctx, sensor_snapshot={})
        count = int(rep.get("incident_count", 0) or 0)
        highest = rep.get("highest_severity", "info")
        affected = rep.get("affected_domains", []) or []

        if count > 0:
            sev = "critical" if highest in ("critical", "high") else "warning" if highest == "medium" else "info"
            msg = f"incidents: {count} active, highest={highest}, domains={', '.join(affected[:4])}"
            signals.append({
                "domain": "incidents",
                "severity": sev,
                "message": msg,
                "evidence": ["incident_intelligence_36a"],
                "confidence": "high" if count > 0 else "medium",
                "freshness": "fresh",
            })
        else:
            signals.append({
                "domain": "incidents",
                "severity": "info",
                "message": "no active incidents",
                "evidence": ["incident_intelligence_36a"],
                "confidence": "high",
                "freshness": "fresh",
            })

        blast = rep.get("blast_radius_summary", {}) or {}
        br_entries = int(blast.get("blast_radius_entries", 0) or 0)
        if br_entries > 0:
            signals.append({
                "domain": "incidents",
                "severity": "warning" if br_entries > 3 else "info",
                "message": f"blast radius: {br_entries} entries across {len(blast.get('affected_domains', []))} domains",
                "evidence": ["incident_intelligence_36a"],
                "confidence": "medium",
                "freshness": "fresh",
            })

        correlations = rep.get("correlation_results", []) or []
        if correlations:
            signals.append({
                "domain": "incidents",
                "severity": "info",
                "message": f"cross-domain correlations: {len(correlations)}",
                "evidence": ["incident_intelligence_36a"],
                "confidence": "medium",
                "freshness": "fresh",
            })

    except Exception:
        signals.append({
            "domain": "incidents",
            "severity": "info",
            "message": "incident intelligence module not available",
            "evidence": ["code"],
            "confidence": "low",
            "freshness": "unavailable",
        })

    return signals


def _fallback_summary(reason: str) -> dict[str, Any]:
    return {
        "contract_version": COGNITIVE_CONTRACT_VERSION,
        "overall_state": "unknown",
        "topology_mode": "unknown",
        "summary": f"NO DISPONIBLE — {reason}",
        "important_signals": [],
        "risks": ["no se pudo generar cognitive_summary"],
        "recommended_actions": ["verificar conectividad con sensor fusion"],
        "unavailable_data": ["cognitive_compression"],
        "confidence": "low",
        "freshness": "unavailable",
        "error": reason,
        "_runtime_generation": "30I-F",
    }
