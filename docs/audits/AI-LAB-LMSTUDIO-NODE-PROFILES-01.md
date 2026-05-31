# AI-LAB-LMSTUDIO-NODE-PROFILES-01

## Resultado: PASS

## Git state
- HEAD/base: `27c6de79`
- Branch: `main`
- Status start: clean, synced with `origin/main`
- No push, no tag, no rebase

## Source-backed scope
- `runtime/profiles/manifest_profiles.json` defines route-family to profile-bundle mapping.
- `runtime/profiles/*.json` define the policy bundles for observe, chat, coding and analysis.
- `runtime/nodes/nodes.json` defines the hardware pools and their capabilities.
- `runtime/nodes/node_registry.py` loads enabled nodes and capability filters.

## Node registry
- `nas-local` -> `RX780M`, `192.168.1.250:1234`, capabilities `fast`, `lightweight`, `fallback`, `router`, `memory`.
- `rx7900xt-node` -> `RX7900XT`, `192.168.1.60:1234`, capabilities `reasoning`, `coding`, `large-context`, `multi-agent`, `orchestration`, `backend`.
- `rx9070-node` -> `RX9070`, `192.168.1.50:1234`, capabilities `vision`, `image`, `multimodal`, `embeddings`, `creative`, `frontend`.

## Profile bundles
- `observe_profile.json` -> minimal memory, fast fallback, brief output.
- `chat_profile.json` -> general conversation, light memory, tools off.
- `coding_profile.json` -> higher token budget, coding default model.
- `analysis_profile.json` -> deep reasoning, full memory, reasoning enabled.

## Manifest routing
- `minimal`, `casual`, `greeting`, `observe`, `opencode_minimal` -> `observe_profile.json`.
- `fast`, `general`, `cognitive`, `chat`, `tool_use`, `tool_fastpath`, `opencode_chat`, `report` -> `chat_profile.json`.
- `coding`, `opencode_coding` -> `coding_profile.json`.
- `reasoning`, `opencode_reasoning` -> `analysis_profile.json`.

## Interpretation
- The node layer is hardware and capability driven.
- The profile layer is policy driven.
- The two layers should stay separate in docs and dashboards.

## Astro update
- `apps/ialab-docs/src/pages/ai-infrastructure/index.astro` now includes a dedicated LM Studio Node Profiles section.
- The page keeps the roadmap concise and adds the node/profile separation explicitly.

## Constraints respected
- No runtime modified
- No services restarted
- No configuration changed
- No push
- No tag
