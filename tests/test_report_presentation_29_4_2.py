#!/usr/bin/env python3
"""FASE 29.4.2 — Report Grounding Presentation Fix Tests."""

import json
import os
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

passed = 0
failed = 0


def test(name: str, ok: bool, detail: str = "") -> None:
    global passed, failed
    if ok:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        msg = f"  ❌ {name}"
        if detail:
            msg += f" — {detail}"
        print(msg)


# ── 1. build_report_runtime_context() ──────────────────────────

try:
    from runtime.context.report_runtime_context import build_report_runtime_context, format_report_runtime_context

    ctx = build_report_runtime_context()
    ctx_str = format_report_runtime_context()
    ctx_parsed = json.loads(ctx_str)

    print("\nFASE 29.4.2 — Report Presentation Fix Tests")
    print("=" * 50)

    # 1A. Models: active
    test("models.active contains qwen2.5-coder-14b", any(
        m["id"] == "qwen2.5-coder-14b-instruct" for m in ctx["models"]["active"]
    ))
    test("models.active contains llama-3.1-8b", any(
        m["id"] == "llama-3.1-8b-instruct" for m in ctx["models"]["active"]
    ))
    test("models.active contains nomic-embed", any(
        m["id"] == "text-embedding-nomic-embed-text-v1.5" for m in ctx["models"]["active"]
    ))

    # 1B. Models: disabled — qwen3.6 nunca activo
    disabled_ids = [m["id"] for m in ctx["models"]["disabled"]]
    test("models.disabled contains qwen3.6-27b", "qwen/qwen3.6-27b" in disabled_ids)
    for m in ctx["models"]["disabled"]:
        if m["id"] == "qwen/qwen3.6-27b":
            test("qwen3.6 has disabled_reason", bool(m.get("disabled_reason")))
    active_ids = [m["id"] for m in ctx["models"]["active"]]
    test("qwen3.6 NEVER in models.active", "qwen/qwen3.6-27b" not in active_ids)
    test("qwen3.6 NEVER in models.discovered", "qwen/qwen3.6-27b" not in [
        m["id"] for m in ctx["models"].get("discovered", [])
    ])

    # 1C. Models: discovered
    discovered_ids = [m["id"] for m in ctx["models"]["discovered"]]
    test("models.discovered contains lmstudio-community/qwen2.5-coder-14b",
         "lmstudio-community/qwen2.5-coder-14b-instruct" in discovered_ids)

    # 1D. Inference nodes: active
    test("inference_nodes.active contains RX9070", any(
        n["name"] == "RX9070" for n in ctx["inference_nodes"]["active"]
    ))
    rx9070 = next((n for n in ctx["inference_nodes"]["active"] if n["name"] == "RX9070"), None)
    if rx9070:
        test("RX9070 status is online", rx9070.get("status") == "online")
        test("RX9070 vram_gb is 16", rx9070.get("vram_gb") == 16)

    # 1E. Inference nodes: inventory
    test("inference_nodes.inventory contains RX7900XT", any(
        n["name"] == "RX7900XT" for n in ctx["inference_nodes"]["inventory"]
    ))
    rx7900xt = next((n for n in ctx["inference_nodes"]["inventory"] if n["name"] == "RX7900XT"), None)
    if rx7900xt:
        test("RX7900XT active_runtime is False", rx7900xt.get("active_runtime") is False)
        test("RX7900XT status is offline", rx7900xt.get("status") == "offline")

    # 1F. Services
    test("services.core contains ailab-gateway", any(
        "ailab-gateway" in s for s in ctx["services"]["core"]
    ))
    test("services.core contains ailab-router", any(
        "ailab-router" in s for s in ctx["services"]["core"]
    ))
    test("services.core contains ailab-live-api", any(
        "ailab-live-api" in s for s in ctx["services"]["core"]
    ))
    test("services.support contains ailab-docs", any(
        "ailab-docs" in s for s in ctx["services"]["support"]
    ))
    test("services.observability contains prometheus", any(
        "prometheus" in str(s).lower() for s in ctx["services"]["observability"]
    ))
    test("services.observability contains grafana", any(
        "grafana" in str(s).lower() for s in ctx["services"]["observability"]
    ))

    # 1G. Data quality
    test("data_quality.observed_fields is list",
         isinstance(ctx["data_quality"]["observed_fields"], list))
    test("data_quality.inferred_fields is list",
         isinstance(ctx["data_quality"]["inferred_fields"], list))
    test("data_quality.missing_fields is list",
         isinstance(ctx["data_quality"]["missing_fields"], list))
    test("data_quality has observed_fields entries",
         len(ctx["data_quality"]["observed_fields"]) > 0)

    # 1H. Report metadata
    test("_report_type is runtime_operational_report",
         ctx.get("_report_type") == "runtime_operational_report")
    gen = ctx.get("_runtime_generation", "")
    test("_runtime_generation is 29.4.x",
         gen in ("29.4.2", "29.4.3"),
         f"got {gen}")
    test("_grounded_runtime is True",
         ctx.get("_grounded_runtime") is True)
    test("_grounding_confidence is high",
         ctx.get("_grounding_confidence") == "high")

    # 1I. Legacy gpu_nodes no longer present
    test("gpu_nodes (legacy) NOT in ctx",
         "gpu_nodes" not in ctx)

    # 2. format_report_runtime_context()
    test("format_report_runtime_context returns valid JSON",
         isinstance(ctx_parsed, dict))
    test("formatted context <= 12000 chars",
         len(ctx_str) <= 12_000)
    test("formatted context contains models",
         "models" in ctx_parsed)
    test("formatted context contains services",
         "services" in ctx_parsed)
    test("formatted context contains inference_nodes",
         "inference_nodes" in ctx_parsed)
    test("formatted context contains data_quality",
         "data_quality" in ctx_parsed)

except Exception:
    test("build_report_runtime_context import", False, traceback.format_exc())


# ── 3. report_prompt.md ────────────────────────────────────────

try:
    prompt_path = os.path.join(os.path.dirname(__file__), "..", "runtime", "prompts", "report_prompt.md")
    with open(prompt_path, encoding="utf-8") as f:
        prompt = f.read()

    test("report_prompt.md exists and readable", len(prompt) > 0)
    test("prompt contains OBSERVADO", "OBSERVADO" in prompt)
    test("prompt contains INFERIDO", "INFERIDO" in prompt)
    test("prompt contains NO DISPONIBLE", "NO DISPONIBLE" in prompt)
    test("prompt contains qwen3.6 and DESACTIVADO",
         "qwen3.6" in prompt and "DESACTIVADO" in prompt)
    test("prompt contains RX7900XT and INVENTARIADO",
         "RX7900XT" in prompt and "INVENTARIADO" in prompt)
    test("prompt does NOT contain '5-8 lineas'",
         "5-8 lineas" not in prompt.lower())
    test("prompt mentions 'en conclusion' only as prohibition",
         "en conclusion" in prompt.lower())

    sections_found = 0
    section_markers = [
        "RESUMEN EJECUTIVO", "RUNTIME IDENTITY", "ACTIVE INFERENCE RUNTIME",
        "SERVICIOS AI-LAB", "MODEL RUNTIME", "STREAMING & GATEWAY",
        "OBSERVABILIDAD", "SLO & RUNTIME PROTECTION",
        "GOVERNANCE & AGENTIC SAFETY", "DATOS NO DISPONIBLES",
        "RIESGOS REALES", "RECOMENDACIONES TECNICAS",
    ]
    for marker in section_markers:
        if marker in prompt:
            sections_found += 1
    test(f"prompt contains all 12 sections ({sections_found}/12)",
         sections_found == 12)

except Exception:
    test("report_prompt.md test", False, traceback.format_exc())


# ── 4. extract_target_ip regression ────────────────────────────

try:
    from runtime.context.report_runtime_context import extract_target_ip

    test("extract_target_ip extracts IP from '192.168.1.30'",
         extract_target_ip("informe de 192.168.1.30") == "192.168.1.30")
    test("extract_target_ip extracts domain from 'metricas.labrazahome.com'",
         "metricas.labrazahome.com" in (extract_target_ip("estado de metricas.labrazahome.com") or ""))
    test("extract_target_ip returns None for empty",
         extract_target_ip("") is None)
    test("extract_target_ip returns None for no IP",
         extract_target_ip("dame un informe") is None)

except Exception:
    test("extract_target_ip regression", False, traceback.format_exc())


# ── Summary ────────────────────────────────────────────────────

print(f"\n{'=' * 50}")
print(f"Resultado: {passed} passed, {failed} failed")
if failed:
    sys.exit(1)
