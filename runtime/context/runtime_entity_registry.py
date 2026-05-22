from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# FASE 31E: Import new entity registry functions for backward-compat shim
from runtime.entities import (
    build_entity_registry as _31e_build_entity_registry,
    build_active_entities as _31e_build_active_entities,
    build_inventory_entities as _31e_build_inventory_entities,
    build_discoverable_entities as _31e_build_discoverable_entities,
    build_deprecated_entities as _31e_build_deprecated_entities,
    build_routability_summary as _31e_build_routability_summary,
    build_topology_preparation as _31e_build_topology_preparation,
    classify_entity_state as _31e_classify_entity_state,
    classify_operational_state as _31e_classify_operational_state,
    classify_discoverability as _31e_classify_discoverability,
    classify_routability as _31e_classify_routability,
    detect_stale_entities as _31e_detect_stale_entities,
    detect_inventory_only_entities as _31e_detect_inventory_only_entities,
    detect_deprecated_entities as _31e_detect_deprecated_entities,
)

OBSERVED_ENTITY_TYPES = frozenset({
    "gpu", "service", "model", "host", "storage", "topology_mode",
})


@dataclass
class ObservedEntity:
    name: str
    entity_type: str
    source_of_truth: list[str] = field(default_factory=list)
    confidence: str = "low"
    freshness: str = "unavailable"
    observed_state: str | None = None
    host: str | None = None


class RuntimeEntityRegistry:
    def __init__(self, ctx: dict[str, Any] | None = None):
        self._entities: dict[str, list[ObservedEntity]] = {
            t: [] for t in OBSERVED_ENTITY_TYPES
        }
        self._forbidden_patterns: dict[str, set[str]] = {}
        if ctx:
            self.build_from_context(ctx)

    def build_from_context(self, ctx: dict[str, Any]) -> None:
        gpu_summaries = ctx.get("gpu_operational_summaries", [])
        if isinstance(gpu_summaries, list):
            for g in gpu_summaries:
                if isinstance(g, dict):
                    self._entities["gpu"].append(ObservedEntity(
                        name=g.get("gpu_id", "?"),
                        entity_type="gpu",
                        source_of_truth=g.get("source_of_truth", ["unknown"]),
                        confidence=g.get("confidence", "low"),
                        freshness=g.get("freshness", {}).get("status", "unavailable") if isinstance(g.get("freshness"), dict) else "unavailable",
                        observed_state=g.get("observed_state"),
                        host=g.get("host"),
                    ))

        inference_nodes = ctx.get("inference_nodes", {})
        if isinstance(inference_nodes, dict):
            for node_list_key in ("active", "inventory"):
                for n in inference_nodes.get(node_list_key, []):
                    if isinstance(n, dict):
                        self._entities["host"].append(ObservedEntity(
                            name=n.get("host", n.get("name", "?")),
                            entity_type="host",
                            source_of_truth=["inventory"],
                            confidence="medium",
                            freshness="unknown",
                        ))

        runtime_host = ctx.get("primary_runtime_ip")
        if runtime_host:
            self._entities["host"].append(ObservedEntity(
                name=runtime_host,
                entity_type="host",
                source_of_truth=["code"],
                confidence="high",
                freshness="fresh",
            ))
        runtime_hostname = ctx.get("runtime_hostname")
        if runtime_hostname:
            self._entities["host"].append(ObservedEntity(
                name=runtime_hostname,
                entity_type="host",
                source_of_truth=["code"],
                confidence="high",
                freshness="fresh",
            ))

        models_data = ctx.get("models", {})
        if isinstance(models_data, dict):
            for model_group in ("active", "disabled", "discovered"):
                for m in models_data.get(model_group, []):
                    if isinstance(m, dict):
                        mid = m.get("id")
                        if mid:
                            self._entities["model"].append(ObservedEntity(
                                name=str(mid),
                                entity_type="model",
                                source_of_truth=["inventory"],
                                confidence="high",
                                freshness="fresh",
                                observed_state=model_group,
                            ))

        services = ctx.get("services", {})
        if isinstance(services, dict):
            for svc_group in ("core", "support", "observability"):
                svc_list = services.get(svc_group, [])
                if isinstance(svc_list, list):
                    for svc in svc_list:
                        if isinstance(svc, str):
                            self._entities["service"].append(ObservedEntity(
                                name=svc,
                                entity_type="service",
                                source_of_truth=["code"],
                                confidence="high",
                                freshness="fresh",
                                observed_state=svc_group,
                            ))
                        elif isinstance(svc, dict):
                            sname = svc.get("name", svc.get("id", "?"))
                            if sname:
                                self._entities["service"].append(ObservedEntity(
                                    name=str(sname),
                                    entity_type="service",
                                    source_of_truth=["code"],
                                    confidence="high",
                                    freshness="fresh",
                                    observed_state=svc_group,
                                ))

        topology_mode = ctx.get("topology_mode") or ctx.get("runtime_topology", {}).get("mode")
        if topology_mode:
            self._entities["topology_mode"].append(ObservedEntity(
                name=str(topology_mode),
                entity_type="topology_mode",
                source_of_truth=["sensor_fusion"],
                confidence="high",
                freshness="fresh",
            ))

        sensor_snap = ctx.get("sensor_snapshot", {})
        if isinstance(sensor_snap, dict):
            fs_usage = sensor_snap.get("observed_data", {}).get("system_node", {}).get("fs_usage_pct")
            if fs_usage is not None:
                self._entities["storage"].append(ObservedEntity(
                    name="root_disk",
                    entity_type="storage",
                    source_of_truth=["prometheus"],
                    confidence="high",
                    freshness="fresh",
                    observed_state=f"{fs_usage}% used",
                ))
            archive_path = "/mnt/opencode/ai-lab-archives"
            self._entities["storage"].append(ObservedEntity(
                name="nas_archive",
                entity_type="storage",
                source_of_truth=["code"],
                confidence="high",
                freshness="fresh",
                observed_state=archive_path,
            ))

    def is_observed(self, entity_type: str, name: str) -> bool:
        if entity_type not in self._entities:
            return False
        nl = name.lower().strip()
        for e in self._entities[entity_type]:
            if e.name.lower().strip() == nl:
                return True
        return False

    def get_observed_entities(self) -> dict[str, list[dict[str, Any]]]:
        return {
            etype: [self._entity_to_dict(e) for e in entities]
            for etype, entities in self._entities.items()
        }

    def _entity_to_dict(self, e: ObservedEntity) -> dict[str, Any]:
        return {
            "name": e.name,
            "entity_type": e.entity_type,
            "source_of_truth": e.source_of_truth,
            "confidence": e.confidence,
            "freshness": e.freshness,
            "observed_state": e.observed_state,
            "host": e.host,
        }

    def get_known_gpus(self) -> list[str]:
        return [e.name for e in self._entities.get("gpu", [])]

    def get_known_models(self) -> list[str]:
        return [e.name for e in self._entities.get("model", [])]

    def get_known_hosts(self) -> list[str]:
        return [e.name for e in self._entities.get("host", [])]

    def get_known_services(self) -> list[str]:
        return [e.name for e in self._entities.get("service", [])]

    def get_forbidden_patterns(self) -> dict[str, set[str]]:
        return {
            "forbidden_gpus": {"a100", "h100", "h200", "b100", "b200", "v100", "t4", "l4", "l40s", "a10", "a16", "mi250", "mi300", "mi350"},
            "forbidden_platforms": {"aws", "gcp", "azure", "amazon", "ec2", "s3", "lambda", "google cloud", "oracle cloud", "heroku", "digitalocean"},
            "forbidden_orchestration": {"kubernetes", "k8s", "spark", "dask", "ray", "docker swarm", "openshift", "rancher", "terraform", "ansible"},
            "forbidden_security": {"selinux", "apparmor", "fail2ban", "wazuh", "snort", "suricata"},
        }


# ── FASE 31E: Backward-compat shim — delegate to runtime/entities ──

def build_entity_registry(sensor_snapshot=None, extra_ctx=None):
    return _31e_build_entity_registry(sensor_snapshot, extra_ctx)

def build_active_entities(sensor_snapshot=None, extra_ctx=None):
    return _31e_build_active_entities(sensor_snapshot, extra_ctx)

def build_inventory_entities(sensor_snapshot=None, extra_ctx=None):
    return _31e_build_inventory_entities(sensor_snapshot, extra_ctx)

def build_discoverable_entities(sensor_snapshot=None, extra_ctx=None):
    return _31e_build_discoverable_entities(sensor_snapshot, extra_ctx)

def build_deprecated_entities(sensor_snapshot=None, extra_ctx=None):
    return _31e_build_deprecated_entities(sensor_snapshot, extra_ctx)

def build_routability_summary(sensor_snapshot=None, extra_ctx=None):
    return _31e_build_routability_summary(sensor_snapshot, extra_ctx)

def build_topology_preparation(sensor_snapshot=None, extra_ctx=None):
    return _31e_build_topology_preparation(sensor_snapshot, extra_ctx)

def classify_entity_state(inventory_state, observed_state, operational_state, *, inventory_expected_offline=False, deprecated=False, disabled=False):
    return _31e_classify_entity_state(inventory_state, observed_state, operational_state, inventory_expected_offline=inventory_expected_offline, deprecated=deprecated, disabled=disabled)

def classify_operational_state(observed_state, *, has_recent_traffic=False, is_loaded_in_backend=False, expected_offline=False):
    return _31e_classify_operational_state(observed_state, has_recent_traffic=has_recent_traffic, is_loaded_in_backend=is_loaded_in_backend, expected_offline=expected_offline)

def classify_discoverability(*, endpoint_responds=False, visible_in_inventory=False, observed_state=None):
    return _31e_classify_discoverability(endpoint_responds=endpoint_responds, visible_in_inventory=visible_in_inventory, observed_state=observed_state)

def classify_routability(entity_type, entity_id, *, deprecated=False, disabled=False, operational_state=None, expected_offline=False):
    return _31e_classify_routability(entity_type, entity_id, deprecated=deprecated, disabled=disabled, operational_state=operational_state, expected_offline=expected_offline)

def detect_stale_entities(sensor_snapshot=None, extra_ctx=None):
    return _31e_detect_stale_entities(sensor_snapshot, extra_ctx)

def detect_inventory_only_entities(sensor_snapshot=None, extra_ctx=None):
    return _31e_detect_inventory_only_entities(sensor_snapshot, extra_ctx)

def detect_deprecated_entities(sensor_snapshot=None, extra_ctx=None):
    return _31e_detect_deprecated_entities(sensor_snapshot, extra_ctx)
