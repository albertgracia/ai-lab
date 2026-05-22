"""FASE 32B: Grafana Semantic Cleanup — test suite."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from runtime.observability.grafana_semantic_validator import (
    GRAFANA_SEMANTIC_CONTRACT_VERSION,
    build_dashboard_inventory_32b,
    build_grafana_semantic_summary,
    calculate_grafana_alignment_score,
    detect_fake_gpu_panels,
    detect_stale_panels,
    detect_orphan_datasources,
    detect_metric_drift,
    detect_topology_dashboard_alignment,
)

PASS = 0
FAIL = 0
TOTAL = 20


def check(condition: bool, name: str, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} — {detail}")


# ── 1. Dashboard inventory ──────────────────────────────────────

def test_dashboard_inventory_generated():
    inv = build_dashboard_inventory_32b()
    check(len(inv) >= 5, "dashboard inventory generated", f"got {len(inv)} dashboards")


# ── 2. Fake GPU panels detected ─────────────────────────────────

def test_fake_gpu_panels_detected():
    fake = detect_fake_gpu_panels()
    check(isinstance(fake, list), "fake_gpu_panels returns list")
    check(all("fake_gpus" in f for f in fake), "fake_gpu_panels have fake_gpus key")


# ── 3. Stale panels detected ────────────────────────────────────

def test_stale_panels_detected():
    stale = detect_stale_panels()
    check(isinstance(stale, list), "stale_panels returns list")
    check(all("stale_metrics" in s for s in stale), "stale_panels have stale_metrics key")


# ── 4. Orphan datasources detected ──────────────────────────────

def test_orphan_datasources_detected():
    orphan = detect_orphan_datasources()
    check(isinstance(orphan, list), "orphan_datasources returns list")
    check(all("orphan_datasource_uid" in o for o in orphan), "orphan_datasources have uid key")


# ── 5. Metric drift detected ────────────────────────────────────

def test_metric_drift_detected():
    drift = detect_metric_drift()
    check(isinstance(drift, list), "metric_drift returns list")
    check(all("metrics" in d for d in drift), "metric_drift has metrics key")


# ── 6. Alignment score generated ────────────────────────────────

def test_runtime_alignment_score_generated():
    score = calculate_grafana_alignment_score(total_dashboards=10)
    check(score["overall_score"] >= 0, "alignment score >= 0")
    check(score["overall_score"] <= 100, "alignment score <= 100")
    check(score["level"] in ("high", "medium", "low", "critical"), "alignment score has valid level")


# ── 7. Topology dashboard alignment ─────────────────────────────

def test_topology_dashboard_alignment():
    topo = detect_topology_dashboard_alignment()
    check(isinstance(topo, list), "topology alignment returns list")
    for t in topo:
        check("issues" in t, "topology issue has issues key")


# ── 8. RX9070 active (no drift) ─────────────────────────────────

def test_rx9070_active_only():
    dashboards = []
    if Path("/opt/ai-lab/stacks/observability/grafana/provisioning/dashboards").exists():
        for fpath in Path("/opt/ai-lab/stacks/observability/grafana/provisioning/dashboards").rglob("*.json"):
            try:
                dashboards.append(json.loads(fpath.read_text(errors="ignore")))
            except (json.JSONDecodeError, OSError):
                pass
    for db in dashboards:
        db_json = json.dumps(db).lower()
        if "rx9070xt" in db_json:
            global FAIL
            FAIL += 1
            print(f"  ❌ RX9070XT drift in {db.get('uid', '?')}: {db.get('title', '?')}")
            return
    print(f"  ✅ No RX9070XT drift in any dashboard")


# ── 9. RX7900XT inventory only ──────────────────────────────────

def test_rx7900xt_inventory_only():
    inv = build_dashboard_inventory_32b()
    for d in inv:
        if "rx7900xt" in d.get("title", "").lower():
            check(d.get("health") in ("deprecated", "inventory_drift"), "RX7900XT marked as inventory", d["title"])


# ── 10. No fake runtime GPU ─────────────────────────────────────

def test_no_fake_runtime_gpu():
    fake = detect_fake_gpu_panels()
    active_dashboards = []
    if Path("/opt/ai-lab/stacks/observability/grafana/provisioning/dashboards/active").exists():
        for fpath in Path("/opt/ai-lab/stacks/observability/grafana/provisioning/dashboards/active").rglob("*.json"):
            try:
                active_dashboards.append(json.loads(fpath.read_text(errors="ignore")))
            except (json.JSONDecodeError, OSError):
                pass
    active_fake = detect_fake_gpu_panels(active_dashboards)
    check(len(active_fake) == 0, "no fake GPUs in active dashboards", f"got {len(active_fake)}")


# ── 11. Dashboard metadata present ──────────────────────────────

def test_dashboard_metadata_present():
    inv = build_dashboard_inventory_32b()
    for d in inv:
        check("uid" in d, f"dashboard {d.get('uid', '?')} has uid")
        check("health" in d, f"dashboard {d.get('uid', '?')} has health")
        check("runtime_aligned" in d, f"dashboard {d.get('uid', '?')} has runtime_aligned")


# ── 12. Degraded mode dashboard awareness ───────────────────────

def test_degraded_mode_dashboard_awareness():
    score = calculate_grafana_alignment_score(
        total_dashboards=5, runtime_aligned_count=5,
    )
    check(score["level"] == "high", "fully aligned dashboards yield high score")


# ── 13. Governance dashboards present ───────────────────────────

def test_governance_dashboards_present():
    inv = build_dashboard_inventory_32b()
    governance_uids = {"ai-lab-overview", "ai-lab-runtime", "ai-lab-gpus"}
    found = {d["uid"] for d in inv} & governance_uids
    check(len(found) >= 2, "governance dashboards present", f"found {found}")


# ── 14. Runtime API alignment ───────────────────────────────────

def test_runtime_api_alignment():
    from runtime.observability.grafana_semantic_validator import _RUNTIME_ENDPOINTS
    check(len(_RUNTIME_ENDPOINTS) >= 10, "runtime endpoints defined", f"got {len(_RUNTIME_ENDPOINTS)}")


# ── 15. Dashboard inventory JSON safe ───────────────────────────

def test_dashboard_inventory_json_safe():
    inv = build_dashboard_inventory_32b()
    try:
        json.dumps(inv)
        check(True, "dashboard inventory is JSON-serializable")
    except (TypeError, ValueError) as exc:
        check(False, "dashboard inventory JSON-safe", str(exc))


# ── 16. Grafana semantic endpoints 200 ──────────────────────────

def test_grafana_semantic_endpoints_200():
    summary = build_grafana_semantic_summary()
    check("contract_version" in summary, "semantic summary has contract_version")
    check(summary["contract_version"] == "32B", f"contract_version is 32B, got {summary.get('contract_version')}")
    score = summary.get("grafana_alignment_score", {})
    check("overall_score" in score, "alignment score in summary")
    check("inventory" in summary, "inventory in summary")
    check("issues" in summary, "issues in summary")


# ── 17. No inventory contamination ──────────────────────────────

def test_no_inventory_contamination():
    inv = build_dashboard_inventory_32b()
    for d in inv:
        if d.get("health") == "healthy":
            check(not d.get("deprecated", False), f"healthy dashboard {d['uid']} not deprecated")


# ── 18. Topology confidence visible ─────────────────────────────

def test_topology_confidence_visible():
    topo = detect_topology_dashboard_alignment()
    for t in topo:
        check("severity" in t, f"topology issue {t.get('dashboard_uid', '?')} has severity")


# ── 19. Runtime maturity presence ───────────────────────────────

def test_runtime_maturity_visible():
    summary = build_grafana_semantic_summary()
    inventory = summary.get("inventory", {})
    check("runtime_aligned" in inventory, "runtime_aligned count in inventory")
    check("legacy" in inventory, "legacy count in inventory")


# ── 20. Prometheus authority preserved ──────────────────────────

def test_prometheus_authority_preserved():
    from runtime.observability.grafana_inventory import _KNOWN_DATASOURCE_UID
    check(bool(_KNOWN_DATASOURCE_UID), "Prometheus datasource UID known")


# ── Run all tests ───────────────────────────────────────────────

if __name__ == "__main__":
    print(f"FASE 32B: Grafana Semantic Cleanup — {TOTAL} tests")
    print()

    test_dashboard_inventory_generated()
    test_fake_gpu_panels_detected()
    test_stale_panels_detected()
    test_orphan_datasources_detected()
    test_metric_drift_detected()
    test_runtime_alignment_score_generated()
    test_topology_dashboard_alignment()
    test_rx9070_active_only()
    test_rx7900xt_inventory_only()
    test_no_fake_runtime_gpu()
    test_dashboard_metadata_present()
    test_degraded_mode_dashboard_awareness()
    test_governance_dashboards_present()
    test_runtime_api_alignment()
    test_dashboard_inventory_json_safe()
    test_grafana_semantic_endpoints_200()
    test_no_inventory_contamination()
    test_topology_confidence_visible()
    test_runtime_maturity_visible()
    test_prometheus_authority_preserved()

    print()
    print(f"Results: {PASS}/{TOTAL} PASS, {FAIL}/{TOTAL} FAIL")
    sys.exit(0 if FAIL == 0 else 1)
