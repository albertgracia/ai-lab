# Decision 0002 - Local RAG Memory Stable

Date: 2026-05-13

## Decision

AI-LAB will use local CPU-based embeddings with sentence-transformers for semantic memory and RAG.

## Reason

LM Studio `/v1/embeddings` returned HTTP 500 on the RX9070 node, while local `sentence-transformers` embeddings worked reliably.

## Current implementation

- Embedding model: `nomic-ai/nomic-embed-text-v1.5`
- Vector size: 768
- Indexed files: 303
- Skipped files: 20213
- Semantic records: 1207
- Output file: `/opt/ai-lab/runtime/state/embedding_records.json`

## Result

Semantic memory search is operational.

Validated retrieval examples:
- `memory/tasks/current-roadmap.md`
- `memory/decisions/0001-local-first-architecture.md`
- `memory/semantic/ai-lab-architecture.md`

## Next steps

1. Add Qdrant persistence
2. Add dynamic context injection
3. Add OpenCode governance modes:
   - plan
   - readonly
   - build
   - execute
4. Add plugin governance:
   - sandbox
   - pilot
   - validation
   - production
