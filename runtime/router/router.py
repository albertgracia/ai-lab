from pathlib import Path

AGENT_RULES = {
    "debugger": [
        "debug", "error", "broken", "fail", "issue", "traceback",
        "crash", "not working", "logs", "502", "routing"
    ],
    "devops-engineer": [
        "deploy", "docker", "compose", "traefik", "nginx",
        "server", "ci", "cd", "infra", "container"
    ],
    "security-auditor": [
        "security", "vulnerability", "audit", "cve", "secret",
        "token", "exposed", "permission", "hardening"
    ],
    "backend-specialist": [
        "api", "backend", "endpoint", "database", "postgres",
        "redis", "auth", "service"
    ],
    "project-planner": [
        "plan", "roadmap", "architecture", "design", "strategy",
        "steps", "organize"
    ],
    "orchestrator": [
        "orchestrate", "multi-agent", "workflow", "coordinate",
        "agents", "pipeline"
    ],
}


def classify_agent(user_request: str) -> str:
    text = user_request.lower()
    scores = {}

    for agent, keywords in AGENT_RULES.items():
        scores[agent] = sum(1 for keyword in keywords if keyword in text)

    best_agent = max(scores, key=scores.get)

    if scores[best_agent] == 0:
        return "orchestrator"

    return best_agent


def load_agent_prompt(agent_name: str) -> str:
    path = Path("/opt/ai-lab/.agent/agents") / f"{agent_name}.md"

    if not path.exists():
        return ""

    return path.read_text(errors="ignore")[:4000]


def route(user_request: str):
    agent = classify_agent(user_request)
    agent_prompt = load_agent_prompt(agent)

    return {
        "agent": agent,
        "agent_prompt": agent_prompt,
    }
