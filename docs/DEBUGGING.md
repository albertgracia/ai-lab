# Known Issues

## Docker Pull Timeout

Root Cause:
Cloudflare R2 connectivity issue.

Fix:
Docker registry mirror.

## Traefik Docker API mismatch

Root Cause:
Old Traefik Docker client API.

Fix:
Upgrade Traefik to v3.6+