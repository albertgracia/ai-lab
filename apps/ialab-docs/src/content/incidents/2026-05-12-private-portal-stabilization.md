---
title: "Private AI-LAB portal stabilization and routing recovery"
date: "2026-05-12"
severity: "medium"
status: "resolved"
tags:
  - astro
  - traefik
  - cloudflare
  - routing
  - operations
---

# Summary

The private AI-LAB portal experienced routing inconsistencies after operational pages and dashboards were added.

The professional homepage was unintentionally replaced by the operational landing page while Traefik was still forwarding requests to an outdated Astro backend port.

# Issues Detected

## 1. Wrong Traefik backend port

Traefik dynamic configuration was pointing to:

```text
http://host.docker.internal:4321
