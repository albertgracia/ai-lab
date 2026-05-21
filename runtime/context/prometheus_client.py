import json
import time
import requests
from typing import Any

PROMETHEUS_BASE_URL = "http://192.168.1.40:9090"
QUERY_TIMEOUT = 2.0
CACHE_TTL = 5.0


class PrometheusQueryClient:
    def __init__(self, base_url: str = PROMETHEUS_BASE_URL, timeout: float = QUERY_TIMEOUT, cache_ttl: float = CACHE_TTL):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.cache_ttl = cache_ttl
        self._cache: dict[str, tuple[float, Any]] = {}

    def query(self, query: str) -> list[dict] | None:
        now = time.time()
        cached = self._cache.get(query)
        if cached and (now - cached[0]) < self.cache_ttl:
            return cached[1]
        result = self._make_request(query)
        self._cache[query] = (now, result)
        return result

    def query_first(self, query: str) -> dict | None:
        results = self.query(query)
        if results and len(results) > 0:
            return results[0]
        return None

    def _make_request(self, query: str) -> list[dict] | None:
        try:
            resp = requests.get(
                f"{self.base_url}/api/v1/query",
                params={"query": query},
                timeout=self.timeout,
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            results = data.get("data", {}).get("result", [])
            return results
        except (requests.ConnectionError, requests.Timeout, json.JSONDecodeError, KeyError):
            return None

    def get_target_up(self, job: str) -> dict | None:
        result = self.query_first(f'up{{job="{job}"}}')
        if result is None:
            return None
        metric = result.get("metric", {})
        value_str = result.get("value", ["0", "0"])[1]
        return {
            "job": job,
            "instance": metric.get("instance", "?"),
            "value": int(float(value_str)),
            "source_of_truth": "prometheus",
        }

    def query_instant(self, query: str) -> float | None:
        result = self.query_first(query)
        if result is None:
            return None
        try:
            return float(result.get("value", ["0", "0"])[1])
        except (ValueError, TypeError, IndexError):
            return None

    def query_instant_with_metric(self, query: str) -> dict | None:
        result = self.query_first(query)
        if result is None:
            return None
        metric = result.get("metric", {})
        try:
            value = float(result.get("value", ["0", "0"])[1])
        except (ValueError, TypeError, IndexError):
            value = None
        return {
            "value": value,
            "metric": metric,
            "source_of_truth": "prometheus",
        }

    def query_gpu_metrics(self) -> dict | None:
        gpu_results = self.query('{__name__=~".*gpu.*",instance="192.168.1.50:9183"}')
        if gpu_results is None or len(gpu_results) == 0:
            return None
        collected: dict[str, Any] = {"source_of_truth": "prometheus"}
        for r in gpu_results:
            name = r.get("metric", {}).get("__name__", "")
            sensor = r.get("metric", {}).get("sensor", "")
            gpu_name = r.get("metric", {}).get("gpu", "")
            try:
                val = float(r.get("value", ["0", "0"])[1])
            except (ValueError, TypeError, IndexError):
                continue
            if not sensor:
                continue
            sensor_key = sensor.lower().replace(' ', '_').replace('-', '_')
            if sensor_key.startswith("gpu_"):
                sensor_key = sensor_key[4:]
            if name == "gpu_smalldata":
                collected[f"gpu_{sensor_key}"] = val
            elif name == "gpu_load_percent":
                collected[f"load_{sensor.lower().replace(' ','_').replace('-','_')}"] = val
            elif name == "gpu_temperature_celsius":
                collected[f"temp_{sensor.lower().replace(' ','_').replace('-','_')}_c"] = val
            elif name == "gpu_power_watts":
                collected[f"power_{sensor.lower().replace(' ','_').replace('-','_')}_w"] = val
            elif name == "gpu_fan_speed_rpm":
                collected[f"fan_{sensor.lower().replace(' ','_').replace('-','_')}_rpm"] = val
            elif name == "gpu_clock_mhz":
                collected[f"clock_{sensor.lower().replace(' ','_').replace('-','_')}_mhz"] = val
            elif name == "gpu_voltage":
                collected[f"voltage_{sensor.lower().replace(' ','_').replace('-','_')}_v"] = val
            elif name == "gpu_control":
                collected[f"control_{sensor.lower().replace(' ','_').replace('-','_')}"] = val
            elif name == "gpu_factor":
                collected[f"factor_{sensor.lower().replace(' ','_').replace('-','_')}"] = val
            else:
                collected[f"{name}_{sensor.lower().replace(' ','_').replace('-','_')}"] = val
        collected["gpu_name"] = gpu_name
        return collected

    def freshness(self, last_scrape_seconds: float | None) -> str:
        if last_scrape_seconds is None:
            return "unknown"
        if last_scrape_seconds < 10:
            return "fresh"
        if last_scrape_seconds < 60:
            return "stale"
        return "expired"

    def clear_cache(self) -> None:
        self._cache.clear()
