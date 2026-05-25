# OPENCODE-GATEWAY-CONTRACT-HARDENING-39A

## Result

PASS.

## Scope

This phase validates and documents the OpenAI-compatible contract between OpenCode/Nexus and the AI-LAB Gateway.

## Runtime baseline

- Gateway: OK
- Router chain: OK
- LM Studio backend: `http://192.168.1.50:1234/v1`
- `/health`: OK
- `/v1/models`: OK
- `/v1/chat/completions`: OK

## ChatCompletion contract

Required fields:

- `id`
- `object`
- `created`
- `model`
- `choices`
- `choices[].index`
- `choices[].message.role`
- `choices[].message.content`
- `choices[].finish_reason`
- `usage.prompt_tokens`
- `usage.completion_tokens`
- `usage.total_tokens`

## Finish reasons

Supported/accepted:

- `stop`
- `length`
- `tool_calls`
- `content_filter`

## Tools and tool calls

Current classification:

```text
SUPPORTED
```

Behavior:

- tools/tool_choice are sanitized/gated.
- parallel unsafe tool execution is blocked where applicable.
- write tools require confirmation gate.
- malformed tool call arguments are repaired/filtered where supported.
- Gateway must not invent tool calls.

## Shutdown behavior

Gateway graceful shutdown is active from phase 38B.

During shutdown:

- new requests are rejected with HTTP 503.
- `/health` can report `shutting_down: true`.
- metric `ailab_gateway_shutdown_rejections_total` is exposed.

## Compatibility conclusion

The Gateway contract is compatible with OpenCode/Nexus for the validated base path.

No functional hardening was required in 39A.2.

## Rollback

This phase only adds tests and documentation. Rollback is limited to removing:

- `tests/test_gateway_openai_contract_39a.py`
- `docs/runtime/opencode-gateway-contract-39a.md`
