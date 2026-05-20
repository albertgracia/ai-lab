"""FASE 30B: Model State Awareness — Active vs Loaded vs Discoverable"""

import time
import json
import pytest

from runtime.maturity.descriptor import ModelStatus, TemporalState
from runtime.state.lmstudio_state import (
    ModelStatusTracker, normalize_model_id,
    ACTIVE_WINDOW_SECONDS, get_model_tracker,
)
from runtime.maturity.builder import build_model_status_map


# ── normalize_model_id (RULE-30B-6) ────────────────────────────

def test_normalize_removes_qwen_prefix():
    assert normalize_model_id("qwen/qwen2.5-coder-14b-instruct") == "qwen2.5-coder-14b-instruct"


def test_normalize_removes_lmstudio_prefix():
    assert normalize_model_id("lmstudio-community/qwen2.5-coder-14b-instruct") == "qwen2.5-coder-14b-instruct"


def test_normalize_removes_hugging_quants_prefix():
    assert normalize_model_id("hugging-quants/llama-3.1-8b-instruct") == "llama-3.1-8b-instruct"


def test_normalize_noop_on_already_clean():
    assert normalize_model_id("llama-3.1-8b-instruct") == "llama-3.1-8b-instruct"


def test_normalize_strips_whitespace():
    assert normalize_model_id("  qwen/qwen2.5-coder-14b-instruct  ") == "qwen2.5-coder-14b-instruct"


# RULE-30B-6: aliases normalize to same key
def test_alias_normalization_equivalence():
    a = normalize_model_id("qwen/qwen2.5-coder-14b-instruct")
    b = normalize_model_id("lmstudio-community/qwen2.5-coder-14b-instruct")
    assert a == b


# ── ModelStatusTracker init ─────────────────────────────────────

def test_tracker_init_empty():
    tracker = ModelStatusTracker()
    assert tracker.to_dict() == {}


def test_tracker_set_disabled_ids():
    tracker = ModelStatusTracker()
    tracker.set_disabled_ids(["qwen3.6-27b", "qwen/qwen3.6-27b"])
    assert "qwen3.6-27b" in tracker._disabled_ids


# ── set_status / get_status ─────────────────────────────────────

def test_tracker_set_and_get_status():
    tracker = ModelStatusTracker()
    tracker.set_status("llama-3.1-8b-instruct", ModelStatus.LOADED)
    assert tracker.get_status("llama-3.1-8b-instruct") == ModelStatus.LOADED


def test_tracker_default_status_is_discoverable():
    tracker = ModelStatusTracker()
    assert tracker.get_status("unknown-model") == ModelStatus.DISCOVERABLE


def test_tracker_set_status_increments_transition():
    tracker = ModelStatusTracker()
    tracker.set_status("model-a", ModelStatus.LOADED)
    tracker.set_status("model-a", ModelStatus.ACTIVE)
    assert tracker.get_temporal("model-a").transition_count == 2


def test_tracker_set_status_same_no_transition():
    tracker = ModelStatusTracker()
    tracker.set_status("model-a", ModelStatus.LOADED)
    tracker.set_status("model-a", ModelStatus.LOADED)
    assert tracker.get_temporal("model-a").transition_count == 1


# ── mark_active ─────────────────────────────────────────────────

def test_mark_active_sets_active():
    tracker = ModelStatusTracker()
    tracker.set_status("model-a", ModelStatus.LOADED)
    tracker.mark_active("model-a")
    assert tracker.get_status("model-a") == ModelStatus.ACTIVE


def test_mark_active_records_route():
    tracker = ModelStatusTracker()
    tracker.mark_active("model-a")
    ts = tracker.get_temporal("model-a")
    assert ts.last_routed > 0


# RULE-30B-4: DISABLED priority — mark_active on disabled is noop
def test_mark_active_on_disabled_is_noop():
    tracker = ModelStatusTracker()
    tracker.set_disabled_ids(["qwen3.6-27b"])
    tracker.set_status("qwen3.6-27b", ModelStatus.LOADED)
    tracker.mark_active("qwen3.6-27b")
    assert tracker.get_status("qwen3.6-27b") != ModelStatus.ACTIVE


# ── mark_error ──────────────────────────────────────────────────

def test_mark_error_sets_unavailable():
    tracker = ModelStatusTracker()
    tracker.mark_error("model-a", "timeout")
    assert tracker.get_status("model-a") == ModelStatus.UNAVAILABLE


def test_mark_error_records_error():
    tracker = ModelStatusTracker()
    tracker.mark_error("model-a", "vram_pressure")
    ts = tracker.get_temporal("model-a")
    assert "vram_pressure" in ts.last_error


# ── ACTIVE TTL (RULE-30B-3) ────────────────────────────────────

def test_active_ttl_does_not_expire_recent():
    tracker = ModelStatusTracker()
    tracker.mark_active("model-a")
    expired = tracker.expire_active_models()
    assert "model-a" not in expired
    assert tracker.get_status("model-a") == ModelStatus.ACTIVE


def test_active_ttl_expires_aged_model():
    tracker = ModelStatusTracker()
    tracker.mark_active("model-a")
    ts = tracker.get_temporal("model-a")
    ts.last_routed = time.time() - ACTIVE_WINDOW_SECONDS - 10
    expired = tracker.expire_active_models()
    assert "model-a" in expired
    assert tracker.get_status("model-a") == ModelStatus.LOADED


def test_active_ttl_increments_transition_on_expiry():
    tracker = ModelStatusTracker()
    tracker.mark_active("model-a")
    ts = tracker.get_temporal("model-a")
    old_count = ts.transition_count
    ts.last_routed = time.time() - ACTIVE_WINDOW_SECONDS - 10
    tracker.expire_active_models()
    assert tracker.get_temporal("model-a").transition_count == old_count + 1


# ── DISABLED priority (RULE-30B-4) ─────────────────────────────

def test_disabled_priority_over_loaded():
    tracker = ModelStatusTracker()
    tracker.set_disabled_ids(["qwen3.6-27b"])
    tracker.set_status("qwen3.6-27b", ModelStatus.LOADED)
    assert tracker.get_status("qwen3.6-27b") == ModelStatus.DISABLED


def test_disabled_priority_over_active():
    tracker = ModelStatusTracker()
    tracker.set_disabled_ids(["qwen3.6-27b"])
    tracker.mark_active("qwen3.6-27b")
    assert tracker.get_status("qwen3.6-27b") != ModelStatus.ACTIVE


def test_disabled_priority_over_discoverable():
    tracker = ModelStatusTracker()
    tracker.set_disabled_ids(["qwen3.6-27b"])
    assert tracker.get_status("qwen3.6-27b") == ModelStatus.DISABLED


# ── is_node_active_capable (RULE-30B-5) ────────────────────────

def test_inventory_node_not_active_capable():
    tracker = ModelStatusTracker()
    assert not tracker.is_node_active_capable("192.168.1.200")


def test_offline_node_not_active_capable():
    tracker = ModelStatusTracker()
    assert not tracker.is_node_active_capable("192.168.1.60")


def test_inference_node_is_active_capable():
    tracker = ModelStatusTracker()
    assert tracker.is_node_active_capable("192.168.1.50")


# ── to_dict ─────────────────────────────────────────────────────

def test_to_dict_includes_status():
    tracker = ModelStatusTracker()
    tracker.set_status("llama-3.1-8b-instruct", ModelStatus.LOADED)
    d = tracker.to_dict()
    assert "llama-3.1-8b-instruct" in d
    assert d["llama-3.1-8b-instruct"]["status"] == "loaded"


def test_to_dict_json_serializable():
    tracker = ModelStatusTracker()
    tracker.set_status("model-a", ModelStatus.ACTIVE)
    json.dumps(tracker.to_dict())


def test_to_dict_includes_temporal():
    tracker = ModelStatusTracker()
    tracker.set_status("model-a", ModelStatus.LOADED)
    d = tracker.to_dict()
    assert "temporal" in d["model-a"]


def test_to_dict_includes_loaded_flag():
    tracker = ModelStatusTracker()
    tracker.set_status("model-a", ModelStatus.ACTIVE)
    assert tracker.to_dict()["model-a"]["loaded"] is True
    tracker.set_status("model-a", ModelStatus.LOADED)
    assert tracker.to_dict()["model-a"]["loaded"] is True
    tracker.set_status("model-a", ModelStatus.DISCOVERABLE)
    assert tracker.to_dict()["model-a"]["loaded"] is False


def test_to_dict_includes_routable_flag():
    tracker = ModelStatusTracker()
    tracker.set_status("model-a", ModelStatus.ACTIVE)
    assert tracker.to_dict()["model-a"]["routable"] is True
    tracker.set_status("model-a", ModelStatus.LOADED)
    assert tracker.to_dict()["model-a"]["routable"] is False


# ── get_model_tracker singleton ─────────────────────────────────

def test_get_model_tracker_returns_singleton():
    t1 = get_model_tracker()
    t2 = get_model_tracker()
    assert t1 is t2


# ── build_model_status_map ──────────────────────────────────────

def test_build_model_status_map_returns_dict():
    result = build_model_status_map()
    assert isinstance(result, dict)


# ── TemporalState integration ───────────────────────────────────

def test_temporal_tracks_transitions():
    ts = TemporalState()
    assert ts.transition_count == 0
    ts.touch()
    assert ts.last_seen > 0
    ts.record_route()
    assert ts.transition_count == 1
    ts.record_route()
    assert ts.transition_count == 2
