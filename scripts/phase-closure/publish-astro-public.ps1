param(
    [switch]$NoPush,
    [switch]$PushOnly,
    [string]$PhaseName = "manual"
)

. (Join-Path $PSScriptRoot "config.ps1")

function Step($n, $m) { Write-Host "--- Step $n : $m ---" -ForegroundColor Magenta }

$ErrorActionPreference = "Continue"
$ASTRO_DIR = Resolve-Path (Join-Path $PSScriptRoot "..\..\apps\ialab-docs")
Set-Location $ASTRO_DIR

# Step 1: Build
if ($PushOnly) {
    Step 1 "Astro build (skipped - PushOnly)"
} else {
    Step 1 "Astro build"
    npm run build 2>&1 | ForEach-Object { Write-Host "  $_" }
    if ($LASTEXITCODE -ne 0) { Write-Host "[FAIL] Build failed" -ForegroundColor Red; exit 1 }
    Write-Host "[PASS] Build OK" -ForegroundColor Green
}

# Step 2: Secret scan
Step 2 "Secret scan"
$secrets = Select-String -Path "dist\**\*" -Pattern "sk-[a-zA-Z0-9]{20,}" -SimpleMatch:$false 2>$null
if ($secrets) { Write-Host "[FAIL] Secrets found in dist/" -ForegroundColor Red; $secrets; exit 1 }
Write-Host "[PASS] No secrets detected" -ForegroundColor Green

# Step 3: Status check
Step 3 "Git status"
git status --short 2>&1 | ForEach-Object { Write-Host "  $_" }
$status = git status --short
if (-not $status) { Write-Host "[WARN] No changes to commit" -ForegroundColor Yellow }

# Step 4: Commit
if ($NoPush) {
    Step 4 "Git commit (skipped - NoPush)"
} else {
    Step 4 "Git commit"
    $changed = git status --short
    if ($changed) {
        git add -A
        git commit -m "feat(docs): $PhaseName - publish Astro public"
        Write-Host "[PASS] Commit created" -ForegroundColor Green
    } else {
        Write-Host "[WARN] Nothing to commit" -ForegroundColor Yellow
    }
}

# Step 5: Push
if ($NoPush) {
    Step 5 "Git push (skipped - NoPush)"
} else {
    Step 5 "Git push"
    git push origin main 2>&1 | ForEach-Object { Write-Host "  $_" }
    if ($LASTEXITCODE -ne 0) { Write-Host "[FAIL] Push failed" -ForegroundColor Red; exit 1 }
    Write-Host "[PASS] Push OK" -ForegroundColor Green
}

# Step 6: Wait for Cloudflare deployment
Step 6 "Wait for Cloudflare deployment"
$timeout = $script:CLOUDFLARE_DEPLOY_TIMEOUT_SECONDS
$deployed = $false
$start = Get-Date
while ((Get-Date) -lt $start.AddSeconds($timeout)) {
    $status = $null
    try { $status = Invoke-WebRequest -Uri $script:PUBLIC_ASTRO_URL -TimeoutSec 10 -UseBasicParsing } catch {}
    if ($status -and $status.StatusCode -eq 200) {
        $deployed = $true
        break
    }
    Start-Sleep -Seconds 15
}
if ($deployed) { Write-Host "[PASS] Deployment detected" -ForegroundColor Green } else { Write-Host "[FAIL] Not detected within timeout" -ForegroundColor Red; exit 1 }

# Step 7: Validate URLs
Step 7 "Validate public URLs"
$allOk = $true
$urls = $script:VALIDATION_URLS_PUBLIC | ForEach-Object { $script:PUBLIC_ASTRO_URL + $_ }
foreach ($u in $urls) {
    try {
        $r = Invoke-WebRequest -Uri $u -TimeoutSec 10 -UseBasicParsing
        if ($r.StatusCode -eq 200) { Write-Host "  [200] $u" -ForegroundColor Green } else { Write-Host "  [$($r.StatusCode)] $u" -ForegroundColor Red; $allOk = $false }
    } catch { Write-Host "  [ERR] $u - $_" -ForegroundColor Red; $allOk = $false }
}
if (-not $allOk) { Write-Host "[FAIL] URL validation failed" -ForegroundColor Red; exit 1 }
Write-Host "[PASS] All public URLs OK" -ForegroundColor Green
exit 0
