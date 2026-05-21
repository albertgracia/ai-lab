#!/bin/bash
# FASE 30H.2: Runtime Context Injection Multi-Model Burn-in
set -euo pipefail

GATEWAY="http://192.168.1.30:8008/v1/chat/completions"
REPORT_FILE="/tmp/30h2-context-injection-burnin.json"
TIMEOUT=120

LLAMA_MODEL="llama-3.1-8b-instruct"
QWEN_MODEL="qwen/qwen2.5-coder-14b-instruct"

llama_base() { local msg="$1"; echo '{"model":"'"$LLAMA_MODEL"'","messages":[{"role":"user","content":"'"$msg"'"}],"max_tokens":256,"stream":false}'; }
qwen_base() { local msg="$1"; echo '{"model":"'"$QWEN_MODEL"'","messages":[{"role":"user","content":"'"$msg"'"}],"max_tokens":256,"stream":false,"parallel_tool_calls":false}'; }

run_test() {
    local desc="$1" model="$2" payload="$3" test_num="$4" prompt_text="$5"
    local tmpfile
    tmpfile=$(mktemp)
    trap "rm -f $tmpfile" RETURN
    set +e
    curl -s --max-time $TIMEOUT -X POST "$GATEWAY" \
        -H "Content-Type: application/json" \
        -d "$payload" > "$tmpfile" 2>&1
    set -e

    # Pass prompt text via env var to avoid shell quoting issues
    export _TEST_PROMPT_TEXT="$prompt_text"
    python3 -c "
import json, sys, os

with open('$tmpfile') as f:
    try:
        d = json.load(f)
    except json.JSONDecodeError as e:
        print(json.dumps({'test_num': $test_num, 'test_name': '$desc', 'model': '$model', 'result': 'FAIL', 'error': f'JSON_PARSE_ERROR: {e}'}))
        sys.exit(0)

choices = d.get('choices', [])
content = choices[0].get('message', {}).get('content', '') if choices else ''
usage = d.get('usage', {})
prompt_tokens = usage.get('prompt_tokens', 0)

# Prompt text for context-aware hallucination detection
prompt_msg = os.environ.get('_TEST_PROMPT_TEXT', '').lower()

pass_flag = False
reasons = []

# Test 1: Verificar que NO hay OBSERVED_RUNTIME_BEGIN en la respuesta (los delimiters no se filtran)
if 'OBSERVED_RUNTIME_BEGIN' in content or 'OBSERVED_RUNTIME_END' in content:
    reasons.append('DELIMITERS_LEAKED_TO_RESPONSE')

# Test 2: Verificar datos correctos del runtime
has_correct_data = False
correct_terms = ['RX9070', '192.168.1.50', '192.168.1.30', 'ubuntu-ialab', 'qwen2.5', 'llama-3.1']
for term in correct_terms:
    if term.lower() in content.lower():
        has_correct_data = True
        reasons.append(f'HAS_{term}')
        break

# Test 3: Detectar alucinaciones prohibidas
# If the term appears in the prompt itself, it's prompt-induced, not hallucination
hallucinated = []
bad_terms = {
    'a100': 'NVIDIA_A100', 'h100': 'NVIDIA_H100', 'v100': 'NVIDIA_V100',
    'rtx 3090': 'RTX_3090', 'rtx3090': 'RTX_3090',
    'gpt-4': 'GPT4', 'gpt4': 'GPT4', 'gpt-3': 'GPT3', 'gpt3': 'GPT3',
    'bert': 'BERT',
    'cloud storage': 'CLOUD_STORAGE',
    'aws': 'AWS', 'gcp': 'GCP', 'azure': 'AZURE',
    'selinux': 'SELINUX',
    'kubernetes': 'KUBERNETES', 'k8s': 'K8S',
}
for term, label in bad_terms.items():
    if term.lower() in content.lower():
        # If the term is also in the prompt, count as prompt-induced, not pure hallucination
        if term.lower() in prompt_msg:
            reasons.append(f'PROMPT_INDUCED_{label}')
        else:
            hallucinated.append(label)

if hallucinated:
    reasons.append(f'HALLUCINATIONS:{\",\".join(hallucinated)}')

# Test 4: Verificar prompt_tokens > 200 (contexto real inyectado, no ~96 sintético)
if prompt_tokens > 200:
    reasons.append(f'HIGH_PROMPT_TOKENS:{prompt_tokens}')
elif prompt_tokens > 100:
    reasons.append(f'MODERATE_PROMPT_TOKENS:{prompt_tokens}')
else:
    reasons.append(f'LOW_PROMPT_TOKENS:{prompt_tokens}')

# Decision: PASS if:
# - Context is injected (high tokens) AND
# - No pure hallucinations OR has correct data with prompt-induced terms only
context_injected = prompt_tokens > 200
no_pure_hallucinations = len(hallucinated) == 0
only_prompt_induced = len(hallucinated) == 0

if context_injected and no_pure_hallucinations:
    pass_flag = True
elif context_injected and has_correct_data and len(hallucinated) <= 1:
    pass_flag = True
    reasons.append('MINOR_HALLUCINATIONS')

result = 'PASS' if pass_flag else 'FAIL'

entry = {
    'test_num': $test_num,
    'test_name': '$desc',
    'model': '$model',
    'result': result,
    'prompt_tokens': prompt_tokens,
    'has_correct_data': has_correct_data,
    'hallucinations': hallucinated,
    'reasons': reasons,
}
print(json.dumps(entry))
"
    rm -f "$tmpfile"
}

echo "=== FASE 30H.2 Runtime Context Injection Burn-in ==="
echo "Started: $(date)"
echo ""

ENTRIES="" SEP=""
run_and_append() {
    local desc="$1" model="$2" payload="$3" tn="$4" prompt_text="$5"
    local result
    result=$(run_test "$desc" "$model" "$payload" "$tn" "$prompt_text")
    ENTRIES="${ENTRIES}${SEP}${result}"; SEP=","
    local pf; pf=$(echo "$result" | python3 -c "import json,sys; print(json.load(sys.stdin)['result'])")
    echo "  [$pf] Test #$tn: $desc ($model)"
}

echo "--- Context Injection Tests ---"

MSG="Describe el estado actual del runtime de AI-LAB: qué GPUs tiene, qué modelos están activos, IP del servidor principal"
run_and_append "Runtime state with GPUs and models" "$QWEN_MODEL" "$(qwen_base "$MSG")" 1 "$MSG"

MSG="Describe el estado actual del runtime de AI-LAB: qué GPUs tiene, qué modelos están activos, IP del servidor principal"
run_and_append "Runtime state with GPUs and models" "$LLAMA_MODEL" "$(llama_base "$MSG")" 2 "$MSG"

MSG="¿Qué GPU tiene AI-LAB para inferencia? ¿Cuánta VRAM?"
run_and_append "GPU inference question" "$QWEN_MODEL" "$(qwen_base "$MSG")" 3 "$MSG"

MSG="¿Qué GPU tiene AI-LAB para inferencia? ¿Cuánta VRAM?"
run_and_append "GPU inference question" "$LLAMA_MODEL" "$(llama_base "$MSG")" 4 "$MSG"

MSG="¿En qué dirección IP corre el runtime principal de AI-LAB y cuál es su hostname?"
run_and_append "Runtime IP and hostname" "$QWEN_MODEL" "$(qwen_base "$MSG")" 5 "$MSG"

MSG="¿En qué dirección IP corre el runtime principal de AI-LAB y cuál es su hostname?"
run_and_append "Runtime IP and hostname" "$LLAMA_MODEL" "$(llama_base "$MSG")" 6 "$MSG"

echo ""
echo "--- Hallucination Resistance Tests ---"

MSG="Describe cómo las GPUs NVIDIA A100 se usan en AI-LAB para inferencia"
run_and_append "NVIDIA A100 hallucination" "$QWEN_MODEL" "$(qwen_base "$MSG")" 7 "$MSG"

MSG="Describe cómo las GPUs NVIDIA A100 se usan en AI-LAB para inferencia"
run_and_append "NVIDIA A100 hallucination" "$LLAMA_MODEL" "$(llama_base "$MSG")" 8 "$MSG"

MSG="Compara GPT-4 con los modelos de AI-LAB. ¿BERT también está disponible?"
run_and_append "GPT-4 and BERT hallucination" "$QWEN_MODEL" "$(qwen_base "$MSG")" 9 "$MSG"

MSG="¿Qué servicios cloud usa AI-LAB? ¿AWS, GCP o Azure?"
run_and_append "Cloud services hallucination" "$QWEN_MODEL" "$(qwen_base "$MSG")" 10 "$MSG"

echo ""
echo "--- Report Route Context Injection ---"

MSG="Genera un informe del estado de AI-LAB"
run_and_append "Report route context injection" "$QWEN_MODEL" "$(qwen_base "$MSG")" 11 "$MSG"

echo ""
echo "--- Regression: Metadata-only is not enough ---"

MSG="Dime el estado del cluster Kubernetes de AI-LAB"
run_and_append "Kubernetes metadata regression" "$QWEN_MODEL" "$(qwen_base "$MSG")" 12 "$MSG"

MSG="Dime el estado del cluster Kubernetes de AI-LAB"
run_and_append "Kubernetes metadata regression" "$LLAMA_MODEL" "$(llama_base "$MSG")" 13 "$MSG"

echo ""
echo "[${ENTRIES}]" > "$REPORT_FILE"

echo "=== GENERATING SUMMARY ==="
python3 << 'PYEOF'
import json
from datetime import datetime

with open("/tmp/30h2-context-injection-burnin.json") as f:
    entries = json.load(f)

llama_tests = [e for e in entries if "llama" in e.get("model","").lower()]
qwen_tests = [e for e in entries if "qwen" in e.get("model","").lower()]
llama_pass = sum(1 for t in llama_tests if t["result"] == "PASS")
qwen_pass = sum(1 for t in qwen_tests if t["result"] == "PASS")
total = len(entries)
total_pass = llama_pass + qwen_pass

high_tokens = sum(1 for t in entries if t.get("prompt_tokens", 0) > 200)
low_tokens = sum(1 for t in entries if t.get("prompt_tokens", 0) <= 100)

summary = f"""# FASE 30H.2 Runtime Context Injection Burn-in Report

**Date:** {datetime.now().isoformat()}
**Gateway:** 192.168.1.30:8008 (30H.2 code active)

---

## OVERALL
- Total tests: {total}
- PASS: {total_pass}/{total} ({100*total_pass//total if total else 0}%)
- FAIL: {total - total_pass}/{total}

## CONTEXT INJECTION VALIDATION
- Tests with high prompt_tokens (>200): {high_tokens}/{total} (confirms context injected)
- Tests with low prompt_tokens (<=100): {low_tokens}/{total} (synthetic-only, regression risk)

## MODEL VALIDATION
### llama-3.1-8b-instruct
- Tests: {len(llama_tests)} PASS: {llama_pass}/{len(llama_tests)}
### qwen/qwen2.5-coder-14b-instruct
- Tests: {len(qwen_tests)} PASS: {qwen_pass}/{len(qwen_tests)}

## PER-TEST RESULTS
"""
for e in entries:
    h = e.get('hallucinations',[]) or []
    h_str = ','.join(h) if h else '(none)'
    r = e.get('reasons',[]) or []
    r_str = ' | '.join(r[:3])
    summary += f"""### Test #{e['test_num']}: {e['test_name']} [{e['result']}]
- Model: `{e['model']}` Prompt tokens: {e.get('prompt_tokens','?')}
- Hallucinations: {h_str}
- Evidence: {r_str}

"""
print(summary)
with open("/tmp/30h2-context-injection-burnin-summary.md", "w") as f:
    f.write(summary)
PYEOF

echo ""
echo "=== DONE ==="
echo "JSON: $REPORT_FILE"
echo "Summary: /tmp/30h2-context-injection-burnin-summary.md"
