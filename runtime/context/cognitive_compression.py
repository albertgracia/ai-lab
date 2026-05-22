import time
from typing import Any

COGNITIVE_CONTRACT_VERSION = "30I-F"

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

    if not all_signals:
        unavailable.append("all_domains")

    important_signals = rank_operational_signals(all_signals)
    summary = build_actionable_summary(important_signals, sensor_snapshot, extra_ctx)
    summary["important_signals"] = important_signals

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
