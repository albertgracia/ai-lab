import csv
import io
import json
import subprocess


GPU_NODES = [
    {
        "name": "Gaming PC RX9070XT",
        "host": "192.168.1.50",
        "user": "ailab",
        "vram_total_gb": 16
    },
    {
        "name": "Gaming PC RX7900XT",
        "host": "192.168.1.60",
        "user": "ailab",
        "vram_total_gb": 20
    }
]


def run_ssh(node, command):
    result = subprocess.run(
        [
            "ssh",
            "-i", "/opt/ai-lab/key_saved",
            "-o", "IdentitiesOnly=yes",
            f"{node['user']}@{node['host']}",
            command
        ],
        capture_output=True,
        text=True,
        encoding="cp1252",
        errors="ignore",
        timeout=20
    )

    return {
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip()
    }


def parse_typeperf_csv(output):
    lines = [
        line for line in output.splitlines()
        if line.startswith('"')
    ]

    if len(lines) < 2:
        return []

    reader = csv.reader(io.StringIO("\n".join(lines)))
    rows = list(reader)

    headers = rows[0][1:]
    values = rows[1][1:]

    samples = []

    for path, value in zip(headers, values):
        try:
            numeric = float(value.replace(",", "."))
        except Exception:
            numeric = 0.0

        samples.append({
            "path": path,
            "value": numeric
        })

    return samples


def get_gpu_utilization(node):
    cmd = r'typeperf "\GPU Engine(*)\Utilization Percentage" -sc 1'

    result = run_ssh(node, cmd)

    if result["returncode"] != 0:
        return {
            "error": result["stderr"]
        }

    samples = parse_typeperf_csv(result["stdout"])

    nonzero = [
        sample for sample in samples
        if sample["value"] > 0
    ]

    max_usage = max(
        [sample["value"] for sample in samples],
        default=0.0
    )

    return {
        "max_gpu_usage_percent": round(max_usage, 2),
        "active_engines": nonzero[:10]
    }


def get_vram_usage(node):
    cmd = r'typeperf "\GPU Adapter Memory(*)\Dedicated Usage" -sc 1'

    result = run_ssh(node, cmd)

    if result["returncode"] != 0:
        return {
            "error": result["stderr"]
        }

    samples = parse_typeperf_csv(result["stdout"])

    max_bytes = max(
        [sample["value"] for sample in samples],
        default=0.0
    )

    used_gib = max_bytes / (1024 ** 3)
    total_gib = node["vram_total_gb"]
    free_gib = total_gib - used_gib

    return {
        "vram_used_gib": round(used_gib, 2),
        "vram_total_gib": total_gib,
        "vram_free_gib_estimated": round(free_gib, 2),
        "raw_samples": samples[:5]
    }


def get_gpu_state_for_node(node):
    return {
        "node": node["name"],
        "host": node["host"],
        "gpu_usage": get_gpu_utilization(node),
        "vram": get_vram_usage(node)
    }


def build_gpu_state():
    return [
        get_gpu_state_for_node(node)
        for node in GPU_NODES
    ]


if __name__ == "__main__":
    print(json.dumps(build_gpu_state(), indent=2))