from dataclasses import dataclass
from typing import List


@dataclass
class RouteResult:
    intent: str
    mode: str
    capabilities: List[str]
    context_tags: List[str]
    suggested_model: str
    score: int = 1


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
        ],
        "mode": "build",
        "context_tags": [
            "codebase",
            "runtime",
            "rag",
        ],
        "model": "ai_lab_router/ailab-router",
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
                )

    return DEFAULT_ROUTE
