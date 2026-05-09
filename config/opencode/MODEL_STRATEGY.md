# MODEL STRATEGY

Default fast model:
- google/gemma-4-e4b

Reasoning model:
- qwen3-14b-claude-sonnet-4.5-reasoning-distill

Coding model:
- qwen2.5-coder-14b-instruct
- qwen2.5-coder-32b-instruct if enough VRAM

Embedding model:
- text-embedding-nomic-embed-text-v1.5

Vision:
- moondream2

Image:
- flux.2-klein-9b

Routing priorities:
1. Prefer online nodes.
2. Prefer models already loaded.
3. Prefer node with enough VRAM.
4. Prefer lower GPU usage.
5. Fallback to Main LM Studio.
