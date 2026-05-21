from typing import Any

from runtime.context.sensor_fusion import RuntimeSensorFusionSnapshot


class OperationalSummaryBuilder:
    @staticmethod
    def build(snapshot: RuntimeSensorFusionSnapshot, route_family: str = "cognitive") -> dict[str, str]:
        summaries: dict[str, str] = {}
        summaries["gpu_summary"] = OperationalSummaryBuilder._gpu_summary(snapshot)
        summaries["routing_summary"] = OperationalSummaryBuilder._routing_summary(snapshot)
        summaries["slo_summary"] = OperationalSummaryBuilder._slo_summary(snapshot)
        summaries["storage_summary"] = OperationalSummaryBuilder._storage_summary(snapshot)

        if route_family in ("minimal", "observe"):
            return {"gpu_summary": summaries["gpu_summary"]}
        if route_family == "report":
            return summaries
        return summaries

    @staticmethod
    def _gpu_summary(snapshot: RuntimeSensorFusionSnapshot) -> str:
        parts = []
        for gpu in snapshot.topology.active_gpus:
            name = gpu.get("name", "?")
            vram = gpu.get("vram_gb", "?")
            temp = gpu.get("gpu_temp_c")
            load = gpu.get("gpu_load_pct")
            power = gpu.get("gpu_power_w")
            fan = gpu.get("gpu_fan_rpm")
            detail = f"{name}: {vram}GB VRAM"
            if load is not None:
                detail += f", {load:.0f}% load"
            if temp is not None:
                detail += f", {temp:.0f}°C"
            if power is not None:
                detail += f", {power:.0f}W"
            if fan is not None:
                detail += f", fan {fan:.0f}RPM"
            parts.append(detail)
        for gpu in snapshot.topology.inventory_gpus:
            name = gpu.get("name", "?")
            vram = gpu.get("vram_gb", "?")
            status = gpu.get("status", "offline")
            parts.append(f"{name}: {vram}GB VRAM, {status} (inventory)")
        if not parts:
            return "NO DISPONIBLE"
        return " | ".join(parts)

    @staticmethod
    def _routing_summary(snapshot: RuntimeSensorFusionSnapshot) -> str:
        gateway_data = snapshot.observed_data.get("gateway", {})
        if not isinstance(gateway_data, dict):
            return "NO DISPONIBLE"
        route_families = gateway_data.get("route_families")
        if route_families and isinstance(route_families, list):
            families = {}
            for r in route_families:
                fam = r.get("metric", {}).get("family", "?")
                try:
                    val = float(r.get("value", ["0", "0"])[1])
                except (ValueError, TypeError, IndexError):
                    val = 0
                families[fam] = int(val)
            if families:
                summary = ", ".join(f"{k}={v}" for k, v in sorted(families.items()))
                return f"Route families: {summary}"
        return "NO DISPONIBLE"

    @staticmethod
    def _slo_summary(snapshot: RuntimeSensorFusionSnapshot) -> str:
        gateway_data = snapshot.observed_data.get("gateway", {})
        if not isinstance(gateway_data, dict):
            return "NO DISPONIBLE"
        slo = gateway_data.get("slo_state")
        deg = gateway_data.get("degradation_level")
        parts = []
        if slo is not None:
            slo_str = {0: "green", 1: "yellow", 2: "red"}.get(int(slo), str(slo))
            parts.append(f"SLO state: {slo_str}")
        else:
            parts.append("SLO state: disabled")
        if deg is not None:
            deg_str = {0: "normal", 1: "light", 2: "heavy", 3: "emergency"}.get(int(deg), str(deg))
            parts.append(f"Degradation: {deg_str}")
        else:
            parts.append("Degradation: NORMAL")
        parts.append("Enforcement: dry-run")
        return " | ".join(parts)

    @staticmethod
    def _storage_summary(snapshot: RuntimeSensorFusionSnapshot) -> str:
        sys_data = snapshot.observed_data.get("system_node", {})
        if not isinstance(sys_data, dict):
            return "NO DISPONIBLE"
        parts = []
        mem_total = sys_data.get("mem_total_bytes")
        mem_avail = sys_data.get("mem_available_bytes")
        if mem_total and mem_avail:
            mem_gb = round(mem_total / (1024**3), 1)
            mem_used = round((mem_total - mem_avail) / (1024**3), 1)
            mem_pct = sys_data.get("mem_usage_pct", 0)
            parts.append(f"RAM: {mem_used}GB / {mem_gb}GB ({mem_pct:.0f}%)")
        fs_avail = sys_data.get("fs_avail_bytes")
        fs_size = sys_data.get("fs_size_bytes")
        if fs_size:
            fs_total_gb = round(fs_size / (1024**3), 1)
            if fs_avail:
                fs_used_gb = round((fs_size - fs_avail) / (1024**3), 1)
                fs_pct = sys_data.get("fs_usage_pct", 0)
                parts.append(f"Disk: {fs_used_gb}GB / {fs_total_gb}GB ({fs_pct:.0f}%)")
            else:
                parts.append(f"Disk: {fs_total_gb}GB total")
        smartctl = snapshot.derived_state.get("smartctl", {})
        if smartctl.get("health") == "ok":
            parts.append("SMART: UP")
        elif smartctl.get("health") == "down":
            parts.append("SMART: DOWN")
        if not parts:
            return "NO DISPONIBLE"
        return " | ".join(parts)
