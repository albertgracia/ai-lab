# Runtime Core Agent

## 1. Domain Purpose

Orchestrate bounded contexts; keep core minimal.

## 2. Ownership

- gateway as orchestrator
- composition of domain outputs

## 3. Allowed Imports

- domain contracts
- domain registries

## 4. Forbidden Coupling

- global reasoning across all domains in one file

## 5. Context Budget Policy

Keep routing deterministic.

## 6. Evidence Policy

Propagate evidence; do not invent.

## 7. Operational Tone

Operational.

## 8. Authority Limits

No authority override.

## 9. Escalation Rules

Escalate to domain owners.

## 10. Must Never Do

- create new public HTTP routes in bootstrap
