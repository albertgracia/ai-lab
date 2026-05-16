"""EXECUTE v1 — command sandbox whitelist.

EXECUTE mode v1 SOLO permite:
  ✅ archivos temporales (/tmp/ai-lab/)
  ✅ scripts sandbox
  ✅ dry-run
  ✅ comandos readonly
  ✅ análisis
  ✅ validación
  ✅ generación de planes

PROHIBIDO:
  ❌ Docker
  ❌ systemctl (except status)
  ❌ network (curl permitido solo a localhost/health)
  ❌ filesystem fuera de /tmp/ai-lab/ y /opt/ai-lab/
  ❌ Hyper-V
  ❌ UniFi
  ❌ Cloudflare API
  ❌ shell=True (nunca)
"""

import shlex

# ── comandos permitidos (prefijos exactos) ────────────────────────────
_ALLOWED_PREFIXES = [
    "ls ",
    "pwd",
    "cat ",
    "echo ",
    "head ",
    "tail ",
    "wc ",
    "sort ",
    "grep ",
    "find ",
    "which ",
    "date",
    "whoami",
    "id",
    "uname ",
    "uptime",
    "df -h",
    "free -h",
    "ps aux",
    "env",
    "printenv",
    "python3 ",
]

_ALLOWED_EXACT = {
    "pwd",
    "date",
    "whoami",
    "id",
    "uptime",
    "env",
    "printenv",
}

# ── prefijos PROHIBIDOS (incluso si pasan la whitelist) ───────────────
_BLOCKED_PREFIXES = [
    "docker",
    "systemctl restart",
    "systemctl stop",
    "systemctl start",
    "systemctl enable",
    "systemctl disable",
    "systemctl daemon-reload",
    "sudo",
    "su ",
    "chmod",
    "chown",
    "mount",
    "umount",
    "mkfs",
    "dd ",
    "shutdown",
    "reboot",
    "poweroff",
    "iptables",
    "ip link",
    "ip addr",
    "ip route",
    "virsh",
    "curl -X POST",
    "wget",
    "git push",
    "git commit",
    "git merge",
    "gh ",
    "cloudflare",
    "unifi",
    "hyper-v",
    "ssh ",
    "scp ",
    "rsync ",
    "kill ",
    "pkill ",
    "tmux",
    "screen",
    "nohup ",
    "apt",
    "pip install",
    "npm install",
    "yarn add",
    "rm -rf /",
    "rm -rf ~",
    "rm -rf .",
    "> /",     # redirect to root
    "| sh",
    "| bash",
    "`",
    "$(",
]

# ── patterns que requieren dry-run mode ────────────────────────────────
_DRY_RUN_REQUIRED = [
    "python3 ",
    "cat > ",
    "echo > ",
    ">>",
]


def is_allowed(command: str) -> tuple[bool, str]:
    """Check if a command is allowed in EXECUTE v1 mode.

    Returns:
        (allowed: bool, reason: str)
    """
    if not command or not command.strip():
        return False, "empty command"

    stripped = command.strip()

    # Check blocked prefixes first
    lower = stripped.lower()
    for bp in _BLOCKED_PREFIXES:
        if lower.startswith(bp):
            return False, f"blocked by EXECUTE v1 policy: {bp}"

    # Check for dangerous patterns
    if " 2>" in stripped or " 1>" in stripped or " &>" in stripped:
        if not stripped.startswith("cat ") and not stripped.startswith("echo "):
            return False, "redirect blocked (use dry-run)"

    # Check allowed exact commands
    if stripped in _ALLOWED_EXACT:
        return True, ""

    # Check allowed prefixes
    for prefix in _ALLOWED_PREFIXES:
        if stripped.startswith(prefix):
            # Check if it requires dry-run
            for dr in _DRY_RUN_REQUIRED:
                if stripped.startswith(dr):
                    return False, f"requires dry-run mode: {dr}"
            return True, ""

    return False, f"not in EXECUTE v1 whitelist: {stripped.split()[0] if stripped.split() else '?'}"


def dry_run_allowed(command: str) -> bool:
    """Whether this command can at least run as dry-run (print, not execute)."""
    stripped = command.strip()
    lower = stripped.lower()
    for bp in _BLOCKED_PREFIXES:
        if lower.startswith(bp):
            return False
    return True
