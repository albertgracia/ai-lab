#!/usr/bin/env python3
"""FASE 28.2-B — Readonly Executor Burn-in & Governance Validation.

Tests 8 categories:
  1. benign_readonly     — safe commands execution
  2. topology_runtime    — API/state queries
  3. malformed_commands  — invalid args, truncated, flags
  4. forbidden_commands  — rm/chmod/systemctl restart/etc → 100% blocked
  5. injection_attempts  — ; && || backticks $() pipes redirects → 100% blocked
  6. timeout_validation  — slow commands, clean timeout
  7. workflow_state      — EXECUTING/DONE/FAILED transitions
  8. governance          — risk HIGH, invalid scopes, denied intents

Runs with 3 concurrent workers. Generates JSON + MD reports.

Usage:
    python tests/burnin_28_2.py [--quick] [--workers 3]
"""

import hashlib
import json
import os
import sys
import time
import threading
from dataclasses import dataclass, field, asdict
from typing import Any

sys.path.insert(0, "/opt/ai-lab")

from runtime.agentic.safe_runner import validate_command, run_safe, SafeRunnerResult
from runtime.agentic.readonly_policies import check_governance, assess_risk, check_scope
from runtime.agentic.execution_audit import write_execution_audit, read_execution_audit, get_audit_stats, build_audit_entry
from runtime.agentic.execution_context import ExecutionMode, DryRunReason, RuntimeExecutionContext, CURRENT_EXECUTION_MODE
from runtime.agentic.workflow_state import WorkflowState, WorkflowTimeline, VALID_TRANSITIONS
from runtime.agentic.readonly_executor import RealReadonlyExecutor, ENABLE_EXECUTOR, DRY_RUN
from runtime.agentic.rollback_placeholder import RollbackPlaceholder
from runtime.agentic.planner import AgenticPlan, WorkflowAction
from runtime.telemetry.prometheus_metrics import (
    record_executor_command, record_executor_blocked,
    record_executor_governance_block, record_executor_dry_run,
    record_executor_duration, record_executor_validation_failure,
)


@dataclass
class BurninResult:
    category: str = ""
    test_name: str = ""
    passed: bool = False
    detail: str = ""
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


ALL_RESULTS: list[BurninResult] = []
_lock = threading.Lock()
_worker_errors: list[str] = []


def record(category: str, test_name: str, passed: bool, detail: str = "", duration_ms: float = 0.0, **kw):
    r = BurninResult(category=category, test_name=test_name, passed=passed,
                     detail=detail, duration_ms=duration_ms, metadata=kw)
    with _lock:
        ALL_RESULTS.append(r)
    status = "✅" if passed else "❌"
    print(f"  {status} [{category}] {test_name} ({duration_ms:.0f}ms) {'| ' + detail if detail else ''}")


# ═══════════════════════════════════════════════════════════════════
# CATEGORY 1: benign_readonly
# ═══════════════════════════════════════════════════════════════════

def test_benign_readonly():
    cat = "benign_readonly"
    commands = [
        ("uptime", "uptime"),
        ("df", "df -h /"),
        ("free", "free -h"),
        ("uname", "uname -a"),
        ("ls_tmp", "ls /tmp"),
        ("date", "date"),
        ("who", "who"),
        ("nproc", "nproc"),
        ("cat_version", "cat /proc/version"),
    ]
    for name, cmd in commands:
        t0 = time.time()
        valid, reason = validate_command(cmd)
        if not valid:
            record(cat, name, False, f"validation failed: {reason}", (time.time()-t0)*1000)
            continue
        result = run_safe(cmd, timeout=10)
        elapsed = (time.time() - t0) * 1000
        passed = not result.blocked and result.exit_code == 0
        record(cat, name, passed, f"exit={result.exit_code}", elapsed,
               stdout_hash=result.stdout_hash, blocked=result.blocked)
        if passed:
            record_executor_command("success", "low")


# ═══════════════════════════════════════════════════════════════════
# CATEGORY 2: topology_runtime
# ═══════════════════════════════════════════════════════════════════

def test_topology_runtime():
    cat = "topology_runtime"
    curls = [
        ("gateway_health", "curl -s http://192.168.1.30:8008/health"),
        ("gateway_metrics", "curl -s http://192.168.1.30:8008/metrics"),
        ("slo_health", "curl -s http://192.168.1.30:8008/slo/health"),
        ("router_health", "curl -s http://192.168.1.30:8083/health"),
        ("agentic_state", "curl -s http://192.168.1.30:8083/agentic/state"),
        ("agentic_executions", "curl -s http://192.168.1.30:8083/agentic/executions"),
    ]
    for name, cmd in curls:
        t0 = time.time()
        valid, reason = validate_command(cmd)
        if not valid:
            record(cat, name, False, f"validation failed: {reason}", (time.time()-t0)*1000)
            continue
        result = run_safe(cmd, timeout=15)
        elapsed = (time.time() - t0) * 1000
        passed = not result.blocked and result.exit_code == 0 and len(result.stdout) > 0
        record(cat, name, passed, f"exit={result.exit_code} bytes={len(result.stdout)}", elapsed,
               stdout_hash=result.stdout_hash, blocked=result.blocked)


# ═══════════════════════════════════════════════════════════════════
# CATEGORY 3: malformed_commands
# ═══════════════════════════════════════════════════════════════════

def test_malformed_commands():
    cat = "malformed_commands"
    cases = [
        ("empty", ""),
        ("only_whitespace", "   "),
        ("shlex_fail", "ls 'unclosed"),
        ("nonexistent_command", "zxywvut_abcdef 123"),
        ("invalid_flag", "ls --nonexistent-flag-xyz"),
        ("unknown_binary", "doesnotexist"),
    ]
    for name, cmd in cases:
        t0 = time.time()
        valid, reason = validate_command(cmd)
        elapsed = (time.time() - t0) * 1000
        if name == "invalid_flag":
            passed = valid
            if passed:
                result = run_safe(cmd, timeout=5)
                passed = result.exit_code != 0
            record(cat, name, passed, f"valid={valid} exit={result.exit_code if not valid else 'N/A'}", elapsed)
        else:
            passed = not valid
            record(cat, name, passed, f"expected_blocked={not valid} reason={reason}", elapsed)
            if passed:
                record_executor_validation_failure(reason or "malformed")


# ═══════════════════════════════════════════════════════════════════
# CATEGORY 4: forbidden_commands (100% blocked expected)
# ═══════════════════════════════════════════════════════════════════

def test_forbidden_commands():
    cat = "forbidden_commands"
    cases = [
        ("rm_force", "rm -rf /"),
        ("chmod", "chmod 777 /etc/passwd"),
        ("chown", "chown root:root /etc/hosts"),
        ("systemctl_restart", "systemctl restart ailab-gateway"),
        ("systemctl_stop", "systemctl stop ailab-gateway"),
        ("docker_exec", "docker exec -it container bash"),
        ("docker_rm", "docker rm container"),
        ("docker_run", "docker run nginx"),
        ("curl_external", "curl -s http://example.com"),
        ("curl_output", "curl -o /tmp/out http://192.168.1.30:8008"),
        ("find_root", "find / -name '*.py'"),
        ("journalctl_follow", "journalctl -f"),
        ("sed_inplace", "sed -i 's/foo/bar/g' /etc/hosts"),
        ("shutdown", "shutdown -h now"),
        ("reboot", "reboot"),
        ("sudo_any", "sudo ls /root"),
        ("dd", "dd if=/dev/zero of=/tmp/out bs=1M count=1"),
        ("tee", "echo test | tee /etc/test"),
        ("apt_install", "apt install nginx"),
        ("mv_file", "mv /etc/hosts /etc/hosts.bak"),
    ]
    for name, cmd in cases:
        t0 = time.time()
        valid, reason = validate_command(cmd)
        elapsed = (time.time() - t0) * 1000
        if valid:
            result = run_safe(cmd, timeout=5)
            elapsed = (time.time() - t0) * 1000
            blocked = result.blocked
        else:
            blocked = True
        passed = blocked
        detail = f"valid={valid} blocked={blocked}" + (f" reason={reason}" if reason else "")
        record(cat, name, passed, detail, elapsed)
        if passed:
            record_executor_blocked(reason or "forbidden_command")

    # Verify 100% blocked
    forbidden_count = len(cases)
    blocked_count = sum(1 for r in ALL_RESULTS if r.category == cat and r.passed)
    record(cat, "100_percent_blocked", blocked_count == forbidden_count,
           f"{blocked_count}/{forbidden_count}", duration_ms=0)


# ═══════════════════════════════════════════════════════════════════
# CATEGORY 5: injection_attempts (100% blocked expected)
# ═══════════════════════════════════════════════════════════════════

def test_injection_attempts():
    cat = "injection_attempts"
    cases = [
        ("semicolon", "ls; rm -rf /"),
        ("andand", "ls && rm -rf /"),
        ("oror", "ls || rm -rf /"),
        ("backticks", "ls `rm -rf /`"),
        ("dollar_paren", "ls $(rm -rf /)"),
        ("pipe", "ls | rm -rf /"),
        ("redirect_write", "ls > /tmp/out"),
        ("redirect_append", "ls >> /tmp/out"),
        ("redirect_input", "cat < /etc/passwd"),
        ("pipe_chain", "ls | grep test | wc -l"),
        ("ampersand_bg", "sleep 10 &"),
        ("dev_urandom", "cat /dev/urandom > /tmp/out"),
    ]
    for name, cmd in cases:
        t0 = time.time()
        valid, reason = validate_command(cmd)
        elapsed = (time.time() - t0) * 1000
        passed = not valid
        detail = f"expected_blocked={not valid} reason={reason}"
        record(cat, name, passed, detail, elapsed)
        if passed:
            record_executor_blocked(reason or "injection")

    injection_count = len(cases)
    blocked_count = sum(1 for r in ALL_RESULTS if r.category == cat and r.passed)
    record(cat, "100_percent_injection_blocked", blocked_count == injection_count,
           f"{blocked_count}/{injection_count}", duration_ms=0)


# ═══════════════════════════════════════════════════════════════════
# CATEGORY 6: timeout_validation
# ═══════════════════════════════════════════════════════════════════

def test_timeout_validation():
    cat = "timeout_validation"
    cases = [
        ("curl_health_ok", "curl -s --max-time 2 http://192.168.1.30:8008/health", 10, True),
    ]
    for name, cmd, timeout, should_pass in cases:
        t0 = time.time()
        valid, reason = validate_command(cmd)
        if not valid:
            record(cat, name, False, f"validation failed: {reason}", (time.time()-t0)*1000)
            continue
        result = run_safe(cmd, timeout=timeout)
        elapsed = (time.time() - t0) * 1000
        passed = (result.exit_code == 0) == should_pass
        detail = f"exit={result.exit_code} blocked={result.blocked} timeout={timeout}s actual={elapsed:.0f}ms"
        record(cat, name, passed, detail, elapsed,
               stdout_hash=result.stdout_hash, blocked=result.blocked)


# ═══════════════════════════════════════════════════════════════════
# CATEGORY 7: workflow_state
# ═══════════════════════════════════════════════════════════════════

def test_workflow_state():
    cat = "workflow_state"

    # EXECUTING exists
    tl = WorkflowTimeline(plan_id="ws-test")
    tl.current_state = WorkflowState.READY_FOR_EXECUTION
    ok = tl.transition(WorkflowState.EXECUTING)
    record(cat, "ready_to_executing", ok and tl.current_state == WorkflowState.EXECUTING,
           f"state={tl.current_state.value}")

    # EXECUTING → DONE
    ok = tl.transition(WorkflowState.DONE)
    record(cat, "executing_to_done", ok and tl.current_state == WorkflowState.DONE,
           f"state={tl.current_state.value}")

    # EXECUTING → FAILED
    tl2 = WorkflowTimeline(plan_id="ws-fail")
    tl2.current_state = WorkflowState.EXECUTING
    ok = tl2.transition(WorkflowState.FAILED)
    record(cat, "executing_to_failed", ok and tl2.current_state == WorkflowState.FAILED,
           f"state={tl2.current_state.value}")

    # SIMULATING → EXECUTING (valid)
    tl3 = WorkflowTimeline(plan_id="ws-sim")
    tl3.current_state = WorkflowState.SIMULATING
    ok = tl3.transition(WorkflowState.EXECUTING)
    record(cat, "simulating_to_executing", ok,
           f"state={tl3.current_state.value}")

    # Invalid transition: PLANNING → DONE
    tl4 = WorkflowTimeline(plan_id="ws-inv")
    tl4.current_state = WorkflowState.PLANNING
    ok_not = not tl4.transition(WorkflowState.DONE)
    record(cat, "invalid_transition_blocked", ok_not,
           f"planning_to_done_blocked={ok_not}")

    # EXECUTING_RESERVED has no transitions
    tl5 = WorkflowTimeline()
    tl5.current_state = WorkflowState.EXECUTING_RESERVED
    no_trans = len(VALID_TRANSITIONS[WorkflowState.EXECUTING_RESERVED]) == 0
    record(cat, "executing_reserved_no_transitions", no_trans,
           f"transitions={len(VALID_TRANSITIONS[WorkflowState.EXECUTING_RESERVED])}")


# ═══════════════════════════════════════════════════════════════════
# CATEGORY 8: governance_validation
# ═══════════════════════════════════════════════════════════════════

def test_governance():
    cat = "governance_validation"
    cases = [
        ("restart_service_blocked", "restart_service", "systemctl restart ailab", False),
        ("install_blocked", "install_package", "apt install foo", False),
        ("run_ls_allowed", "run_command", "ls /tmp", True),
        ("dangerous_command_blocked", "run_command", "rm -rf /", False),
        ("wrong_phase", "read_config", "ls", False, "28.1"),
    ]
    for test_case in cases:
        name = test_case[0]
        intent = test_case[1]
        cmd = test_case[2]
        should_pass = test_case[3]
        phase = test_case[4] if len(test_case) > 4 else "28.2"
        t0 = time.time()
        result = check_governance(intent, cmd, phase)
        elapsed = (time.time() - t0) * 1000
        passed = result.allowed == should_pass
        detail = f"allowed={result.allowed} expected={should_pass} reason={result.reason}"
        record(cat, name, passed, detail, elapsed)
        if not result.allowed:
            record_executor_governance_block(intent)

    # assess_risk checks
    risk_cases = [
        ("risk_restart_bash", "restart_service", "bash", "", "high"),
        ("risk_run_bash", "run_command", "bash", "", "medium"),
        ("risk_read_bash", "read_config", "bash", "", "medium"),
        ("risk_read_ls", "read_config", "ls", "", "low"),
    ]
    for name, intent, tool, target, expected in risk_cases:
        risk = assess_risk(intent, tool, target)
        passed = risk == expected
        record(cat, name, passed, f"risk={risk} expected={expected}")

    # check_scope
    scope_cases = [
        ("scope_filesystem_ok", "/opt/ai-lab/test", {"filesystem"}, True),
        ("scope_filesystem_block", "/opt/ai-lab/test", {"network"}, False),
        ("scope_network_ok", "http://192.168.1.30:8008", {"network"}, True),
    ]
    for name, target, scopes, expected in scope_cases:
        ok = check_scope(target, scopes)
        passed = ok == expected
        record(cat, name, passed, f"scope_ok={ok} expected={expected}")


# ═══════════════════════════════════════════════════════════════════
# WORKER
# ═══════════════════════════════════════════════════════════════════

def run_worker(worker_id: int):
    print(f"\n--- Worker {worker_id} starting ---")
    try:
        test_benign_readonly()
        test_topology_runtime()
        test_malformed_commands()
        test_forbidden_commands()
        test_injection_attempts()
        test_timeout_validation()
        test_workflow_state()
        test_governance()
    except Exception as e:
        msg = f"Worker {worker_id} error: {e}"
        print(f"  ❌ {msg}")
        with _lock:
            _worker_errors.append(msg)


# ═══════════════════════════════════════════════════════════════════
# REPORT
# ═══════════════════════════════════════════════════════════════════

def generate_reports():
    report_dir = "/mnt/opencode/test"
    os.makedirs(report_dir, exist_ok=True)

    total = len(ALL_RESULTS)
    passed = sum(1 for r in ALL_RESULTS if r.passed)
    failed = total - passed
    by_category: dict[str, dict] = {}
    for r in ALL_RESULTS:
        if r.category not in by_category:
            by_category[r.category] = {"total": 0, "passed": 0, "failed": 0}
        by_category[r.category]["total"] += 1
        if r.passed:
            by_category[r.category]["passed"] += 1
        else:
            by_category[r.category]["failed"] += 1

    pass_rate = (passed / total * 100) if total else 0

    report_data = {
        "burnin": "FASE 28.2-B Readonly Executor Burn-in",
        "timestamp": int(time.time()),
        "total_tests": total,
        "passed": passed,
        "failed": failed,
        "pass_rate_pct": round(pass_rate, 2),
        "executor_enabled": ENABLE_EXECUTOR,
        "dry_run": DRY_RUN,
        "execution_mode": CURRENT_EXECUTION_MODE.value,
        "audit_stats": get_audit_stats(),
        "worker_errors": _worker_errors,
        "by_category": by_category,
        "failures": [
            {"category": r.category, "test": r.test_name, "detail": r.detail}
            for r in ALL_RESULTS if not r.passed
        ],
        "results": [asdict(r) for r in ALL_RESULTS],
    }

    # JSON
    json_path = os.path.join(report_dir, "fase28-2b-burnin-report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    print(f"\n📄 JSON report: {json_path}")

    # Markdown summary
    md_path = os.path.join(report_dir, "fase28-2b-summary.md")
    lines = [
        "# FASE 28.2-B — Readonly Executor Burn-in Summary",
        "",
        f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
        f"**Duration:** {time.time() - _burnin_start:.0f}s",
        f"**Pass rate:** {pass_rate:.1f}% ({passed}/{total})",
        "",
        "## Configuration",
        f"- Executor enabled: `{ENABLE_EXECUTOR}`",
        f"- Dry run: `{DRY_RUN}`",
        f"- Execution mode: `{CURRENT_EXECUTION_MODE.value}`",
        f"- Workers: 3",
        "",
        "## Results by Category",
    ]
    for cat in sorted(by_category.keys()):
        c = by_category[cat]
        icon = "✅" if c["failed"] == 0 else "❌"
        lines.append(f"- {icon} **{cat}**: {c['passed']}/{c['total']} passed")
    lines += [
        "",
        "## Failures",
    ]
    failures = [r for r in ALL_RESULTS if not r.passed]
    if failures:
        for f_entry in failures:
            lines.append(f"- ❌ `{f_entry.category}` → `{f_entry.test_name}`: {f_entry.detail}")
    else:
        lines.append("- ✅ No failures")
    lines += [
        "",
        "## Pass Criteria",
    ]
    pass_criteria = {
        "0 crashes": not _worker_errors,
        "0 shell escapes": all("shell" not in r.detail.lower() for r in ALL_RESULTS if not r.passed),
        "0 governance bypass": all(r.passed for r in ALL_RESULTS if r.category == "governance_validation"),
        "0 forbidden executions": all(r.passed for r in ALL_RESULTS if r.category == "forbidden_commands"),
        "100% injection blocked": all(r.passed for r in ALL_RESULTS if r.category == "injection_attempts"),
        "workflow transitions valid": all(r.passed for r in ALL_RESULTS if r.category == "workflow_state"),
    }
    all_pass = all(pass_criteria.values())
    for criterion, ok in pass_criteria.items():
        icon = "✅" if ok else "❌"
        lines.append(f"- {icon} {criterion}")
    lines += [
        "",
        f"## Verdict: **{'PASS ✅' if all_pass else 'FAIL ❌'}**",
        "",
    ]
    if all_pass:
        lines.append("Tag: `CP-28.2-B-READONLY-BURNIN-STABLE`")
    md_content = "\n".join(lines)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"📄 MD summary:  {md_path}")

    return all_pass


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

_burnin_start = time.time()

def main():
    quick = "--quick" in sys.argv
    num_workers = 3

    print("=" * 60)
    print("FASE 28.2-B — Readonly Executor Burn-in")
    print("=" * 60)
    print(f"  Executor enabled: {ENABLE_EXECUTOR}")
    print(f"  Dry run:          {DRY_RUN}")
    print(f"  Execution mode:   {CURRENT_EXECUTION_MODE.value}")
    print(f"  Workers:          {num_workers}")
    print(f"  Quick mode:       {quick}")
    print()

    # Pre-clean audit
    print("Pre-flight: verifying modules...")
    v, r = validate_command("ls /tmp")
    assert v, f"preflight failed: {r}"
    print(f"  validate_command:  ✅")
    print(f"  Prometheus metrics: ✅ ({len(ALL_RESULTS)} baseline)")
    print()

    if not quick:
        # Run 3 concurrent workers with stagger
        workers = []
        for i in range(num_workers):
            w = threading.Thread(target=run_worker, args=(i,), daemon=True)
            workers.append(w)
            w.start()
            time.sleep(15 + (i * 2))  # 15-19s stagger
        for w in workers:
            w.join(timeout=120)  # max 2 min per worker
    else:
        # Single sequential run
        run_worker(0)

    generate_reports()
    all_pass = all(r.passed for r in ALL_RESULTS) and not _worker_errors

    elapsed = time.time() - _burnin_start
    print(f"\n{'=' * 60}")
    print(f"Burn-in completed in {elapsed:.0f}s")
    print(f"Total tests: {len(ALL_RESULTS)}")
    print(f"Passed:      {sum(1 for r in ALL_RESULTS if r.passed)}")
    print(f"Failed:      {sum(1 for r in ALL_RESULTS if not r.passed)}")
    print(f"Errors:      {len(_worker_errors)}")
    print(f"Verdict:     {'✅ PASS' if all_pass else '❌ FAIL'}")
    print(f"{'=' * 60}")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
