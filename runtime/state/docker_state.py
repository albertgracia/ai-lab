import json
import subprocess


def run(cmd):
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True
    )

    return result.stdout.strip()


def get_docker_state():
    containers_raw = run(
        "docker ps --format '{{json .}}'"
    )

    containers = []

    for line in containers_raw.splitlines():
        try:
            containers.append(json.loads(line))
        except Exception:
            pass

    return {
        "containers": containers
    }