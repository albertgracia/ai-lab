---
title: "AI-LAB OpenAI Gateway"
summary: "Gateway OpenAI-compatible para inyectar contexto .agent, sanear reasoning_content y estabilizar OpenCode con LM Studio."
status: "stable"
category: "gateway"
tags:
  - gateway
  - opencode
  - lmstudio
  - openai-compatible
  - agent-context
  - sanitization
date: "2026-05-14"
---

# AI-LAB OpenAI Gateway

## Objetivo

El AI-LAB OpenAI Gateway actúa como capa intermedia entre OpenCode y LM Studio.

```text
OpenCode
→ AI-LAB Gateway :8008
→ Agent Context Injection
→ Output Sanitizer
→ LM Studio :1234
