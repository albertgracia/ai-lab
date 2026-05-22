import time
import requests

from runtime.maturity.descriptor import ModelStatus, TemporalState

LMSTUDIO_NODES = [
    {
        "name": "Main LM Studio",
        "host": "192.168.1.200",
        "port": 1234
    },
    {
        "name": "Gaming PC RX7900XT",
        "host": "192.168.1.60",
        "port": 1234
    },
    {
        "name": "Gaming PC RX9070XT",
        "host": "192.168.1.50",
        "port": 1234
    }
]

# RULE-30B-3: ACTIVE window
ACTIVE_WINDOW_SECONDS = 300

# RULE-30B-6: Alias normalization map
_ALIAS_MAP: dict[str, str] = {
    "qwen/": "",
    "lmstudio-community/": "",
    "hugging-quants/": "",
}

# FASE 30I-F0: deprecated model prefixes — hidden from operational inventory
_DEPRECATED_PREFIXES: tuple[str, ...] = (
    "lmstudio-community/qwen2.5-coder-14b-instruct",
)


def normalize_model_id(model_id: str) -> str:
    normalized = model_id.strip()
    for prefix, replacement in _ALIAS_MAP.items():
        if normalized.startswith(prefix):
            normalized = replacement + normalized[len(prefix):]
            break
    return normalized


class ModelStatusTracker:
    def __init__(self) -> None:
        self._statuses: dict[str, ModelStatus] = {}
        self._temporal: dict[str, TemporalState] = {}
        self._node_map: dict[str, str] = {}
        self._disabled_ids: set[str] = set()

    def set_disabled_ids(self, ids: list[str]) -> None:
        self._disabled_ids = {normalize_model_id(i) for i in ids}

    def set_model_node(self, model_id: str, node_name: str) -> None:
        normalized = normalize_model_id(model_id)
        self._node_map[normalized] = node_name

    # RULE-30B-4: DISABLED has absolute priority
    def get_status(self, model_id: str) -> ModelStatus:
        normalized = normalize_model_id(model_id)
        candidate = self._statuses.get(normalized, ModelStatus.DISCOVERABLE)
        return self._final_status(normalized, candidate)

    def get_temporal(self, model_id: str) -> TemporalState:
        normalized = normalize_model_id(model_id)
        if normalized not in self._temporal:
            self._temporal[normalized] = TemporalState()
        return self._temporal[normalized]

    def _final_status(self, normalized: str, candidate: ModelStatus) -> ModelStatus:
        if normalized in self._disabled_ids:
            return ModelStatus.DISABLED
        return candidate

    def set_status(self, model_id: str, status: ModelStatus, error: str = "") -> None:
        normalized = normalize_model_id(model_id)
        if normalized not in self._temporal:
            self._temporal[normalized] = TemporalState()
        ts = self._temporal[normalized]
        old = self._statuses.get(normalized)
        if old != status:
            ts.transition_count += 1
        if error:
            ts.record_error(error)
        ts.touch()
        self._statuses[normalized] = status

    def mark_active(self, model_id: str) -> None:
        normalized = normalize_model_id(model_id)
        if normalized in self._disabled_ids:
            return
        if normalized not in self._temporal:
            self._temporal[normalized] = TemporalState()
        ts = self._temporal[normalized]
        old = self._statuses.get(normalized)
        if old != ModelStatus.ACTIVE:
            ts.transition_count += 1
        ts.record_route()
        ts.touch()
        self._statuses[normalized] = ModelStatus.ACTIVE

    def mark_error(self, model_id: str, error: str) -> None:
        self.set_status(model_id, ModelStatus.UNAVAILABLE, error=error)

    # RULE-30B-3: ACTIVE TTL
    def expire_active_models(self) -> list[str]:
        now = time.time()
        expired: list[str] = []
        for model_id, status in list(self._statuses.items()):
            if status != ModelStatus.ACTIVE:
                continue
            ts = self._temporal.get(model_id)
            if ts and (now - ts.last_routed) > ACTIVE_WINDOW_SECONDS:
                self._statuses[model_id] = ModelStatus.LOADED
                ts.transition_count += 1
                expired.append(model_id)
        return expired

    # RULE-30B-5: Inventory/offline nodes never ACTIVE
    def is_node_active_capable(self, node_host: str) -> bool:
        return node_host not in ("192.168.1.200", "192.168.1.60")

    def rebuild_from_nodes(self) -> None:
        from runtime.state.lmstudio_state import LMSTUDIO_NODES

        self.expire_active_models()
        seen_normalized: set[str] = set()
        node_models: dict[str, list[str]] = {}

        for node_def in LMSTUDIO_NODES:
            host = node_def["host"]
            try:
                result = get_models(node_def)
            except Exception:
                continue

            node_name = node_def["name"]
            node_models[node_name] = []

            if not result.get("online"):
                continue

            for raw_id in result.get("models", []):
                # FASE 30I-F0: skip deprecated model prefixes in operational inventory
                if any(raw_id.startswith(prefix) for prefix in _DEPRECATED_PREFIXES):
                    continue
                normalized = normalize_model_id(raw_id)
                self.set_model_node(normalized, node_name)
                seen_normalized.add(normalized)
                node_models[node_name].append(normalized)

                if normalized in self._disabled_ids:
                    self.set_status(normalized, ModelStatus.DISABLED)
                elif not self.is_node_active_capable(host):
                    self.set_status(normalized, ModelStatus.DISCOVERABLE)
                elif self._statuses.get(normalized) == ModelStatus.ACTIVE:
                    pass
                else:
                    self.set_status(normalized, ModelStatus.LOADED)

        for node_name, models in node_models.items():
            for normalized in models:
                self._node_map[normalized] = node_name

    def to_dict(self) -> dict[str, dict]:
        result: dict[str, dict] = {}
        all_ids = set(self._statuses.keys()) | set(self._disabled_ids)
        for model_id in sorted(all_ids):
            normalized = normalize_model_id(model_id)
            status = self._final_status(normalized, self._statuses.get(normalized, ModelStatus.DISCOVERABLE))
            ts = self._temporal.get(normalized)
            result[normalized] = {
                "status": status.value,
                "loaded": status in (ModelStatus.LOADED, ModelStatus.ACTIVE),
                "routable": status == ModelStatus.ACTIVE,
                "disabled": normalized in self._disabled_ids,
                "deprecated": any(
                    normalized == normalize_model_id(prefix)
                    for prefix in _DEPRECATED_PREFIXES
                ),
                "node": self._node_map.get(normalized, ""),
                "transition_count": ts.transition_count if ts else 0,
                "last_routed": ts.last_routed if ts else 0.0,
                "temporal": ts.to_dict() if ts else {},
            }
        return result


_TRACKER: ModelStatusTracker | None = None


def get_model_tracker() -> ModelStatusTracker:
    global _TRACKER
    if _TRACKER is None:
        _TRACKER = ModelStatusTracker()
        try:
            from runtime.state.runtime_state import RUNTIME_STATE
            disabled_raw = RUNTIME_STATE.get("disabled_models", [])
            if disabled_raw:
                _TRACKER.set_disabled_ids(disabled_raw)
        except Exception:
            pass
        _TRACKER.rebuild_from_nodes()
    return _TRACKER


def get_models(node):
    url = f"http://{node['host']}:{node['port']}/v1/models"

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()

        data = response.json()

        return {
            "node": node["name"],
            "host": node["host"],
            "port": node["port"],
            "online": True,
            "models": [
                model["id"]
                for model in data.get("data", [])
            ]
        }

    except Exception as e:
        return {
            "node": node["name"],
            "host": node["host"],
            "port": node["port"],
            "online": False,
            "error": str(e)
        }


def get_lmstudio_state():
    return {
        "lmstudio_nodes": [
            get_models(node)
            for node in LMSTUDIO_NODES
        ]
    }
