from dataclasses import dataclass, field
from typing import List


@dataclass
class RouteResult:
    intent: str
    mode: str
    capabilities: List[str]
    context_tags: List[str]
    suggested_model: str
    score: int = 1
    agent: str = "orchestrator"
    reasoning: str = "Routing based on intent classification"
    complexity: str = "medium"
    workflow: str = ""
    domains: List[str] = field(default_factory=list)
    multi_agent: bool = False
    skills: List[str] = field(default_factory=list)


INTENT_RULES = {

    "coding": {
        "keywords": [
            "python",
            "script",
            "implementa",
            "implementar",
            "crear",
            "crea",
            "desarrolla",
            "workflow",
            "fix",
            "code",
            "código",
            "debug",
            "refactor",
            "optimiza",
        ],
        "mode": "build",
        "context_tags": [
            "codebase",
            "runtime",
            "rag",
        ],
        "model": "ai_lab_router/ailab-router",
        "agent": "backend-specialist",
        "skills": ["python-patterns", "clean-code"],
    },

    "operations": {
        "keywords": [
            "docker",
            "restart",
            "deploy",
            "infra",
            "systemctl",
            "logs",
            "service",
            "gpu",
        ],
        "mode": "execute",
        "context_tags": [
            "runtime",
            "infra",
            "observability",
        ],
        "model": "ai_lab_router/ailab-router",
        "agent": "devops-engineer",
        "skills": ["bash-linux", "deployment"],
    },

    "security": {
        "keywords": [
            "security",
            "secure",
            "policy",
            "permissions",
            "sandbox",
            "audit",
            "governance",
            "audita",
        ],
        "mode": "plan",
        "context_tags": [
            "security",
            "policies",
            "audit",
        ],
        "model": "ai_lab_router/ailab-router",
        "agent": "security-auditor",
        "skills": ["red-team", "vulnerability-scanner"],
    },

    "architecture": {
        "keywords": [
            "arquitectura",
            "architecture",
            "design",
            "routing",
            "runtime",
            "agent",
        ],
        "mode": "plan",
        "context_tags": [
            "architecture",
            "runtime",
            "memory",
        ],
        "model": "ai_lab_router/ailab-router",
        "agent": "orchestrator",
        "skills": ["architecture", "plan-writing"],
    },

    "research": {
        "keywords": [
            "investiga",
            "research",
            "analiza",
            "analyze",
            "documenta",
            "explica",
            "resume",
        ],
        "mode": "plan",
        "context_tags": [
            "memory",
            "docs",
            "rag",
        ],
        "model": "ai_lab_router/ailab-router",
        "agent": "documentation-writer",
        "skills": ["documentation", "plan-writing"],
    },
}


DEFAULT_ROUTE = RouteResult(
    intent="general",
    mode="plan",
    capabilities=[
        "analyze",
        "plan",
        "rag",
        "read",
        "search",
    ],
    context_tags=[
        "memory",
    ],
    suggested_model="ai_lab_router/ailab-router",
    agent="orchestrator",
    reasoning="No specific intent detected, using general route",
    complexity="medium",
    workflow="",
    domains=["general"],
    multi_agent=False,
    skills=["plan-writing"],
)


from runtime.modes.registry import get_capabilities


def detect_intent(prompt: str) -> RouteResult:

    prompt_lower = prompt.lower()

    for intent_name, cfg in INTENT_RULES.items():

        for keyword in cfg["keywords"]:

            if keyword.lower() in prompt_lower:

                return RouteResult(
                    intent=intent_name,
                    mode=cfg["mode"],
                    capabilities=get_capabilities(cfg["mode"]),
                    context_tags=cfg["context_tags"],
                    suggested_model=cfg["model"],
                    score=1,
                    agent=cfg.get("agent", "orchestrator"),
                    reasoning=f"Matched intent '{intent_name}' via keyword '{keyword}'",
                    complexity="medium",
                    workflow="",
                    domains=[intent_name],
                    multi_agent=False,
                    skills=cfg.get("skills", []),
                )

    return DEFAULT_ROUTE


def route_request(prompt: str) -> RouteResult:
    return detect_intent(prompt)
