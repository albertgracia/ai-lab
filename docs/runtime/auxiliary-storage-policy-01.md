# Auxiliary Storage Policy

## Purpose
Define the usage policy for `/mnt/ai-models/ai-lab` as auxiliary storage for non-versioned operational artifacts.

## Scope

### `/opt/ai-lab` (primary — git-versioned)
- Source code, configuration, documentation
- Versioned runtime state
- Docker compose stacks and deployment definitions

### `/mnt/ai-models/ai-lab` (auxiliary — not git-versioned)
- Operational logs (gateway, router, MCP, docs)
- Systemd unit backups and config backups
- Audit reports and forensic evidence
- Auxiliary snapshots (pre/post deployment)
- Staging area for content updates
- Cache for build artifacts

## Exclusions
- Unencrypted secrets must never be placed here
- Qdrant vector data requires a dedicated migration phase
- AI model weights require a dedicated migration phase
- Git-versioned runtime state must stay in `/opt/ai-lab`

## Directory Layout

```
/mnt/ai-models/ai-lab/
├── logs/
│   ├── gateway/
│   ├── router/
│   ├── mcp/
│   ├── docs/
│   └── audits/
├── backups/
│   ├── systemd-units/
│   ├── configs/
│   └── reports/
├── snapshots/
├── staging/
└── cache/
```

## Ownership
- `albert:albert` for operational directories (logs, snapshots, staging, cache)
- `root:root` for backup directories (backups, configs, reports)

## Retention
- Logs: 90 days rolling
- Backups: retain until confirmed stable + 30 days
- Audit reports: permanent
- Snapshots: 30 days rolling
- Cache: ephemeral, cleared on build

## Changes
This policy may only be updated through a documented phase with human approval.
