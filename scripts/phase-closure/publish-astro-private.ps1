param(
    [switch]$BuildOnly,
    [string]$PhaseName = "manual",
    [string]$SudoPassword = ""
)

. (Join-Path $PSScriptRoot "config.ps1")

function Step($n, $m) { Write-Host "--- Step $n : $m ---" -ForegroundColor Magenta }

$ErrorActionPreference = "Continue"
$hostStr = "${script:AILAB_SSH_USER}@${script:AILAB_SSH_HOST}"

# Step 1: SSH connectivity
Step 1 "SSH connectivity to $hostStr"
$sshTest = ssh -o BatchMode=yes -o ConnectTimeout=5 $hostStr "echo SSH_OK" 2>&1
if ($sshTest -notcontains "SSH_OK") { Write-Host "[FAIL] SSH failed" -ForegroundColor Red; exit 1 }
Write-Host "[PASS] SSH OK" -ForegroundColor Green

# Step 2: Git status on remote
Step 2 "Git status on remote"
ssh $hostStr "cd ${script:AILAB_REMOTE_REPO} && git status --short" 2>&1 | ForEach-Object { Write-Host "  $_" }

# Step 3: Git pull
Step 3 "Git pull"
ssh $hostStr "cd ${script:AILAB_REMOTE_REPO} && git pull --ff-only" 2>&1 | ForEach-Object { Write-Host "  $_" }

# Step 4: NPM install (if needed)
Step 4 "NPM install (if needed)"
ssh $hostStr "cd ${script:AILAB_REMOTE_REPO}/apps/ialab-docs && npm install" 2>&1 | ForEach-Object { Write-Host "  $_" }

# Step 5: Build
Step 5 "Astro build"
ssh $hostStr "cd ${script:AILAB_REMOTE_REPO}/apps/ialab-docs && npm run build" 2>&1 | ForEach-Object { Write-Host "  $_" }

# Step 6: Restart service
if ($BuildOnly) {
    Step 6 "Service restart (skipped - BuildOnly)"
} else {
    Step 6 "Restart ailab-docs"
    $pw = if ($SudoPassword) { $SudoPassword } else { $env:AILAB_SUDO_PASSWORD }
    if ($pw) {
        ssh $hostStr "echo '$pw' | sudo -S systemctl restart ailab-docs" 2>&1 | ForEach-Object { Write-Host "  $_" }
    } else {
        Write-Host "  [WARN] No sudo password - skipping restart (service may need manual restart)" -ForegroundColor Yellow
    }
    if ($LASTEXITCODE -ne 0) { Write-Host "[FAIL] Restart failed" -ForegroundColor Red; exit 1 }
    Write-Host "[PASS] Restart OK" -ForegroundColor Green
}

# Step 7: Validate private URLs
Step 7 "Validate private URLs"
Start-Sleep -Seconds 3
$allOk = $true
$urls = $script:VALIDATION_URLS_PRIVATE | ForEach-Object { $script:PRIVATE_ASTRO_LOCAL_URL + $_ }
foreach ($u in $urls) {
    try {
        $r = ssh $hostStr "curl -s -o /dev/null -w '%{http_code}' '$u'" 2>&1
        if ($r -eq "200") { Write-Host "  [200] $u" -ForegroundColor Green } else { Write-Host "  [$r] $u" -ForegroundColor Red; $allOk = $false }
    } catch { Write-Host "  [ERR] $u - $_" -ForegroundColor Red; $allOk = $false }
}
if (-not $allOk) { Write-Host "[FAIL] URL validation failed" -ForegroundColor Red; exit 1 }
Write-Host "[PASS] All private URLs OK" -ForegroundColor Green
exit 0
