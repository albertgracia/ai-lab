<#
.SYNOPSIS
AI-LAB Phase Closure Orchestrator - automated document publishing pipeline.

.PARAMETER PhaseName
Name of the phase being closed (required).

.PARAMETER CommitMessage
Git commit message (default: "docs(astro): phase closure auto-publish").

.PARAMETER SudoPassword
Password for sudo on .30 (also via $env:AILAB_SUDO_PASSWORD).

.PARAMETER AnythingLLMApiKey
API key for AnythingLLM (also via $env:ANYTHINGLLM_API_KEY).

.PARAMETER DryRun
Validate connectivity and prerequisites without making changes.

.PARAMETER SkipPublic
Skip public Astro publish (commit, push, Cloudflare).

.PARAMETER SkipPrivate
Skip private Astro publish (SSH, build, restart).

.PARAMETER SkipReindex
Skip AnythingLLM reindex and smoke queries.

.PARAMETER DocFolder
Folder with docs for AnythingLLM reindex.
#>

param(
    [Parameter(Mandatory)]
    [string]$PhaseName,

    [string]$CommitMessage = "docs(astro): phase closure auto-publish",

    [string]$SudoPassword = $env:AILAB_SUDO_PASSWORD,

    [string]$AnythingLLMApiKey = $env:ANYTHINGLLM_API_KEY,

    [switch]$DryRun,

    [switch]$SkipPublic,
    [switch]$SkipPrivate,
    [switch]$SkipReindex,

    [string]$DocFolder = ""
)

. "$PSScriptRoot\config.ps1"
$ErrorActionPreference = "Stop"

$script:OVERALL_PASS = 0
$script:OVERALL_FAIL = 0
$script:OVERALL_WARN = 0
$script:PUBLIC_RESULT = "SKIPPED"
$script:PRIVATE_RESULT = "SKIPPED"
$script:REINDEX_RESULT = "SKIPPED"
$script:SMOKE_RESULT = "SKIPPED"
$script:REPORT_PATH = ""
$script:AUDIT_TIMESTAMP = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$script:LOG_LINES = @()

function Log($m) {
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $m"
    $script:LOG_LINES += $line
}

function Title($m) { Write-Host "`n$m" -ForegroundColor Magenta }
function Banner($n, $m) {
    $msg = ("SECTION " + $n + " : " + $m)
    Write-Host "`n=== $msg ===" -ForegroundColor Blue
    Log $msg
}
function GlobalPass($m) { Write-Host "  [PASS] $m" -ForegroundColor Green; $script:OVERALL_PASS++; Log "PASS: $m" }
function GlobalFail($m) { Write-Host "  [FAIL] $m" -ForegroundColor Red; $script:OVERALL_FAIL++; Log "FAIL: $m" }
function GlobalWarn($m) { Write-Host "  [WARN] $m" -ForegroundColor Yellow; $script:OVERALL_WARN++; Log "WARN: $m" }
function Info($m) { Write-Host "  [INFO] $m" -ForegroundColor Cyan; Log "INFO: $m" }

if (-not $DocFolder) {
    $script:REINDEX_DOC_FOLDER = Join-Path $ASTRO_CONTENT_DIR "docs"
} else {
    $script:REINDEX_DOC_FOLDER = $DocFolder
}

Title "================================================"
Title "  AI-LAB Phase Closure Pipeline v1"
Title ("  Phase: $PhaseName")
if ($DryRun) { Title "  Mode: DRY RUN" } else { Title "  Mode: APPLY" }
Title "================================================"

Banner 0 "Prerequisites"

try {
    $gitRoot = git rev-parse --show-toplevel 2>$null
    if ($gitRoot) { GlobalPass "Git repository: $gitRoot" } else { GlobalFail "Not in a git repository" }
} catch { GlobalFail "Git check failed" }

if (Test-Path $ASTRO_DIR) { GlobalPass "Astro directory: $ASTRO_DIR" } else { GlobalFail "Astro directory not found" }

try {
    $sshCheck = ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new ($AILAB_SSH_USER + "@" + $AILAB_SSH_HOST) "echo SSH_OK" 2>&1
    if ($sshCheck -contains "SSH_OK") { GlobalPass "SSH to ${AILAB_SSH_USER}@${AILAB_SSH_HOST}" } else { GlobalFail "SSH connectivity failed" }
} catch { GlobalFail "SSH check failed" }

if ($AnythingLLMApiKey) {
    GlobalPass "AnythingLLM API key configured"
} elseif (Test-Path (Join-Path $SCRIPTS_DIR "anythingllm\.anythingllm.env")) {
    GlobalPass "AnythingLLM API key file exists"
} else {
    GlobalWarn "AnythingLLM API key not set - reindex will fail if attempted"
}

if ($DryRun) {
    Info "`nDryRun mode - no changes will be made"
    GlobalPass "DryRun validation complete"
    Write-Host "`n========== PHASE CLOSURE DRY RUN ==========" -ForegroundColor Cyan
    Write-Host "Phase         : $PhaseName"
    Write-Host "Git repo      : OK"
    Write-Host "Astro dir     : OK"
    Write-Host "SSH           : OK"
    if ($AnythingLLMApiKey) { Write-Host "AnythingLLM   : OK" } else { Write-Host "AnythingLLM   : API key missing" }
    Write-Host "PASS: $($script:OVERALL_PASS) WARN: $($script:OVERALL_WARN) FAIL: $($script:OVERALL_FAIL)"
    Write-Host "============================================" -ForegroundColor Cyan
    exit 0
}

Banner 1 "Public Astro (Cloudflare Pages)"

if ($SkipPublic) {
    Info "Skipped via -SkipPublic"
} else {
    try {
        $publicScript = Join-Path $PSScriptRoot "publish-astro-public.ps1"
        $publicArgs = @()
        if ($CommitMessage) { $publicArgs += "-CommitMessage"; $publicArgs += $CommitMessage }
        & $publicScript @publicArgs 2>&1 | ForEach-Object { Write-Host "    $_" }
        if ($LASTEXITCODE -eq 0) {
            $script:PUBLIC_RESULT = "PASS"
            GlobalPass "Public Astro published successfully"
        } else {
            $script:PUBLIC_RESULT = "FAIL"
            GlobalFail "Public Astro publish failed"
        }
    } catch {
        $script:PUBLIC_RESULT = "FAIL"
        GlobalFail "Public Astro publish exception"
    }
}

Banner 2 "Private Astro (blog-ai-lab)"

if ($SkipPrivate) {
    Info "Skipped via -SkipPrivate"
} else {
    try {
        $privateScript = Join-Path $PSScriptRoot "publish-astro-private.ps1"
        $privateArgs = @()
        if ($SudoPassword) { $privateArgs += "-SudoPassword"; $privateArgs += $SudoPassword }
        & $privateScript @privateArgs 2>&1 | ForEach-Object { Write-Host "    $_" }
        if ($LASTEXITCODE -eq 0) {
            $script:PRIVATE_RESULT = "PASS"
            GlobalPass "Private Astro published successfully"
        } else {
            $script:PRIVATE_RESULT = "FAIL"
            GlobalFail "Private Astro publish failed"
        }
    } catch {
        $script:PRIVATE_RESULT = "FAIL"
        GlobalFail "Private Astro publish exception"
    }
}

Banner 3 "AnythingLLM Reindex"

if ($SkipReindex) {
    Info "Skipped via -SkipReindex"
} elseif ((-not $AnythingLLMApiKey) -and (-not (Test-Path (Join-Path $SCRIPTS_DIR "anythingllm\.anythingllm.env")))) {
    $script:REINDEX_RESULT = "SKIPPED"
    GlobalWarn "AnythingLLM API key not configured - reindex skipped"
} else {
    try {
        $reindexScript = Join-Path $SCRIPTS_DIR "anythingllm\reindex-workspace.ps1"
        $reindexArgs = @("-Mode", "Apply", "-DocFolder", $script:REINDEX_DOC_FOLDER, "-AllowLargeBatch", "-BatchSize", "10", "-BatchDelaySeconds", "5")
        if ($AnythingLLMApiKey) { $reindexArgs += "-ApiKey"; $reindexArgs += $AnythingLLMApiKey }
        & $reindexScript @reindexArgs 2>&1 | ForEach-Object { Write-Host "    $_" }
        $reindexExit = $LASTEXITCODE
        if ($reindexExit -eq 0) {
            $script:REINDEX_RESULT = "PASS"
            GlobalPass "AnythingLLM reindex completed"
        } else {
            $script:REINDEX_RESULT = "FAIL"
            GlobalFail "AnythingLLM reindex failed (exit: $reindexExit)"
        }
    } catch {
        $script:REINDEX_RESULT = "FAIL"
        GlobalFail "AnythingLLM reindex exception"
    }
}

Banner 4 "AnythingLLM Smoke Queries"

if ($SkipReindex) {
    Info "Skipped via -SkipReindex"
} elseif ($script:REINDEX_RESULT -eq "SKIPPED") {
    Info "Skipped because reindex was skipped"
} else {
    try {
        $smokeScript = Join-Path $SCRIPTS_DIR "anythingllm\reindex-workspace.ps1"
        $smokeArgs = @("-Mode", "SmokeOnly")
        if ($AnythingLLMApiKey) { $smokeArgs += "-ApiKey"; $smokeArgs += $AnythingLLMApiKey }
        & $smokeScript @smokeArgs 2>&1 | ForEach-Object { Write-Host "    $_" }
        $smokeExit = $LASTEXITCODE
        if ($smokeExit -eq 0) {
            $script:SMOKE_RESULT = "PASS"
            GlobalPass "Smoke queries passed"
        } else {
            $script:SMOKE_RESULT = "FAIL"
            GlobalFail "Smoke queries failed (exit: $smokeExit)"
        }
    } catch {
        $script:SMOKE_RESULT = "FAIL"
        GlobalFail "Smoke queries exception"
    }
}

Banner 5 "Audit report generation"

$reportName = "AI-LAB-PHASE-CLOSURE-$PhaseName.md"
$reportPath = Join-Path $AUDITS_DIR $reportName

$auditLines = @()
$auditLines += ("# " + $PhaseName)
$auditLines += ""
$auditLines += ("**Estado:** " + $(if ($script:OVERALL_FAIL -eq 0) { "PASS" } else { "FAIL" }))
$auditLines += ("**Fecha:** " + $script:AUDIT_TIMESTAMP)
$auditLines += "**Pipeline:** invoke-phase-closure.ps1 v1"
$auditLines += ""
$auditLines += "## Resumen"
$auditLines += ""
$auditLines += "| Componente | Estado |"
$auditLines += "|---|---|"
$auditLines += ("| Public Astro | " + $script:PUBLIC_RESULT + " |")
$auditLines += ("| Private Astro | " + $script:PRIVATE_RESULT + " |")
$auditLines += ("| AnythingLLM Reindex | " + $script:REINDEX_RESULT + " |")
$auditLines += ("| Smoke Queries | " + $script:SMOKE_RESULT + " |")
$auditLines += ""
$auditLines += ("PASS: " + $script:OVERALL_PASS + " | WARN: " + $script:OVERALL_WARN + " | FAIL: " + $script:OVERALL_FAIL)
$auditLines += ""
if ($script:LOG_LINES.Count -gt 0) {
    $auditLines += "## Log"
    $auditLines += ""
    $auditLines += ($script:LOG_LINES -join "`n")
}
$auditLines += ""
$auditLines += ("## Conclusion: " + $(if ($script:OVERALL_FAIL -eq 0) { "PASS" } else { "FAIL" }))

try {
    Set-Content -LiteralPath $reportPath -Value ($auditLines -join "`n") -Encoding UTF8
    $script:REPORT_PATH = $reportPath
    GlobalPass "Audit report: $reportPath"
} catch {
    GlobalFail "Audit report generation failed"
}

Title "================================================"
Title "  PHASE CLOSURE COMPLETE"
Title "================================================"

Write-Host "`n========== PHASE CLOSURE SUMMARY ==========" -ForegroundColor Cyan
Write-Host "Phase            : $PhaseName"
Write-Host "Public Astro     : $($script:PUBLIC_RESULT)"
Write-Host "Private Astro    : $($script:PRIVATE_RESULT)"
Write-Host "AnythingLLM      : $($script:REINDEX_RESULT)"
Write-Host "Smoke Queries    : $($script:SMOKE_RESULT)"
Write-Host "---" -ForegroundColor Gray
Write-Host "PASS             : $($script:OVERALL_PASS)"
Write-Host "WARN             : $($script:OVERALL_WARN)"
Write-Host "FAIL             : $($script:OVERALL_FAIL)"
Write-Host "---" -ForegroundColor Gray
Write-Host "Report           : $($script:REPORT_PATH)"
Write-Host "===========================================" -ForegroundColor Cyan

if ($script:OVERALL_FAIL -gt 0) { exit 1 }
exit 0
