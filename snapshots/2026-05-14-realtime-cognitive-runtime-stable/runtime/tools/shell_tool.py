import subprocess


SAFE_COMMANDS = [
    "ls",
    "pwd",
    "cat",
    "head",
    "tail",
    "find",
    "grep",
    "docker ps",
    "docker logs",
    "docker inspect",
    "git status",
    "git log",
    "git diff",
    "df -h",
    "free -h",
    "ps aux",
]


BLOCKED_PATTERNS = [
    "rm ",
    "mkfs",
    "shutdown",
    "reboot",
    "dd ",
    ">:",
    "chmod 777",
    "iptables",
    "ufw delete",
    "docker compose down",
]


def is_safe(command: str) -> bool:
    lower = command.lower()

    for blocked in BLOCKED_PATTERNS:
        if blocked in lower:
            return False

    return any(lower.startswith(cmd) for cmd in SAFE_COMMANDS)


def execute(command: str):
    if not is_safe(command):
        return {
            "success": False,
            "error": f"Blocked unsafe command: {command}"
        }

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )

        return {
            "success": True,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


if __name__ == "__main__":
    while True:
        cmd = input("Command> ")

        if cmd in ["exit", "quit"]:
            break

        print(execute(cmd))
