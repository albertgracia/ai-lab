<#
.SYNOPSIS
Reindex AnythingLLM workspace after documentation changes.

.DESCRIPTION
Uploads documents to AnythingLLM in batches, links them to a workspace,
then triggers update-embeddings for the workspace.

Modes:
  - DryRun: validate connectivity and file selection without changes
  - Apply: upload + embed + smoke
  - SmokeOnly: validate retrieval without uploads

Configuration from .anythingllm.env (PSScriptRoot):
  ANYTHINGLLM_BASE_URL=http://127.0.0.1:3001
  ANYTHINGLLM_WORKSPACE_SLUG=ai-lab-core
  ANYTHINGLLM_API_KEY=<secret>

Environment variables take precedence over .anythingllm.env.
#>

param(
    [ValidateSet("DryRun", "Apply", "SmokeOnly")]
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

$ErrorActionPreference = "Stop"

$dotEnvPath = Join-Path $PSScriptRoot ".anythingllm.env"
if ((Test-Path $dotEnvPath) -and (-not $ApiKey -or -not $BaseUrl)) {
    Get-Content $dotEnvPath | ForEach-Object {
        if ($_ -match "^\s*([^#][^=]+)=(.*)$") {
            $k = $matches[1].Trim()
            $v = $matches[2].Trim()
            if ($k -eq "ANYTHINGLLM_API_KEY" -and -not $ApiKey) { $ApiKey = $v }
            if ($k -eq "ANYTHINGLLM_BASE_URL" -and -not $BaseUrl) { $BaseUrl = $v }
            if ($k -eq "ANYTHINGLLM_WORKSPACE_SLUG" -and -not $PSBoundParameters.ContainsKey("WorkspaceSlug")) { $WorkspaceSlug = $v }
        }
    }
}

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
function Step($n, $m) { Write-Host "--- Step $n : $m ---" -ForegroundColor Cyan }

function Invoke-ALLM {
    param([string]$Method, [string]$Path, $Body = $null)
    $params = @{
        Uri = "$Api$Path"
        Method = $Method
        Headers = $HEADERS
        UseBasicParsing = $true
        ContentType = "application/json"
    }
    if ($Body) { $params.Body = ($Body | ConvertTo-Json -Depth 10 -Compress) }
    try {
        $resp = Invoke-WebRequest @params
        return ($resp.Content | ConvertFrom-Json)
    } catch {
        $err = $_.Exception.Response
        if ($err) {
            $reader = New-Object System.IO.StreamReader($err.GetResponseStream())
            $body = $reader.ReadToEnd()
            $reader.Close()
            Fail "API error ($($err.StatusCode.value__)): $body"
        } else {
            Fail "Request failed: $_"
        }
    }
}

Step 1 "Check prerequisites"

if ($Mode -ne "SmokeOnly") {
    if (-not $DocFolder -and -not $ChangedFilesPath) {
        Fail "Provide -DocFolder or -ChangedFilesPath in Apply/DryRun mode"
    }
    if ($DocFolder -and -not (Test-Path $DocFolder)) {
        Fail "DocFolder not found: $DocFolder"
    }
    $PROJECT_ROOT = Resolve-Path "$PSScriptRoot\..\.."
    $ASTRO_DOCS = Join-Path $PROJECT_ROOT "apps\ialab-docs\src\content\docs"
    if (Test-Path $ASTRO_DOCS) { Pass "Astro docs directory: $ASTRO_DOCS" }
    else { Warn "Astro docs directory not found" }
}

Step 2 "Connectivity"
$ping = Invoke-ALLM GET "/ping"
Info "API reachable"

Step 3 "Workspace verification"
$detail = Invoke-ALLM GET "/v1/workspace/$WorkspaceSlug"
$workspace = $detail.workspace
if ($workspace -is [array]) { $workspace = $workspace[0] }
$docCount = @($workspace.documents).Count
Pass "Workspace $WorkspaceSlug found with $docCount document(s)"

Step 4 "File collection"
if ($Mode -eq "SmokeOnly") {
    Pass "SmokeOnly mode - no files to collect"
    Step 5 "Smoke queries"
    $questions = @(
        @{ q = "Que hace el pipeline de Document Publishing Automation?" },
        @{ q = "Cuales son los pasos del Phase Closure Protocol?" }
    )
    $allOk = $true
    foreach ($item in $questions) {
        try {
            $body = @{ message = $item.q; mode = "chat" }
            $resp = Invoke-ALLM POST "/v1/workspace/$WorkspaceSlug/chat" $body
            $answer = $resp.textResponse
            if ($answer -and $answer.Length -gt 20) {
                Pass "Q: $($item.q)"
                Write-Host "    A: $($answer.Substring(0, [math]::Min(150, $answer.Length)))..." -ForegroundColor Gray
            } else {
                Warn "Short/empty response for: $($item.q)"
                $allOk = $false
            }
        } catch {
            Warn "Smoke failed: $($item.q)"
            $allOk = $false
        }
    }
    if ($allOk) { Pass "All smoke queries PASS" } else { Warn "Some smoke queries had issues" }
    Write-Host "--- Summary ---" -ForegroundColor Cyan
    Write-Host "PASS: $PASS  WARN: $WARN  FAIL: $FAIL" -ForegroundColor $(
        if ($FAIL -gt 0) { "Red" } elseif ($WARN -gt 0) { "Yellow" } else { "Green" }
    )
    exit 0
}

# Collect candidate files
$excludeDirs = @("node_modules", ".git", ".astro", "dist", "__pycache__", ".venv", "venv", "backups", ".obsidian")
$excludeExts = @(".pyc", ".log", ".db", ".sqlite", ".json", ".env", ".key", ".pem", ".crt", ".gguf")

$candidateFiles = @()
$targetDir = if ($DocFolder) { $DocFolder } else { Get-ItemProperty -Path $ChangedFilesPath | Select-Object -ExpandProperty DirectoryName }

if ($DocFolder) {
    Get-ChildItem -Path $DocFolder -Recurse -File | Where-Object {
        $inExcludedDir = $false
        foreach ($ed in $excludeDirs) {
            if ($_.FullName -match "\\$ed\\") { $inExcludedDir = $true; break }
        }
        if ($inExcludedDir) { return $false }

        $ext = $_.Extension.ToLower()
        foreach ($ee in $excludeExts) { if ($ext -eq $ee) { return $false } }

        if ($_.Length -gt ($MaxFileSizeKB * 1KB)) {
            if (-not $AllowLargeFiles) { return $false }
        }

        return $true
    } | Sort-Object Name -Unique | Select-Object -First $MaxFiles | ForEach-Object { $candidateFiles += $_ }
}

if ($ChangedFilesPath -and (Test-Path $ChangedFilesPath)) {
    Get-Content $ChangedFilesPath | ForEach-Object {
        if ($_ -and (Test-Path $_)) { $candidateFiles += Get-Item $_ }
    }
}

$candidateFiles = $candidateFiles | Sort-Object FullName -Unique
$fileCount = $candidateFiles.Count
Pass "Found $fileCount file(s) to process"

# DryRun summary
if ($Mode -eq "DryRun") {
    Step 5 "DryRun summary"
    Info "Mode: DryRun - no changes will be made"
    if ($fileCount -gt 0) {
        $batches = [math]::Ceiling($fileCount / $BatchSize)
        for ($b = 0; $b -lt $batches; $b++) {
            $start = $b * $BatchSize
            $end = [math]::Min($start + $BatchSize - 1, $fileCount - 1)
            $batchFiles = $candidateFiles[$start..$end]
            Info ("  Batch {0}/{1}: {2} file(s)" -f ($b + 1), $batches, $batchFiles.Count)
            foreach ($f in $batchFiles) {
                $rel = (Resolve-Path $f.FullName -Relative) -replace '^\.\\', ''
                $sk = [math]::Round($f.Length / 1024, 1)
                $fs = "    - $rel ($sk KB)"
                Info $fs
            }
        }
        $msg = "Would execute $batches update-embeddings call(s) with $BatchDelaySeconds s delay"
        Info $msg
    } else {
        Info "No files to upload. DryRun validated connectivity only."
    }
    Pass "DryRun completed. No changes made."
    exit 0
}

# Apply mode: upload + embed
Step 5 "Upload documents"

for ($b = 0; $b -lt $candidateFiles.Count; $b += $BatchSize) {
    $batchFiles = $candidateFiles[$b..([math]::Min($b + $BatchSize - 1, $candidateFiles.Count - 1))]
    $BatchesProcessed++
    $batchNum = $BatchesProcessed
    $totalBatches = [math]::Ceiling($candidateFiles.Count / $BatchSize)

    $msg = "Batch $batchNum / $totalBatches - $($batchFiles.Count) file(s)"
    Info $msg

    foreach ($f in $batchFiles) {
        try {
            $content = Get-Content -Path $f.FullName -Raw
            $body = @{
                textContent = $content
                metadata = @{
                    title = $f.Name
                    description = "Auto-uploaded by AI-LAB reindex pipeline"
                    sourceURL = "file:///$($f.FullName)"
                    docDate = (Get-Date -Format "yyyy-MM-dd")
                }
            }
            $upload = Invoke-ALLM POST "/v1/document/raw-text" $body
            if ($upload.success -and $upload.documents) {
                foreach ($d in $upload.documents) {
                    $script:UploadedLocations += @{ location = $d.id; title = $d.title }
                    $script:FilesUploaded++
                }
                $rel = (Resolve-Path $f.FullName -Relative) -replace '^\.\\', ''
                Pass "Uploaded: $rel"
            } else {
                Warn "Upload returned no documents for: $($f.Name)"
            }
        } catch {
            Warn "Upload failed: $($f.Name)"
        }
    }

    # Update embeddings per batch
    if ($UploadedLocations.Count -gt 0) {
        $embedBody = @{
            addOnly = $true
            documentLocations = @($UploadedLocations | Select-Object -ExpandProperty location)
        }
        try {
            $update = Invoke-ALLM POST "/v1/workspace/$WorkspaceSlug/update-embeddings" $embedBody
            $msg2 = "Batch {0}: added {1} document(s) to workspace" -f $batchNum, $UploadedLocations.Count
            Pass $msg2
        } catch {
            Warn "update-embeddings failed for batch $batchNum"
        }
    } else {
        Warn "No documents uploaded in batch $batchNum - skipping update-embeddings"
    }

    # Delay between batches
    if ($batchNum -lt $totalBatches) {
        Start-Sleep -Seconds $BatchDelaySeconds
    }
}

# Final workspace confirmation
$detail2 = Invoke-ALLM GET "/v1/workspace/$WorkspaceSlug"
$finalCount = @($detail2.workspace.documents).Count
$msg3 = "All batches complete: $BatchesProcessed batch(es), $FilesUploaded file(s) uploaded"
Pass $msg3
$msg4 = "Workspace $WorkspaceSlug now has $finalCount document(s)"
Info $msg4

Step 6 "Smoke queries"
$questions = @(
    @{ q = "Que hace el pipeline de Document Publishing Automation?" },
    @{ q = "Cuales son los pasos del Phase Closure Protocol?" }
)
$allOk = $true
foreach ($item in $questions) {
    try {
        $body = @{ message = $item.q; mode = "chat" }
        $resp = Invoke-ALLM POST "/v1/workspace/$WorkspaceSlug/chat" $body
        $answer = $resp.textResponse
        if ($answer -and $answer.Length -gt 20) {
            Pass "Q: $($item.q)"
            Write-Host "    A: $($answer.Substring(0, [math]::Min(150, $answer.Length)))..." -ForegroundColor Gray
        } else {
            Warn "Short/empty response for: $($item.q)"
            $allOk = $false
        }
    } catch {
        Warn "Smoke failed: $($item.q)"
        $allOk = $false
    }
}
if ($allOk) { Pass "All smoke queries PASS" } else { Warn "Some smoke queries had issues" }

Write-Host "--- Summary ---" -ForegroundColor Cyan
Write-Host "PASS: $PASS  WARN: $WARN  FAIL: $FAIL" -ForegroundColor $(if ($FAIL -gt 0) { "Red" } elseif ($WARN -gt 0) { "Yellow" } else { "Green" })
if ($FAIL -gt 0) { exit 1 } else { exit 0 }
