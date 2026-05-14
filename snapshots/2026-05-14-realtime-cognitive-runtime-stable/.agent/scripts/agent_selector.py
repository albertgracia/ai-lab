#!/usr/bin/env python3
"""Suggest the most appropriate AI-LAB specialist agent for a task.

This is a lightweight local routing helper that mirrors the
`intelligent-routing` skill.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentMatch:
    agent: str
    skills: tuple[str, ...]
    reason: str


ROUTES: list[tuple[re.Pattern[str], AgentMatch]] = [
    (
        re.compile(r"\b(login|auth|signup|password|jwt|token|oauth|session)\b", re.I),
        AgentMatch("security-auditor", ("api-patterns", "vulnerability-scanner"), "authentication or security-related request"),
    ),
    (
        re.compile(r"\b(api|endpoint|route|post|get|server|backend)\b", re.I),
        AgentMatch("backend-specialist", ("api-patterns", "nodejs-best-practices", "python-patterns"), "backend or API request"),
    ),
    (
        re.compile(r"\b(component|layout|card|button|ui|css|html|tailwind|frontend|page|dashboard)\b", re.I),
        AgentMatch("frontend-specialist", ("frontend-design", "web-design-guidelines"), "frontend or UI request"),
    ),
    (
        re.compile(r"\b(schema|migration|table|database|sql|prisma|query|index)\b", re.I),
        AgentMatch("database-architect", ("database-design",), "database or schema request"),
    ),
    (
        re.compile(r"\b(test|coverage|vitest|jest|playwright|e2e)\b", re.I),
        AgentMatch("test-engineer", ("testing-patterns", "webapp-testing"), "testing or QA request"),
    ),
    (
        re.compile(r"\b(docker|deploy|deployment|ci/cd|infra|traefik|portainer)\b", re.I),
        AgentMatch("devops-engineer", ("docker-expert", "deployment-procedures"), "deployment or infrastructure request"),
    ),
    (
        re.compile(r"\b(error|bug|broken|not working|crash|debug)\b", re.I),
        AgentMatch("debugger", ("systematic-debugging",), "debugging or incident request"),
    ),
    (
        re.compile(r"\b(security|vulnerability|exploit|red team|owasp)\b", re.I),
        AgentMatch("security-auditor", ("vulnerability-scanner", "red-team-tactics"), "security review request"),
    ),
    (
        re.compile(r"\b(doc|documentation|manual|readme|blog|write-up)\b", re.I),
        AgentMatch("documentation-writer", ("documentation-templates",), "documentation request"),
    ),
]


def select_agent(text: str) -> AgentMatch:
    normalized = text.strip()
    if not normalized:
        return AgentMatch("project-planner", ("plan-writing",), "empty request")

    if re.search(r"\b(build|create|implement|refactor|multi-agent|orchestrate)\b", normalized, re.I):
        if sum(bool(pattern.search(normalized)) for pattern, _ in ROUTES) >= 2:
            return AgentMatch("orchestrator", ("parallel-agents", "behavioral-modes"), "multi-domain request")

    for pattern, match in ROUTES:
        if pattern.search(normalized):
            return match

    return AgentMatch("project-planner", ("plan-writing", "brainstorming"), "default planning fallback")


def main() -> int:
    parser = argparse.ArgumentParser(description="Suggest the best AI-LAB agent for a request.")
    parser.add_argument("request", nargs="*", help="User request to classify")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args()

    text = " ".join(args.request).strip()
    match = select_agent(text)

    if args.json:
        print(json.dumps({"agent": match.agent, "skills": list(match.skills), "reason": match.reason}, ensure_ascii=False))
    else:
        print(f"agent={match.agent}")
        print(f"skills={', '.join(match.skills)}")
        print(f"reason={match.reason}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
