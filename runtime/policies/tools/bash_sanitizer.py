"""Bash command sanitizer for AI-LAB FASE 22B.

Uses shlex.split() token scanning to validate bash commands against
dangerous operators (pipes, redirects, chaining) based on tool policy mode.
Uses first-token exact match for command allowlists — NOT startswith.
"""

from __future__ import annotations

import shlex

_DANGEROUS_OPERATORS = frozenset({"|", "||", "&&", ";", "&"})
_DANGEROUS_REDIRECTS = frozenset({">", ">>", "<", "<<", "2>", "&>", "1>"})
_BLOCKED_TOKENS = frozenset({"$(", "`", "/dev/"})

_WRITE_COMMANDS = frozenset({"write", "edit", "rm", "mv", "cp", "dd", "tee"})


def sanitize_bash_command(command: str, policy: dict) -> tuple[str | None, list[str], bool]:
    """Validate a bash command against tool policy.

    Returns:
        (safe_command | None, [warnings], requires_confirmation)

    - readonly: first token exact match in bash_allowed_commands, no operators
    - agentic:  first token exact match, pipes allowed, redirects blocked
    - Strips dangerous tokens always ($( ), backticks, /dev/)
    """
    if not command or not isinstance(command, str):
        return None, ["empty or invalid command"], False

    try:
        tokens = shlex.split(command)
    except ValueError as exc:
        return None, [f"shlex parse error: {exc}"], False

    if not tokens:
        return None, ["empty after tokenization"], False

    cmd = tokens[0]
    mode = policy.get("mode", "disabled")

    # Always block dangerous token prefixes
    for token in tokens:
        if any(token.startswith(prefix) for prefix in _BLOCKED_TOKENS):
            return None, [f"dangerous token '{token}' blocked"], False

    # Command allowlist check (first token exact match)
    allowed = set(policy.get("bash_allowed_commands", []))
    if allowed and cmd not in allowed:
        return None, [f"command '{cmd}' not in allowlist"], False

    if mode == "readonly":
        for token in tokens[1:]:  # skip first token (command name)
            if token in _DANGEROUS_OPERATORS:
                return None, [f"operator '{token}' blocked in readonly mode"], False
            if token in _DANGEROUS_REDIRECTS:
                return None, [f"redirect '{token}' blocked in readonly mode"], False

    elif mode == "agentic":
        allow_pipes = policy.get("allow_pipes", False)
        for token in tokens[1:]:
            if token in _DANGEROUS_REDIRECTS:
                return None, [f"redirect '{token}' blocked"], False
            if token in _DANGEROUS_OPERATORS:
                if token in {"|"} and allow_pipes:
                    continue
                if token in {"||"} and allow_pipes:
                    continue
                return None, [f"operator '{token}' blocked"], False

        if cmd in _WRITE_COMMANDS:
            return command, [], True  # requires_confirmation

    return command, [], False
