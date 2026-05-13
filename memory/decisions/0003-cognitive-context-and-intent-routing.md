# Decision 0003 - Cognitive Context and Intent Routing

Date: 2026-05-13

## Decision

AI-LAB now uses semantic intent routing and cognitive context loading as part of the operational runtime.

## Implemented

- Scored intent router
- Mode selection:
  - plan
  - build
  - execute
- Capability mapping
- Semantic context loading
- Local RAG retrieval inside agent context
- Integration with current roadmap and architecture memory

## Result

AI-LAB can now:

1. Detect user intent
2. Select an operational mode
3. Attach capabilities
4. Load semantic memory
5. Build contextual prompts for governed OpenCode/runtime usage

## Next steps

1. Create runtime agent orchestrator
2. Connect intent router + context loader + governance
3. Add audit runtime
4. Add sandbox/production profiles
5. Add episodic memory
