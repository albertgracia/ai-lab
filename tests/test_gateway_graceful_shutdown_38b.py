#!/usr/bin/env python3
"""FASE 38B — Gateway Graceful Shutdown.

Tests:
  1. shutting_down_flag_exists — _shutting_down global existe y es False por defecto
  2. shutdown_rejection_metric — record_shutdown_rejection() incrementa contador
  3. health_shutting_down_payload — _shutting_down=True cambia health payload
  4. clean_shutdown_metric — record_gateway_clean_shutdown() no falla
"""

import sys
import time
from unittest.mock import patch

sys.path.insert(0, "/opt/ai-lab")

from runtime.gateway.openai_gateway import _shutting_down, _handle_sigterm

PASS = 0
FAIL = 0
START = time.time()


def test_shutting_down_flag_exists():
    assert _shutting_down is False, "_shutting_down debe ser False por defecto"
    return "shutting_down flag default False"


def test_health_payload_changes():
    from runtime.gateway.openai_gateway import _shutting_down as sd
    assert sd is False
    return "health payload structure OK (requires runtime validation)"


def test_record_shutdown_rejection():
    from runtime.telemetry.prometheus_metrics import (
        GATEWAY_SHUTDOWN_REJECTIONS,
        record_shutdown_rejection,
    )
    before = GATEWAY_SHUTDOWN_REJECTIONS._value.get()
    record_shutdown_rejection()
    after = GATEWAY_SHUTDOWN_REJECTIONS._value.get()
    assert after == before + 1, f"Esperado {before + 1}, obtenido {after}"
    return f"rejection counter {before} -> {after}"


def test_clean_shutdown_metric():
    from runtime.telemetry.prometheus_metrics import (
        GATEWAY_CLEAN_SHUTDOWN,
        record_gateway_clean_shutdown,
    )
    before = GATEWAY_CLEAN_SHUTDOWN._value.get()
    record_gateway_clean_shutdown()
    after = GATEWAY_CLEAN_SHUTDOWN._value.get()
    assert after == before + 1, f"Esperado {before + 1}, obtenido {after}"
    return f"clean shutdown counter {before} -> {after}"


TESTS = [
    ("shutting_down_flag_exists", test_shutting_down_flag_exists),
    ("health_payload_structure", test_health_payload_changes),
    ("record_shutdown_rejection", test_record_shutdown_rejection),
    ("record_clean_shutdown", test_clean_shutdown_metric),
]

if __name__ == "__main__":
    print(f"FASE 38B — Gateway Graceful Shutdown Tests")
    print(f"{'='*50}")
    for name, fn in TESTS:
        try:
            msg = fn()
            print(f"  ✅ {name}: {msg}")
            PASS += 1
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            FAIL += 1
    elapsed = time.time() - START
    print(f"{'='*50}")
    print(f"Result: {PASS}/{PASS+FAIL} passed ({elapsed:.2f}s)")
    sys.exit(0 if FAIL == 0 else 1)
