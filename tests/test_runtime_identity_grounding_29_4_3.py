#!/usr/bin/env python3
"""FASE 29.4.3 — Runtime Identity Grounding Fix Tests."""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

passed = 0
failed = 0
total = 0


def test(name: str, ok: bool, detail: str = "") -> None:
    global passed, failed, total
    total += 1
    if ok:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        msg = f"  ❌ {name}"
        if detail:
            msg += f" — {detail}"
        print(msg)


from runtime.context.report_runtime_context import (
    build_report_runtime_context,
    format_report_runtime_context,
    extract_target_ip,
    classify_target_role,
    runtime_identity,
)

print("\nFASE 29.4.3 — Runtime Identity Grounding Tests")
print("=" * 55)

# ── 1. runtime_identity() ────────────────────────────────────
rid = runtime_identity()
test("runtime_identity has identity string", isinstance(rid.get("runtime_identity"), str))
test("runtime_identity contains hostname@ip", rid["runtime_identity"] == "ubuntu-ialab@192.168.1.30")
test("runtime_identity has hostname", rid.get("runtime_hostname") == "ubuntu-ialab")
test("runtime_identity has primary IP", rid.get("primary_runtime_ip") == "192.168.1.30")
test("runtime_identity has role", rid.get("primary_runtime_role") == "primary-control-plane")

# ── 2. build_report_runtime_context() with identity ──────────
ctx = build_report_runtime_context()
test("context has runtime_identity", ctx.get("runtime_identity") == "ubuntu-ialab@192.168.1.30")
test("context has runtime_hostname", ctx.get("runtime_hostname") == "ubuntu-ialab")
test("context has primary_runtime_ip", ctx.get("primary_runtime_ip") == "192.168.1.30")
test("context has primary_runtime_role", ctx.get("primary_runtime_role") == "primary-control-plane")
test("runtime_identity in observed", "runtime_identity" in ctx.get("data_quality", {}).get("observed_fields", []))

# ── 3. build_report_runtime_context() with target IP match ───
ctx_match = build_report_runtime_context(target_ip="192.168.1.30")
test("match: target_runtime_match True", ctx_match.get("target_runtime_match") is True)
test("match: target_runtime_ip present", ctx_match.get("target_runtime_ip") == "192.168.1.30")
test("match: target_runtime_role", ctx_match.get("target_runtime_role") == "primary-control-plane")

# ── 4. build_report_runtime_context() with hostname target ───
ctx_host = build_report_runtime_context(target_ip="ubuntu-ialab")
test("match: hostname target_runtime_match True", ctx_host.get("target_runtime_match") is True)
test("match: hostname target_runtime_ip present", ctx_host.get("target_runtime_ip") == "ubuntu-ialab")
test("match: hostname target_runtime_role", ctx_host.get("target_runtime_role") == "primary-control-plane")

# ── 5. classify_target_role() ────────────────────────────────
test("role: primary IP → control-plane", classify_target_role("192.168.1.30") == "primary-control-plane")
test("role: hostname → control-plane", classify_target_role("ubuntu-ialab") == "primary-control-plane")
test("role: 1.50 → inference backend", classify_target_role("192.168.1.50") == "inference-backend-gpu")
test("role: 1.60 → inventory offline", classify_target_role("192.168.1.60") == "inventory-offline")
test("role: unknown IP → unknown", classify_target_role("10.0.0.1") == "unknown")

# ── 6. extract_target_ip() ───────────────────────────────────
test("extract: 192.168.1.30", extract_target_ip("hazme informe de ai-lab en 192.168.1.30") == "192.168.1.30")
test("extract: 192.168.1.50", extract_target_ip("informe de 192.168.1.50") == "192.168.1.50")
test("extract: 192.168.1.60", extract_target_ip("informe de 192.168.1.60") == "192.168.1.60")
test("extract: None", extract_target_ip(None) is None)
test("extract: empty", extract_target_ip("") is None)
test("extract: no IP", extract_target_ip("hola mundo") is None)

# ── 7. format_report_runtime_context() with target ───────────
fctx = format_report_runtime_context(target_ip="192.168.1.30")
fparsed = json.loads(fctx)
test("format: target_runtime_match True", fparsed.get("target_runtime_match") is True)
test("format: primary_runtime_ip present", fparsed.get("primary_runtime_ip") == "192.168.1.30")
test("format: runtime_identity present", fparsed.get("runtime_identity") == "ubuntu-ialab@192.168.1.30")

# ── 8. format_report_runtime_context() with no target ────────
fctx_no = format_report_runtime_context()
fparsed_no = json.loads(fctx_no)
test("format no target: no target_runtime_match", fparsed_no.get("target_runtime_match") is None)
test("format no target: runtime_identity present", fparsed_no.get("runtime_identity") == "ubuntu-ialab@192.168.1.30")

# ── 9. Backend target context ────────────────────────────────
ctx_be = build_report_runtime_context(target_ip="192.168.1.50")
test("backend: target_runtime_match False", ctx_be.get("target_runtime_match") is False)
test("backend: target_runtime_role inference-backend", ctx_be.get("target_runtime_role") == "inference-backend-gpu")

# ── 10. Inventory target context ─────────────────────────────
ctx_inv = build_report_runtime_context(target_ip="192.168.1.60")
test("inventory: target_runtime_match False", ctx_inv.get("target_runtime_match") is False)
test("inventory: target_runtime_role inventory-offline", ctx_inv.get("target_runtime_role") == "inventory-offline")

# ── 11. No false denial — context always sets match for 1.30 ─
test("no false denial: 1.30 is matched", ctx_match.get("target_runtime_match") is True)
test("no false denial: hostname is matched", ctx_host.get("target_runtime_match") is True)
test("no false denial: 1.50 is NOT matched", ctx_be.get("target_runtime_match") is False)
test("no false denial: 1.60 is NOT matched", ctx_inv.get("target_runtime_match") is False)

# ── 12. Role separation
test("role separation: control-plane != inference-backend",
     "primary-control-plane" != "inference-backend-gpu")
test("role separation: inference-backend != inventory",
     "inference-backend-gpu" != "inventory-offline")

# ── Summary ──────────────────────────────────────────────────
print(f"\n{'=' * 55}")
print(f"Results: {passed}/{total} passed, {failed} failed")
print(f"{'✅ ALL PASS' if failed == 0 else '❌ FAILURES DETECTED'}")
print(f"{'=' * 55}")

sys.exit(0 if failed == 0 else 1)
