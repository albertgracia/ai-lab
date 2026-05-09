# OPENCODE POLICY FOR AI-LAB

## Language
Always answer in Spanish.

## Safety
Do not perform destructive changes automatically.
No rm -rf.
No docker compose down unless explicitly approved.
No systemctl restart unless explicitly approved.
No editing production configs without backup.
No secrets in logs.

## Reasoning
Use evidence from:
- system_state.py
- gpu_state.py
- docker inspect/logs
- git status
- current files

## Workflow
1. Understand request.
2. Inspect relevant files.
3. Build hypothesis.
4. Propose minimal change.
5. Validate.
6. Document result.

## Preferred output
- concise
- actionable
- command blocks
- explain risk
- include rollback when needed
