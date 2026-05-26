import time
from types import SimpleNamespace
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_shutdown_flag_defaults_false() -> None:
    import runtime.gateway.openai_gateway as gw

    assert gw._shutting_down is False


def test_handle_sigterm_sets_flag_and_requests_shutdown(monkeypatch) -> None:
    import runtime.gateway.openai_gateway as gw

    class DummyServer:
        def __init__(self) -> None:
            self.shutdown_calls = 0

        def shutdown(self) -> None:
            self.shutdown_calls += 1

    dummy_server = DummyServer()
    gw._server_ref = dummy_server
    gw._shutting_down = False
    gw._shutdown_thread_started = False

    calls = {"released": 0, "clean": 0}

    monkeypatch.setattr("runtime.gateway.process_guard.release_lock", lambda: calls.__setitem__("released", calls["released"] + 1))
    monkeypatch.setattr("runtime.telemetry.prometheus_metrics.record_gateway_clean_shutdown", lambda: calls.__setitem__("clean", calls["clean"] + 1))

    gw._handle_sigterm(15, None)
    for _ in range(50):
        if dummy_server.shutdown_calls > 0:
            break
        time.sleep(0.01)

    assert gw._shutting_down is True
    assert calls["released"] == 1
    assert calls["clean"] == 1
    assert dummy_server.shutdown_calls == 1


def test_health_reports_shutting_down(monkeypatch) -> None:
    import runtime.gateway.openai_gateway as gw

    sent = {}

    class DummyHandler:
        path = "/health"
        client_address = ("127.0.0.1", 0)

        def _send_json(self, status, payload):
            sent["status"] = status
            sent["payload"] = payload

    monkeypatch.setattr(gw, "check_rate_limit", lambda _ip: True)
    monkeypatch.setattr(gw, "get_active_backend", lambda: {"url": "http://x/v1"})

    prev = gw._shutting_down
    gw._shutting_down = True
    try:
        gw.GatewayHandler.do_GET(DummyHandler())
    finally:
        gw._shutting_down = prev

    assert sent["status"] == 200
    assert sent["payload"]["status"] == "shutting_down"
    assert sent["payload"]["shutting_down"] is True


def test_post_requests_rejected_when_shutting_down(monkeypatch) -> None:
    import runtime.gateway.openai_gateway as gw
    from runtime.telemetry.prometheus_metrics import GATEWAY_SHUTDOWN_REJECTIONS

    sent = {}

    class DummyHandler:
        def _send_json(self, status, payload):
            sent["status"] = status
            sent["payload"] = payload

        def _reject_if_shutting_down(self):
            return gw.GatewayHandler._reject_if_shutting_down(self)

    before = GATEWAY_SHUTDOWN_REJECTIONS._value.get()
    prev = gw._shutting_down
    gw._shutting_down = True
    try:
        gw.GatewayHandler.do_POST(DummyHandler())
    finally:
        gw._shutting_down = prev

    after = GATEWAY_SHUTDOWN_REJECTIONS._value.get()
    assert sent["status"] == 503
    assert sent["payload"]["error"] == "shutting_down"
    assert after >= before + 1


def test_release_lock_idempotent() -> None:
    from runtime.gateway.process_guard import release_lock

    release_lock()
    release_lock()
