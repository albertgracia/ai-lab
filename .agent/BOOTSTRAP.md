# OpenCode Bootstrap for AI-LAB

## Purpose

This file tells OpenCode how to use the local `.agent` knowledge layer as the operating source of truth.

## Source of Truth

Always prioritize these files in this order:

1. `OPENCODE.md`
2. `.agent/ARCHITECTURE.md`
3. `.agent/rules/GEMINI.md`
4. The relevant agent file under `.agent/agents/`
5. The relevant skill file under `.agent/skills/`
6. The relevant workflow file under `.agent/workflows/`
7. Runtime memory under `memory/semantic/`

## Loading Protocol

When a task arrives:

1. Classify the task domain.
2. Run the automatic selector in `.agent/scripts/agent_selector.py` when the task is not explicitly routed.
3. Load the matching specialist agent.
4. Load the minimum set of skills needed.
5. Read the global rules before acting.
6. If the request is vague, ask clarifying questions before coding.

## Agent Routing Guide

- Backend, API, database, auth, server logic -> `backend-specialist`
- UI, components, styling, frontend behavior -> `frontend-specialist`
- Data model, schema, migrations, query design -> `database-architect`
- CI/CD, Docker, deployment, infra -> `devops-engineer`
- Testing, coverage, E2E -> `test-engineer`
- Security review, auth audit, risks -> `security-auditor`
- Docs, manuals, technical writing -> `documentation-writer`
- Planning, task breakdown, roadmap -> `project-planner`
- Multi-domain tasks -> `orchestrator`

## Automatic Selector

Use `.agent/scripts/agent_selector.py` to suggest the best agent from the user request.

It mirrors the `intelligent-routing` skill and should be used as a quick local routing helper.

Examples:

```bash
python .agent/scripts/agent_selector.py "create a secure login endpoint"
python .agent/scripts/agent_selector.py "build a dashboard card"
python .agent/scripts/agent_selector.py "refactor the database schema"
```

## Behavioral Rules

- Write in Spanish.
- Do not invent files, ports, services, or configuration.
- Use the runtime state as evidence.
- Prefer safe diagnostics before changes.
- Keep changes minimal and reversible.
- Preserve encapsulation and separation of concerns.
- Ask before assuming stack, scope, or deployment model.

## Skills Loading

Only load the skills that directly help the current task.

Examples:

- API work -> `api-patterns`, `nodejs-best-practices`, `python-patterns`
- Database work -> `database-design`
- Docs -> `documentation-templates`
- Validation -> `lint-and-validate`
- Shell work -> `bash-linux` or `powershell-windows`
- Routing -> `intelligent-routing`

## Workflow Hint

If the task maps to a workflow, prefer the corresponding workflow file:

- Plan -> `.agent/workflows/plan.md`
- Debug -> `.agent/workflows/debug.md`
- Test -> `.agent/workflows/test.md`
- Deploy -> `.agent/workflows/deploy.md`

## Output Standard

- Be concise.
- Separate facts from hypotheses.
- State risks clearly.
- Include rollback when changes are proposed.
- Prefer actionable steps over long explanations.
