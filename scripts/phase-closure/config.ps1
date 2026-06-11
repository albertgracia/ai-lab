# AI-LAB Phase Closure — Shared Configuration
# Source this file from other scripts: . "$PSScriptRoot\config.ps1"

$script:PROJECT_ROOT = Resolve-Path "$PSScriptRoot\..\.."
$script:ASTRO_DIR = Join-Path $PROJECT_ROOT "apps\ialab-docs"
$script:ASTRO_CONTENT_DIR = Join-Path $ASTRO_DIR "src\content"
$script:SCRIPTS_DIR = Join-Path $PROJECT_ROOT "scripts"
$script:AUDITS_DIR = Join-Path $PROJECT_ROOT "docs\audits"

# SSH
$script:AILAB_SSH_HOST = "192.168.1.30"
$script:AILAB_SSH_USER = "albert"
$script:AILAB_REMOTE_REPO = "/opt/ai-lab"

# Public Astro (Cloudflare Pages)
$script:PUBLIC_ASTRO_URL = "https://ai-lab.labrazahome.com"

# Private Astro (local .30)
$script:PRIVATE_ASTRO_LOCAL_URL = "http://127.0.0.1:4322"

# AnythingLLM
$script:ANYTHINGLLM_BASE_URL = if ($env:ANYTHINGLLM_BASE_URL) { $env:ANYTHINGLLM_BASE_URL } else { "http://192.168.1.30:3001" }
$script:ANYTHINGLLM_WORKSPACE = if ($env:ANYTHINGLLM_WORKSPACE_SLUG) { $env:ANYTHINGLLM_WORKSPACE_SLUG } else { "ai-lab-core" }

# Timeouts
$script:CLOUDFLARE_DEPLOY_TIMEOUT_SECONDS = 300
$script:CLOUDFLARE_POLL_INTERVAL_SECONDS = 15
$script:SSH_TIMEOUT_SECONDS = 120
$script:ASTRO_BUILD_TIMEOUT_SECONDS = 120

# Validation URLs (public)
$script:VALIDATION_URLS_PUBLIC = @(
    "/blog/017-anythingllm-memoria-documental/",
    "/docs/architecture/anythingllm-role/",
    "/docs/governance/anythingllm-reindex-automation/",
    "/docs/governance/phase-closure-protocol/"
)

# Validation URLs (private, same paths)
$script:VALIDATION_URLS_PRIVATE = $script:VALIDATION_URLS_PUBLIC
