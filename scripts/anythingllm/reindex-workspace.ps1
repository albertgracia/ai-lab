<#
.SYNOPSIS
Reindex AnythingLLM workspace after documentation changes.

.DESCRIPTION
Uploads documents to AnythingLLM in batches, links them to a workspace,
and runs smoke queries to validate retrieval.

Supports three modes:
  - DryRun: validate connectivity without changes
  - Apply: upload + embed + smoke
  - SmokeOnly: validate retrieval without uploads

Features:
  - Batch processing (default 10 files per batch)
  - MaxFiles guard (default 20, override with -AllowLargeBatch)
  - Incremental mode via -ChangedFilesPath
  - Auto-excludes: docs/archive/**, docs/quarantine/**, docs/audits/** (unless -IncludeAudits)
  - Per-batch embedding update + workspace confirmation
  - Default workspace slug: ai-lab-core

.PARAMETER Mode
DryRun | Apply | SmokeOnly

.PARAMETER BaseUrl
AnythingLLM base URL (default: $env:ANYTHINGLLM_BASE_URL)

.PARAMETER WorkspaceSlug
Target workspace slug (default: ai-lab-core)

.PARAMETER ApiKey
API key (default: $env:ANYTHINGLLM_API_KEY)

.PARAMETER DocFolder
Local folder with documentation files (for small folders only)

.PARAMETER ChangedFilesPath
Path to a text file with one relative path per line (incremental mode)

.PARAMETER BatchSize
Files per embedding batch (default: 10)

.PARAMETER BatchDelaySeconds
Seconds to wait between batches (default: 5)

.PARAMETER MaxFiles
Max files to process without -AllowLargeBatch (default: 20)

.PARAMETER AllowLargeBatch
Bypass MaxFiles guard

.PARAMETER IncludeAudits
Include docs/audits/ in upload

.PARAMETER AllowLargeFiles
Include files > 500KB

.PARAMETER MaxFileSizeKB
Maximum file size in KB (default: 500)

.EXAMPLE
.\scripts\anythingllm\reindex-workspace.ps1 -Mode DryRun
.\scripts\anythingllm\reindex-workspace.ps1 -Mode Apply -ChangedFilesPath ./changed.txt -BatchSize 5
.\scripts\anythingllm\reindex-workspace.ps1 -Mode Apply -DocFolder ./new-docs -MaxFiles 5
.\scripts\anythingllm\reindex-workspace.ps1 -Mode SmokeOnly
#>

param(
    [ValidateSet("DryRun","Apply","SmokeOnly")]
    [string]$Mode = "DryRun",

    [string]$BaseUrl = $env:ANYTHINGLLM_BASE_URL,
    [string]$WorkspaceSlug = $(if ($env:ANYTHINGLLM_WORKSPACE_SLUG) { $env:ANYTHINGLLM_WORKSPACE_SLUG } else { "ai-lab-core" }),
    [string]$ApiKey = $env:ANYTHINGLLM_API_KEY,

    [string]$DocFolder,
    [string]$ChangedFilesPath,

    [int]$BatchSize = 10,
    [int]$BatchDelaySeconds = 5,
    [int]$MaxFiles = 20,
    [switch]$AllowLargeBatch,
    [switch]$IncludeAudits,
    [switch]$AllowLargeFiles,
    [int]$MaxFileSizeKB = 500
)

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
$ErrorActionPreference = "Stop"

if (-not $BaseUrl) { throw "ANYTHINGLLM_BASE_URL not set." }
if (-not $ApiKey) { throw "ANYTHINGLLM_API_KEY not set." }

$BaseUrl = $BaseUrl.TrimEnd("/")
$Api = "$BaseUrl/api"
$Headers = @{
    Authorization = "Bearer $ApiKey"
    Accept = "application/json"
}

$PASS = 0; $FAIL = 0; $WARN = 0
$UploadedLocations = @()
$BatchesProcessed = 0
$FilesUploaded = 0
$FilesSkipped = 0

function Pass($m) { Write-Host "  [PASS] $m" -ForegroundColor Green; $script:PASS++ }
function Fail($m) { Write-Host "  [FAIL] $m" -ForegroundColor Red; $script:FAIL++; exit 1 }
function Warn($m) { Write-Host "  [WARN] $m" -ForegroundColor Yellow; $script:WARN++ }
function Info($m) { Write-Host "  [INFO] $m" -ForegroundColor Cyan }
function Step($n,$m) { Write-Host "`n─── Step ${n}: $m ───" -ForegroundColor Cyan }

function Invoke-ALLM {
    param([string]$Method, [string]$Path, $Body = $null)
    $params = @{
        Uri = "$Api$Path"
        Method = $Method
        Headers = $Headers
        ContentType = "application/json"
    }
    if ($null -ne $Body) {
        $params.Body = ($Body | ConvertTo-Json -Depth 20 -Compress)
    }
    return Invoke-RestMethod @params
}

function Confirm-WorkspaceDocuments {
    param([string]$Slug, [int]$ExpectedMin)
    try {
        $d = Invoke-ALLM GET "/v1/workspace/$Slug"
        $w = $d.workspace
        if ($w -is [array]) { $w = $w[0] }
        $count = @($w.documents).Count
        if ($count -ge $ExpectedMin) {
            Pass "Workspace '$Slug' now has $count document(s)"
            return $true
        } else {
            Warn "Workspace '$Slug' has $count document(s) (expected >= $ExpectedMin)"
            return $false
        }
    } catch {
        Warn "Failed to verify workspace docs: $_"
        return $false
    }
}

# ──────────────────────────────────────────────
# STEP 1: AUTH
# ──────────────────────────────────────────────
Step 1 "Authentication"
try {
    $auth = Invoke-ALLM GET "/v1/auth"
    if ($auth.authenticated -eq $true) {
        Pass "Authenticated against $BaseUrl"
    } else {
        Fail "API key rejected"
    }
} catch {
    Fail "Auth failed: $_"
}

# ──────────────────────────────────────────────
# STEP 2: WORKSPACE LOOKUP
# ──────────────────────────────────────────────
Step 2 "Workspace lookup"
try {
    $wsList = Invoke-ALLM GET "/v1/workspaces"
    $workspaces = @($wsList.workspaces)
    Pass "$($workspaces.Count) workspace(s) found"
    foreach ($w in $workspaces) {
        $mark = if ($w.slug -eq $WorkspaceSlug) { " <-- TARGET" } else { "" }
        Info "[$($w.id)] $($w.name) (slug: $($w.slug))$mark"
    }
    $target = $workspaces | Where-Object { $_.slug -eq $WorkspaceSlug } | Select-Object -First 1
    if (-not $target) { Fail "Target workspace '$WorkspaceSlug' not found" }
    Pass "Target workspace '$WorkspaceSlug' found"
} catch {
    Fail "Workspace lookup failed: $_"
}

# ──────────────────────────────────────────────
# STEP 3: WORKSPACE DETAILS
# ──────────────────────────────────────────────
Step 3 "Workspace details"
try {
    $detail = Invoke-ALLM GET "/v1/workspace/$WorkspaceSlug"
    $workspace = $detail.workspace
    if ($workspace -is [array]) { $workspace = $workspace[0] }
    Info "Name: $($workspace.name)"
    $docCount = @($workspace.documents).Count
    Pass "$docCount document(s) currently attached"
    @($workspace.documents) | Select-Object -First 10 | ForEach-Object {
        $name = if ($_.name) { $_.name } else { $_.title }
        Info "  - $name"
    }
} catch {
    Fail "Workspace details failed: $_"
}

# ──────────────────────────────────────────────
# STEP 4: COLLECT FILES (DryRun + Apply)
# ──────────────────────────────────────────────
Step 4 "File collection"

$candidateFiles = @()

if ($ChangedFilesPath) {
    if (-not (Test-Path $ChangedFilesPath -PathType Leaf)) {
        Fail "ChangedFilesPath not found: $ChangedFilesPath"
    }
    $changedLines = Get-Content $ChangedFilesPath | Where-Object { $_.Trim() -ne "" -and -not $_.TrimStart().StartsWith("#") }
    $resolvedRoot = Resolve-Path "."
    foreach ($line in $changedLines) {
        $path = $line.Trim()
        $fullPath = Join-Path $resolvedRoot $path
        if (Test-Path $fullPath -PathType Leaf) {
            $candidateFiles += Get-Item $fullPath
        } else {
            Warn "Changed file not found: $path"
        }
    }
    Info "ChangedFilesPath: $($candidateFiles.Count) file(s) resolved"
} elseif ($DocFolder) {
    if (-not (Test-Path $DocFolder -PathType Container)) {
        Fail "DocFolder not found: $DocFolder"
    }
    $candidateFiles = Get-ChildItem $DocFolder -Recurse -File | Where-Object {
        $_.Extension -match '^\.(md|txt|json|yaml|yml|html)$'
    }
    Info "DocFolder: $($candidateFiles.Count) file(s) found"
} else {
    Info "No file source provided. Use -DocFolder or -ChangedFilesPath for Apply."
}

# Filter by extension (already done above for DocFolder, but ChangedFilesPath bypasses)
$candidateFiles = $candidateFiles | Where-Object { $_.Extension -match '^\.(md|txt|json|yaml|yml|html)$' }

# Apply exclusions
$excludedPatterns = @(
    '\barchive[\\/]',
    '\bquarantine[\\/]'
)
if (-not $IncludeAudits) {
    $excludedPatterns += '\baudits[\\/]'
}

$beforeExclude = $candidateFiles.Count
$candidateFiles = $candidateFiles | Where-Object {
    $path = $_.FullName
    $excluded = $false
    foreach ($pat in $excludedPatterns) {
        if ($path -match $pat) { $excluded = $true; break }
    }
    if (-not $excluded -and -not $AllowLargeFiles) {
        if ($_.Length -gt ($MaxFileSizeKB * 1KB)) { $excluded = $true }
    }
    if ($excluded) { $script:FilesSkipped++ }
    -not $excluded
}
$excludedCount = $beforeExclude - $candidateFiles.Count
if ($excludedCount -gt 0) {
    Warn "$excludedCount file(s) excluded (audits/archive/quarantine/size)"
    Info "  Use -IncludeAudits, -AllowLargeFiles to override"
}

$fileCount = $candidateFiles.Count
Info "$fileCount candidate file(s) after filtering"

# MaxFiles guard
if ($fileCount -gt $MaxFiles -and -not $AllowLargeBatch) {
    Fail "Found $fileCount files, exceeds -MaxFiles $MaxFiles. Use -AllowLargeBatch to override."
}

if ($Mode -eq "Apply" -and $fileCount -eq 0) {
    Fail "No files to process in Apply mode"
}

if ($Mode -eq "DryRun") {
    Step 5 "DryRun summary"
    Info "Mode: DryRun — no changes will be made"
    if ($fileCount -gt 0) {
        Info ("Would process {0} file(s) in batches of {1}:" -f $fileCount, $BatchSize)
        $batches = [math]::Ceiling($fileCount / $BatchSize)
        for ($b = 0; $b -lt $batches; $b++) {
            $start = $b * $BatchSize
            $batchFiles = $candidateFiles[$start..([math]::Min($start + $BatchSize - 1, $fileCount - 1))]
            Info ("  Batch {0}/{1}: {2} file(s)" -f ($b + 1), $batches, $batchFiles.Count)
            foreach ($f in $batchFiles) {
                $rel = [System.IO.Path]::GetRelativePath((Resolve-Path "."), $f.FullName)
                $sk = [math]::Round($f.Length / 1024, 1)
                Info ("    - " + $rel + " (" + $sk + " KB)")
            }
        }
        Info "Would execute $batches update-embeddings call(s) with $BatchDelaySeconds s delay"
    } else {
        Info "No files to upload. DryRun validated connectivity only."
    }
    Pass "DryRun completed. No changes made."
    exit 0
}

# ──────────────────────────────────────────────
# STEP 5: APPLY — UPLOAD + BATCHED EMBEDDINGS
# ──────────────────────────────────────────────
if ($Mode -eq "Apply") {
    Step 5 "Upload + batch embeddings"

    $totalBatches = [math]::Ceiling($fileCount / $BatchSize)
    Info "Processing $fileCount file(s) in $totalBatches batch(es)"

    for ($b = 0; $b -lt $totalBatches; $b++) {
        $start = $b * $BatchSize
        $end = [math]::Min($start + $BatchSize - 1, $fileCount - 1)
        $batchFiles = $candidateFiles[$start..$end]
        $batchNum = $b + 1

        Write-Progress -Activity "Upload + embed batch" -Status "Batch $batchNum / $totalBatches" -PercentComplete (($b / $totalBatches) * 100)

        Info "Batch $batchNum / $totalBatches — $($batchFiles.Count) file(s)"

        $batchLocations = @()

        foreach ($file in $batchFiles) {
            try {
                $content = Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8
                $relPath = [System.IO.Path]::GetRelativePath((Resolve-Path "."), $file.FullName)

                $body = @{
                    textContent = $content
                    metadata = @{
                        title = $file.BaseName
                        docAuthor = "AI-LAB"
                        description = "Auto-uploaded"
                        docSource = $relPath
                    }
                }

                $upload = Invoke-ALLM POST "/v1/document/raw-text" $body

                if ($upload.success -and $upload.documents) {
                    foreach ($d in $upload.documents) {
                        if ($d.location) {
                            $batchLocations += $d.location
                            $script:UploadedLocations += $d.location
                        }
                    }
                    $script:FilesUploaded++
                } else {
                    Warn "Upload returned no location: $($file.Name)"
                }
            } catch {
                Warn "Upload failed: $($file.Name) — $_"
            }
        }

        if ($batchLocations.Count -eq 0) {
            Warn "No documents uploaded in batch $batchNum — skipping update-embeddings"
            continue
        }

        $embedBody = @{ adds = $batchLocations; deletes = @() }
        try {
            $update = Invoke-ALLM POST "/v1/workspace/$WorkspaceSlug/update-embeddings" $embedBody
            $script:BatchesProcessed++
            Pass ("Batch {0}: added {1} document(s) to workspace" -f $batchNum, $batchLocations.Count)
        } catch {
            Warn "Batch $batchNum embedding update failed: $_"
        }

        # Confirm workspace has the new docs
        Confirm-WorkspaceDocuments -Slug $WorkspaceSlug -ExpectedMin ($docCount + $script:FilesUploaded) | Out-Null

        # Delay between batches (unless last batch)
        if ($b -lt $totalBatches - 1) {
            Info "Waiting $BatchDelaySeconds second(s) before next batch..."
            Start-Sleep -Seconds $BatchDelaySeconds
        }
    }

    Write-Progress -Activity "Upload + embed batch" -Completed
    Pass "All batches complete: $BatchesProcessed batch(es), $FilesUploaded file(s) uploaded"
}

# ──────────────────────────────────────────────
# STEP 6: SMOKE QUERIES
# ──────────────────────────────────────────────
if ($Mode -eq "SmokeOnly" -or $Mode -eq "Apply") {
    Step 6 "Smoke queries"

    $questions = @(
        @{
            q = "¿Qué exige el protocolo de cierre de fase si hay impacto documental?"
            expected = "document"
        },
        @{
            q = "¿Qué es el Cognitive Health Layer 37A?"
            expected = "health|37A|cognitive"
        },
        @{
            q = "¿Por qué validation_score era 56.3?"
            expected = "Prometheus|sensor|safety|56.3"
        }
    )

    $ok = 0

    foreach ($item in $questions) {
        try {
            $body = @{
                message = $item.q
                mode = "query"
            }
            $resp = Invoke-ALLM POST "/v1/workspace/$WorkspaceSlug/chat" $body
            $answer = [string]$resp.textResponse
            $hasSources = ($resp.sources -and $resp.sources.Count -gt 0)

            if ($answer -match $item.expected -and $hasSources) {
                Pass "Smoke OK (cited): $($item.q)"
                $ok++
            } elseif ($answer -match $item.expected) {
                Pass "Smoke OK: $($item.q)"
                $ok++
            } else {
                Warn "Smoke weak: $($item.q)"
                Info ($answer.Substring(0, [Math]::Min(200, $answer.Length)))
            }
        } catch {
            Warn "Smoke failed: $($item.q) — $_"
        }
    }

    Info "Smoke result: $ok / $($questions.Count)"
}

# ──────────────────────────────────────────────
# SUMMARY
# ──────────────────────────────────────────────
Write-Host "`n═══════════════════════════════════════" -ForegroundColor Cyan
Write-Host " ANYTHINGLLM REINDEX SUMMARY" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Workspace      : $WorkspaceSlug"
Write-Host "Base URL       : $BaseUrl"
Write-Host "Mode           : $Mode"
Write-Host "Batch size     : $BatchSize"
Write-Host "Files          :"
Write-Host "  Uploaded     : $FilesUploaded"
Write-Host "  Skipped      : $FilesSkipped"
Write-Host "  Total batches: $BatchesProcessed"
Write-Host "Checks         :"
Write-Host "  PASS         : $PASS"
Write-Host "  WARN         : $WARN"
Write-Host "  FAIL         : $FAIL"
Write-Host "═══════════════════════════════════════" -ForegroundColor Cyan

if ($FAIL -gt 0) { exit 1 }
exit 0
