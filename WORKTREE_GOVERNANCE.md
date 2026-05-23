# Worktree Governance

## Purpose

AI-LAB runtime checkpoints must be deterministic, reproducible and safe for autonomous agents. A phase is not stable because code appears to work locally; it is stable only when the worktree is classified, commits are semantic, generated state is excluded, and validation evidence exists.

## What May Stay Outside Git

These are operational or generated artifacts and may remain untracked or modified locally:

- `runtime/state/*`: live state, snapshots, caches, episodic/audit JSONL, discovery outputs.
- `.gitnexus/`: local GitNexus index database.
- Qdrant snapshots and vector-store payloads.
- build outputs: `dist/`, `.astro/`, `node_modules/`, `__pycache__/`, `*.pyc`.
- `/tmp/*` diagnostics and one-off reports.
- local agent/session files when explicitly marked local-only.

They must not be staged unless the user explicitly requests a state snapshot as an artifact and governance approves it.

## What Must Never Remain Ambiguous

The following cannot remain gray without classification:

- Runtime code imported by tracked code.
- Gateway hardening code.
- Authority, precision, fastpath, routing, governance, validation or telemetry code.
- Public documentation that describes runtime truth.
- Tooling exclusions that affect indexing or agent behavior.
- Any file required to reproduce a stable checkpoint.

If such a file appears in `git status --short`, classify it before continuing feature work.

## Validation Requirements

Runtime code changes require:

- `python3 -m compileall -q runtime`.
- Targeted pytest suite for affected contexts.
- Gateway HTTP smoke for affected APIs.
- `sudo systemctl restart ailab-gateway` smoke when TTY/permissions allow; otherwise document the limitation and run an ephemeral gateway smoke if possible.

Docs-only changes require:

- Content review.
- Build only if docs app content or routes are changed.

Tooling/indexing changes require:

- Syntax/content review.
- Confirm they do not exclude runtime source needed by GitNexus.

## Burn-in, Smoke and Tags

A checkpoint may be called `stable` only when:

- Tests PASS.
- Build PASS when applicable.
- Gateway smoke PASS when gateway behavior changed.
- No `runtime/state/*` is staged.
- Working tree gray files are either absent or explicitly classified and non-contaminating.
- Commit exists for the phase.
- Tag points at the phase commit.

Do not create stable tags on old commits while phase changes or unclassified gray files exist.

## Runtime State Policy

`runtime/state/*` is operational memory, not source code.

Rules:

- Never stage `runtime/state/*` in feature/hotfix commits.
- Never use state diffs as source-of-truth for code behavior.
- If state must be inspected, treat it as live evidence only.
- If state influences a fix, encode the fix in source/tests/docs, not in the state file.

## GitNexus Policy

- `.gitnexus/` is local generated index and must not be committed.
- `.gitnexusignore` is repo tooling and should be committed when stable.
- GitNexus is structural cognition; Prometheus/live runtime remains operational truth.
- Reindex after architectural changes using `npx gitnexus analyze --force --index-only --skip-agents-md --no-stats`.

## Generated Artifacts and Diagnostics

- `/tmp/*.md`, `/tmp/*.json`, burn-in logs and diagnostics are evidence artifacts, not commits by default.
- If a report needs to become durable documentation, move/summarize it into tracked docs in a separate docs commit.
- Do not commit generated caches or snapshots to make tests pass.

## Feature Phase Policy

Each feature phase must be isolated:

- One semantic commit for implementation.
- One docs commit if needed.
- One tag only after validation.
- No mixed commits across unrelated phases.
- No feature work while prior phase has unclassified runtime gray files.

## Hotfix Policy

Hotfix commits must be minimal and evidence-backed:

- Fix only the failing behavior.
- Add/update tests when feasible.
- Run targeted tests and smoke.
- Document residual risk if restart/burn-in cannot be performed.

## Agent Policy

Agents must:

- Read current `git status --short` before edits.
- Preserve user/runtime changes they did not make.
- Stage selectively by file.
- Never stage `runtime/state/*`.
- Never mix docs/tooling/runtime changes unless explicitly requested.
- Stop or ask when a gray file is an active runtime dependency and its destination is unclear.

## Rollback Safety

A rollback-safe change is:

- Small.
- Semantically isolated.
- Reversible by reverting one commit.
- Covered by tests/smoke.
- Not dependent on local state mutations.

## Architectural Stabilization

Architectural stabilization changes must prefer boundaries and dependency reduction over behavior changes. If behavior changes are unavoidable, they require explicit tests and report notes.

Stable architecture work should reduce one or more of:

- import cycles
- gateway fan-out
- producer/consumer inversion
- runtime/state coupling
- stale authority ambiguity
- untracked runtime dependencies
