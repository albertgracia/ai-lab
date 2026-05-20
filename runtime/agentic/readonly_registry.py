from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ExecutionCapability(Enum):
    READONLY = "readonly"
    SANDBOX_WRITE = "sandbox_write"
    SYSTEM_WRITE = "system_write"


CURRENT_CAPABILITY = ExecutionCapability.READONLY


@dataclass(frozen=True)
class ReadonlyCommandSpec:
    command: str
    category: str
    risk: str
    local_only: bool = True
    requires_args_validation: bool = False


SAFE_READONLY_COMMANDS: dict[str, ReadonlyCommandSpec] = {
    "docker": ReadonlyCommandSpec("docker", "docker", "medium", requires_args_validation=True),
    "systemctl": ReadonlyCommandSpec("systemctl", "system", "medium", requires_args_validation=True),
    "journalctl": ReadonlyCommandSpec("journalctl", "logs", "low", requires_args_validation=True),
    "cat": ReadonlyCommandSpec("cat", "filesystem", "low"),
    "ls": ReadonlyCommandSpec("ls", "filesystem", "low"),
    "df": ReadonlyCommandSpec("df", "system", "low"),
    "free": ReadonlyCommandSpec("free", "system", "low"),
    "uptime": ReadonlyCommandSpec("uptime", "system", "low"),
    "ps": ReadonlyCommandSpec("ps", "process", "low"),
    "top": ReadonlyCommandSpec("top", "process", "low"),
    "ss": ReadonlyCommandSpec("ss", "network", "low"),
    "ip": ReadonlyCommandSpec("ip", "network", "low"),
    "who": ReadonlyCommandSpec("who", "system", "low"),
    "date": ReadonlyCommandSpec("date", "system", "low"),
    "uname": ReadonlyCommandSpec("uname", "system", "low"),
    "curl": ReadonlyCommandSpec("curl", "network", "medium", local_only=True, requires_args_validation=True),
    "wc": ReadonlyCommandSpec("wc", "filesystem", "low"),
    "head": ReadonlyCommandSpec("head", "filesystem", "low"),
    "tail": ReadonlyCommandSpec("tail", "filesystem", "low"),
    "grep": ReadonlyCommandSpec("grep", "filesystem", "low"),
    "find": ReadonlyCommandSpec("find", "filesystem", "low", requires_args_validation=True),
    "du": ReadonlyCommandSpec("du", "filesystem", "low"),
    "stat": ReadonlyCommandSpec("stat", "filesystem", "low"),
    "file": ReadonlyCommandSpec("file", "filesystem", "low"),
    "nproc": ReadonlyCommandSpec("nproc", "system", "low"),
    "lscpu": ReadonlyCommandSpec("lscpu", "system", "low"),
    "lspci": ReadonlyCommandSpec("lspci", "system", "low"),
}


FORBIDDEN_READONLY_COMMANDS: set[str] = {
    "rm", "mv", "cp", "chmod", "chown", "dd", "tee",
    "apt", "apt-get", "dpkg", "yum", "dnf", "pacman",
    "sudo",
    "shutdown", "reboot", "poweroff", "halt",
    "mkfs", "fdisk", "parted",
    "mount", "umount",
    "iptables", "nft", "ufw",
    "wget",
}

FORBIDDEN_READONLY_PATTERNS: set[str] = {
    "systemctl restart", "systemctl stop", "systemctl disable",
    "systemctl enable", "systemctl start",
    "docker stop", "docker rm", "docker kill", "docker compose",
    "docker exec", "docker cp", "docker run", "docker build",
    "docker push", "docker pull", "docker attach",
    "sed -i", "sed --in-place",
    "curl -o", "curl -O", "curl --output",
}

DANGEROUS_OPERATORS: frozenset = frozenset({"|", "||", "&&", ";", "&"})
DANGEROUS_REDIRECTS: frozenset = frozenset({">", ">>", "<", "<<", "2>", "&>", "1>"})
DANGEROUS_TOKENS: frozenset = frozenset({"$(", "`", "/dev/"})

FIND_ALLOWED_PATHS: tuple[str, ...] = ("/opt/ai-lab", "/tmp", "/var/log", "/home/albert")

DOCKER_ALLOWED_SUBCOMMANDS: set[str] = {"ps", "stats", "inspect", "logs"}
DOCKER_BLOCKED_SUBCOMMANDS: set[str] = {"exec", "cp", "compose", "attach", "run", "build", "push", "pull"}

RFC1918_PATTERNS: tuple[str, ...] = (
    "127.0.0.1", "localhost",
    "192.168.", "10.", "172.16.", "172.17.", "172.18.", "172.19.",
    "172.20.", "172.21.", "172.22.", "172.23.", "172.24.", "172.25.",
    "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.",
)
