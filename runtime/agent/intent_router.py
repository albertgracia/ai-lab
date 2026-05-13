from dataclasses import dataclass
from typing import List

from runtime.modes.registry import get_capabilities


@dataclass
class RouteResult:

    intent: str
    mode: str
    capabilities: List[str]
    context_tags: List[str]
    suggested_model: str
    score: int = 0


INTENT_RULES = {

    "research": {
        "keywords": [
            "investiga",
            "research",
            "analiza",
            "documenta",
            "resume",
            "explica",
        ],
        "mode": "plan",
        "context_tags": [
            "memory",
            "docs",
            "rag",
        ],
        "model": "ai_lab_router/ailab-router",
    },

    "architecture": {
        "keywords": [
            "arquitectura",
            "architecture",
            "runtime",
            "routing",
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

    "coding": {
        "keywords": [
            "python",
            "script",
            "implementa",
            "desarrolla",
            "fix",
            "code",
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
            "logs",
            "gpu",
            "infra",
            "service",
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
            "governance",
            "policy",
            "audit",
            "sandbox",
        ],
        "mode": "plan",
        "context_tags": [
            "security",
            "policies",
            "audit",
        ],
        "model": "ai_lab_router/ailab-router",
    },
}


DEFAULT_ROUTE = RouteResult(
    intent="general",
    mode="plan",
    capabilities=get_capabilities("plan"),
    context_tags=[
        "memory",
    ],
    suggested_model="ai_lab_router/ailab-router",
    score=0,
)


def detect_intent(prompt: str) -> RouteResult:

    prompt_lower = prompt.lower()

    best_match = DEFAULT_ROUTE

    for intent_name, cfg in INTENT_RULES.items():

        score = 0

        for keyword in cfg["keywords"]:

            if keyword.lower() in prompt_lower:
                score += 1

        if score > best_match.score:

            best_match = RouteResult(
                intent=intent_name,
                mode=cfg["mode"],
                capabilities=get_capabilities(cfg["mode"]),
                context_tags=cfg["context_tags"],
                suggested_model=cfg["model"],
                score=score,
            )

    return best_match
