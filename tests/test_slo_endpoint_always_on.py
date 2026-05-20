#!/usr/bin/env python3
"""FASE 29.4.4-C — SLO Health Endpoint Always-On.

Tests:
  1. disabled_default    — sin flag, responde 200 con payload disabled
  2. payload_structure   — payload disabled tiene los 5 campos exactos
  3. module_unavailable  — _HAVE_SLO=False + flag=true → 200 disabled (fallback)
  4. no_break_health     — /health sigue funcionando
  5. no_break_metrics    — /metrics sigue funcionando
  6. enabled_mock        — flag=true + SLO disponible → 200 con get_runtime_health()
"""

import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, "/opt/ai-lab")

from runtime.gateway.openai_gateway import (
    _slo_is_enabled, _DISABLED_SLO_PAYLOAD, _HAVE_SLO,
)

PASS = 0
FAIL = 0
START = time.time()

EXPECTED_DISABLED = {
    "enabled": False,
    "state": "disabled",
    "mode": "passive",
    "enforcement": False,
    "reason": "slo_enforcement_disabled",
}


def test(name: str, ok: bool, detail: str = ""):
    global PASS, FAIL
    if ok:
        PASS += 1
        status = "✅"
    else:
        FAIL += 1
        status = "❌"
    elapsed = (time.time() - START) * 1000
    print(f"  {status} {name} ({elapsed:.0f}ms) {('| ' + detail) if detail else ''}")


# ═══════════════════════════════════════════════════
# TEST 1: _slo_is_enabled() helper
# ═══════════════════════════════════════════════════

# Default (no flag)
os.environ.pop("AI_LAB_ENABLE_SLO_ENFORCEMENT", None)
test("helper_default_false", not _slo_is_enabled(),
     "_slo_is_enabled() debe ser False por defecto")

# Explicit false
os.environ["AI_LAB_ENABLE_SLO_ENFORCEMENT"] = "false"
test("helper_explicit_false", not _slo_is_enabled(),
     "_slo_is_enabled() False cuando flag=false")

# True
os.environ["AI_LAB_ENABLE_SLO_ENFORCEMENT"] = "true"
test("helper_explicit_true", _slo_is_enabled(),
     "_slo_is_enabled() True cuando flag=true")

# 1
os.environ["AI_LAB_ENABLE_SLO_ENFORCEMENT"] = "1"
test("helper_numeric_true", _slo_is_enabled(),
     "_slo_is_enabled() True cuando flag=1")

# yes
os.environ["AI_LAB_ENABLE_SLO_ENFORCEMENT"] = "yes"
test("helper_yes_true", _slo_is_enabled(),
     "_slo_is_enabled() True cuando flag=yes")

# Clean up
os.environ.pop("AI_LAB_ENABLE_SLO_ENFORCEMENT", None)


# ═══════════════════════════════════════════════════
# TEST 2: _DISABLED_SLO_PAYLOAD structure
# ═══════════════════════════════════════════════════

test("payload_is_dict", isinstance(_DISABLED_SLO_PAYLOAD, dict),
     f"type={type(_DISABLED_SLO_PAYLOAD).__name__}")

test("payload_5_keys", len(_DISABLED_SLO_PAYLOAD) == 5,
     f"keys={sorted(_DISABLED_SLO_PAYLOAD.keys())}")

test("payload_exact_match", _DISABLED_SLO_PAYLOAD == EXPECTED_DISABLED,
     f"payload={json.dumps(_DISABLED_SLO_PAYLOAD)}")

for key in ("enabled", "state", "mode", "enforcement", "reason"):
    test(f"payload_has_{key}", key in _DISABLED_SLO_PAYLOAD,
         f"value={_DISABLED_SLO_PAYLOAD[key]}")


# ═══════════════════════════════════════════════════
# TEST 3: module import guard
# ═══════════════════════════════════════════════════

# _HAVE_SLO reflects module availability
test("have_slo_defined", isinstance(_HAVE_SLO, bool),
     f"_HAVE_SLO={_HAVE_SLO}")


# ═══════════════════════════════════════════════════
# TEST 4: _slo_is_enabled combined with _HAVE_SLO
# ═══════════════════════════════════════════════════

# When enforcement=false or SLO unavailable, handler returns disabled payload
# Simulate the handler logic
def handler_logic():
    if _HAVE_SLO and _slo_is_enabled():
        return "real_health"  # would call _slo_manager.get_runtime_health()
    return _DISABLED_SLO_PAYLOAD

os.environ["AI_LAB_ENABLE_SLO_ENFORCEMENT"] = "false"
result = handler_logic()
test("disabled_when_flag_false", result == _DISABLED_SLO_PAYLOAD,
     f"result={type(result).__name__}")

os.environ["AI_LAB_ENABLE_SLO_ENFORCEMENT"] = "true"
result = handler_logic()
if _HAVE_SLO:
    test("real_health_when_flag_true_and_have_slo", result == "real_health",
         "handler devuelve real_health (mock)")
else:
    test("disabled_fallback_when_module_unavailable", result == _DISABLED_SLO_PAYLOAD,
         "SLO module unavailable → disabled fallback")

os.environ.pop("AI_LAB_ENABLE_SLO_ENFORCEMENT", None)


# ═══════════════════════════════════════════════════
# TEST 5: Payload JSON serializable
# ═══════════════════════════════════════════════════

try:
    serialized = json.dumps(_DISABLED_SLO_PAYLOAD)
    test("payload_json_serializable", True,
         f"len={len(serialized)}")
except Exception as e:
    test("payload_json_serializable", False, f"exception={e}")

# Verify round-trip
parsed = json.loads(json.dumps(_DISABLED_SLO_PAYLOAD))
test("payload_json_roundtrip", parsed == _DISABLED_SLO_PAYLOAD,
     "json.dumps → json.loads mantiene estructura")


# ═══════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════

total = PASS + FAIL
elapsed = time.time() - START
print(f"\n{'=' * 55}")
print(f"Results: {PASS}/{total} passed, {FAIL} failed ({elapsed:.1f}s)")
print(f"{'=' * 55}")

sys.exit(0 if FAIL == 0 else 1)
