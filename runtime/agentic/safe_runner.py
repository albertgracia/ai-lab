from __future__ import annotations

import shlex
import subprocess
import hashlib
import time
from typing import Any

from runtime.agentic.readonly_registry import (
    SAFE_READONLY_COMMANDS,
    FORBIDDEN_READONLY_COMMANDS,
    FORBIDDEN_READONLY_PATTERNS,
    DANGEROUS_OPERATORS,
    DANGEROUS_REDIRECTS,
    DANGEROUS_TOKENS,
    FIND_ALLOWED_PATHS,
    DOCKER_ALLOWED_SUBCOMMANDS,
    DOCKER_BLOCKED_SUBCOMMANDS,
    RFC1918_PATTERNS,
)


class SafeRunnerResult:
    def __init__(self, command: str, exit_code: int, stdout: str, stderr: str,
                 duration_ms: int, blocked: bool, blocked_reason: str,
                 stdout_hash: str, stderr_hash: str):
        self.command = command
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.duration_ms = duration_ms
        self.blocked = blocked
        self.blocked_reason = blocked_reason
        self.stdout_hash = stdout_hash
        self.stderr_hash = stderr_hash

    def to_dict(self) -> dict:
        return {
            "command": self.command[:500],
            "exit_code": self.exit_code,
            "stdout": self.stdout[:2000],
            "stderr": self.stderr[:1000],
            "duration_ms": self.duration_ms,
            "blocked": self.blocked,
            "blocked_reason": self.blocked_reason,
            "stdout_hash": self.stdout_hash,
            "stderr_hash": self.stderr_hash,
        }


def _hash16(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]


def validate_command(command: str) -> tuple[bool, str]:
    if not command or not command.strip():
        return False, "empty command"

    for pattern in FORBIDDEN_READONLY_PATTERNS:
        if pattern in command.lower():
            return False, f"forbidden pattern: {pattern}"

    try:
        tokens = shlex.split(command)
    except ValueError as e:
        return False, f"shlex parse error: {e}"

    if not tokens:
        return False, "empty after tokenization"

    cmd = tokens[0]

    for token in tokens:
        for prefix in DANGEROUS_TOKENS:
            if token.startswith(prefix):
                return False, f"dangerous token: {prefix}"
        if token in DANGEROUS_REDIRECTS:
            return False, f"redirect blocked: {token}"
        if token in DANGEROUS_OPERATORS:
            return False, f"operator blocked in readonly: {token}"

    if cmd in FORBIDDEN_READONLY_COMMANDS:
        return False, f"command forbidden: {cmd}"

    if cmd not in SAFE_READONLY_COMMANDS:
        return False, f"command not in safe readonly catalog: {cmd}"

    spec = SAFE_READONLY_COMMANDS[cmd]

    if spec.requires_args_validation:
        if cmd == "curl":
            for token in tokens[1:]:
                if token.startswith("-"):
                    if token in ("-o", "-O", "--output"):
                        return False, "curl -o/-O blocked in readonly"
            for token in tokens[1:]:
                if token.startswith("http://") or token.startswith("https://"):
                    _stripped = token.split("://", 1)[1]
                    if not any(_stripped.startswith(p) for p in RFC1918_PATTERNS):
                        return False, f"curl to non-RFC1918 target blocked: {token}"
        elif cmd == "find":
            has_path_arg = False
            for token in tokens[1:]:
                if token.startswith("/"):
                    if not any(token.startswith(p) for p in FIND_ALLOWED_PATHS):
                        return False, f"find path not in allowed set: {token}"
                    has_path_arg = True
            if not has_path_arg:
                return False, "find requires explicit path argument"
        elif cmd == "journalctl":
            for token in tokens[1:]:
                if token == "-f" or token == "--follow":
                    return False, "journalctl -f blocked in readonly"
            for i, token in enumerate(tokens[1:]):
                if token == "--lines" or token == "-n":
                    if i + 2 < len(tokens):
                        try:
                            val = int(tokens[i + 2])
                            if val > 500:
                                return False, "journalctl --lines max 500"
                        except (ValueError, IndexError):
                            pass
        elif cmd == "docker":
            has_allowed = False
            for token in tokens[1:]:
                if token in DOCKER_ALLOWED_SUBCOMMANDS:
                    has_allowed = True
                if token in DOCKER_BLOCKED_SUBCOMMANDS:
                    return False, f"docker subcommand blocked: {token}"
            if not has_allowed:
                return False, "docker requires allowed subcommand (ps/stats/inspect/logs)"
        elif cmd == "systemctl":
            for token in tokens[1:]:
                if token in ("restart", "stop", "start", "enable", "disable", "reload"):
                    return False, f"systemctl {token} blocked in readonly"
                if token == "is-active" or token == "is-enabled" or token == "status":
                    continue
            for token in tokens[1:]:
                if token.startswith("-"):
                    continue

    return True, ""


def run_safe(command: str, timeout: int = 30) -> SafeRunnerResult:
    valid, reason = validate_command(command)
    if not valid:
        return SafeRunnerResult(
            command=command, exit_code=-1, stdout="", stderr="",
            duration_ms=0, blocked=True, blocked_reason=reason,
            stdout_hash="", stderr_hash="",
        )

    t_start = time.time()
    try:
        proc = subprocess.run(
            shlex.split(command),
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
        exit_code = proc.returncode
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
    except subprocess.TimeoutExpired:
        duration_ms = int((time.time() - t_start) * 1000)
        return SafeRunnerResult(
            command=command, exit_code=-1, stdout="", stderr=f"timeout after {timeout}s",
            duration_ms=duration_ms, blocked=False, blocked_reason="timeout",
            stdout_hash="", stderr_hash=_hash16(f"timeout after {timeout}s"),
        )
    except FileNotFoundError:
        return SafeRunnerResult(
            command=command, exit_code=-1, stdout="", stderr="command not found",
            duration_ms=0, blocked=True, blocked_reason="command_not_found",
            stdout_hash="", stderr_hash="",
        )
    except Exception as e:
        return SafeRunnerResult(
            command=command, exit_code=-1, stdout="", stderr=str(e),
            duration_ms=int((time.time() - t_start) * 1000),
            blocked=True, blocked_reason=str(e),
            stdout_hash="", stderr_hash=_hash16(str(e)),
        )

    duration_ms = int((time.time() - t_start) * 1000)
    return SafeRunnerResult(
        command=command, exit_code=exit_code, stdout=stdout, stderr=stderr,
        duration_ms=duration_ms, blocked=False, blocked_reason="",
        stdout_hash=_hash16(stdout), stderr_hash=_hash16(stderr),
    )
