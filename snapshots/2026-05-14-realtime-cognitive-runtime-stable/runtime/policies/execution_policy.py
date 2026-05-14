DANGEROUS_PATTERNS = [
    "rm -rf",
    "mkfs",
    "dd if=",
    "shutdown",
    "reboot",
    "poweroff",
    "docker compose down",
    "docker rm",
    "docker volume rm",
    "docker system prune",
    "systemctl restart",
    "systemctl stop",
    "systemctl disable",
]

REQUIRES_EXECUTE_MODE = [
    "docker ",
    "docker-compose ",
    "systemctl ",
    "service ",
    "ufw ",
    "iptables ",
    "nft ",
    "mount ",
    "umount ",
]


def command_risk(command: str) -> str:
    normalized = command.strip().lower()

    for pattern in DANGEROUS_PATTERNS:
        if pattern in normalized:
            return "high"

    for pattern in REQUIRES_EXECUTE_MODE:
        if normalized.startswith(pattern):
            return "medium"

    return "low"


def is_command_allowed(mode_name: str, command: str) -> bool:
    risk = command_risk(command)

    if risk == "high":
        return mode_name == "execute"

    if risk == "medium":
        return mode_name in {"execute"}

    return mode_name in {"readonly", "build", "execute"}


def explain_command(mode_name: str, command: str):
    return {
        "mode": mode_name,
        "command": command,
        "risk": command_risk(command),
        "allowed": is_command_allowed(mode_name, command),
    }


if __name__ == "__main__":
    tests = [
        ("readonly", "ls -la"),
        ("build", "python3 -m py_compile runtime/llm/router_api.py"),
        ("build", "systemctl restart ialab-router-api"),
        ("execute", "systemctl restart ialab-router-api"),
        ("execute", "rm -rf /opt/ai-lab"),
    ]

    for mode, cmd in tests:
        print(explain_command(mode, cmd))
