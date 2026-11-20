# ============================================================
# Claude Code + Amazon Bedrock — Team Setup (Windows)
# ============================================================
# This script:
#   1. Creates an AWS profile via ada (or isengardcli as fallback)
#   2. Sets Bedrock environment variables (user-level persistent)
#   3. Adds them to PowerShell profile for new sessions
#   4. Installs Claude Code if not already installed
#   5. Launches Claude Code
#
# Usage (run in PowerShell as Administrator):
#   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
#   .\setup-windows.ps1
#
# You will be prompted for your AWS account ID.
# ============================================================

$ErrorActionPreference = "Stop"

# ── Configuration ───────────────────────────────────────────
$ProfileName     = "claude-bedrock"
$AwsRegion       = "us-east-1"
$SonnetModel     = "us.anthropic.claude-sonnet-4-6"
$HaikuModel      = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
$OpusModel       = "us.anthropic.claude-opus-4-7"
# ─────────────────────────────────────────────────────────────

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Claude Code + Bedrock - Windows Setup"     -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ── Step 1: Check prerequisites ─────────────────────────────
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

# Node.js
try {
    $nodeVersion = (node -v) -replace 'v', ''
    $nodeMajor = [int]($nodeVersion.Split('.')[0])
    if ($nodeMajor -lt 18) {
        Write-Host "  Node.js 18+ required. Found: v$nodeVersion" -ForegroundColor Red
        exit 1
    }
    Write-Host "  Node.js v$nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "  Node.js not found. Install from https://nodejs.org/" -ForegroundColor Red
    exit 1
}

# Detect credential tool: prefer ada, fall back to isengardcli
$credTool = $null
try {
    $null = Get-Command ada -ErrorAction Stop
    $credTool = "ada"
    Write-Host "  ada found" -ForegroundColor Green
} catch {
    try {
        $null = Get-Command isengardcli -ErrorAction Stop
        $credTool = "isengardcli"
        Write-Host "  isengardcli found (legacy)" -ForegroundColor Green
    } catch {
        Write-Host "  Neither ada nor isengardcli found. Install one first:" -ForegroundColor Red
        Write-Host "    ada:          toolbox install ada" -ForegroundColor White
        Write-Host "    isengardcli:  toolbox install isengardcli  (legacy, may not be available)" -ForegroundColor White
        exit 1
    }
}

# AWS CLI
try {
    $null = Get-Command aws -ErrorAction Stop
    Write-Host "  AWS CLI found" -ForegroundColor Green
} catch {
    Write-Host "  AWS CLI not found. Install from https://aws.amazon.com/cli/" -ForegroundColor Red
    exit 1
}

# ── Step 2: Create AWS profile ───────────────────────────────
Write-Host ""
Write-Host "Setting up AWS profile '$ProfileName' via $credTool..." -ForegroundColor Yellow

function New-AwsProfile {
    param([string]$AccountId)
    if ($credTool -eq "ada") {
        ada profile add --account $AccountId --profile $ProfileName --provider isengard --region $AwsRegion
    } else {
        isengardcli add-profile $AccountId --profile $ProfileName --region $AwsRegion
    }
}

# Check if profile already exists
$profileExists = $false
try {
    $null = aws configure list --profile $ProfileName 2>$null
    if ($LASTEXITCODE -eq 0) { $profileExists = $true }
} catch {}

if ($profileExists) {
    Write-Host "  Profile '$ProfileName' already exists." -ForegroundColor DarkYellow
    $overwrite = Read-Host "  Overwrite it? (y/N)"
    if ($overwrite -eq 'y' -or $overwrite -eq 'Y') {
        $accountId = Read-Host "  Enter your AWS account ID"
        New-AwsProfile -AccountId $accountId
        Write-Host "  Profile '$ProfileName' created via $credTool" -ForegroundColor Green
    } else {
        Write-Host "  Keeping existing profile." -ForegroundColor DarkYellow
    }
} else {
    $accountId = Read-Host "  Enter your AWS account ID"
    New-AwsProfile -AccountId $accountId
    Write-Host "  Profile '$ProfileName' created via $credTool" -ForegroundColor Green
}

# Verify credentials
Write-Host ""
Write-Host "  Verifying credentials..." -ForegroundColor Gray
try {
    $identity = aws sts get-caller-identity --profile $ProfileName --output text --query 'Arn' 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Authenticated as: $identity" -ForegroundColor Green
    } else {
        throw "failed"
    }
} catch {
    Write-Host "  Could not verify credentials now. You may need to run:" -ForegroundColor DarkYellow
    if ($credTool -eq "ada") {
        Write-Host "    ada credentials update --account <account-id> --profile $ProfileName --role <your-role> --once" -ForegroundColor White
        Write-Host "    (Common roles: Admin, ReadOnly, or a custom role from your team)" -ForegroundColor Gray
    } else {
        Write-Host "    isengardcli credentials <account-id>" -ForegroundColor White
    }
    Write-Host "  Continuing with setup..." -ForegroundColor Gray
}

# ── Step 3: Set environment variables ────────────────────────
Write-Host ""
Write-Host "Setting environment variables..." -ForegroundColor Yellow

# Set persistent user-level environment variables
$envVars = @{
    "CLAUDE_CODE_USE_BEDROCK"        = "1"
    "AWS_PROFILE"                    = $ProfileName
    "AWS_REGION"                     = $AwsRegion
    "ANTHROPIC_DEFAULT_SONNET_MODEL" = $SonnetModel
    "ANTHROPIC_DEFAULT_HAIKU_MODEL"  = $HaikuModel
    "ANTHROPIC_DEFAULT_OPUS_MODEL"   = $OpusModel
}

foreach ($key in $envVars.Keys) {
    [System.Environment]::SetEnvironmentVariable($key, $envVars[$key], "User")
    # Also set in current session
    Set-Item -Path "Env:\$key" -Value $envVars[$key]
    Write-Host "  $key = $($envVars[$key])" -ForegroundColor Gray
}
Write-Host "  Persistent user-level env vars set" -ForegroundColor Green

# Add to PowerShell profile for new sessions
Write-Host ""
Write-Host "Adding to PowerShell profile..." -ForegroundColor Yellow

$psProfilePath = $PROFILE.CurrentUserAllHosts
$psProfileDir  = Split-Path $psProfilePath -Parent

if (-not (Test-Path $psProfileDir)) {
    New-Item -ItemType Directory -Path $psProfileDir -Force | Out-Null
}

$profileBlock = @"

# Claude Code + Amazon Bedrock (added by setup script)
`$env:CLAUDE_CODE_USE_BEDROCK = "1"
`$env:AWS_PROFILE = "$ProfileName"
`$env:AWS_REGION = "$AwsRegion"
`$env:ANTHROPIC_DEFAULT_SONNET_MODEL = "$SonnetModel"
`$env:ANTHROPIC_DEFAULT_HAIKU_MODEL = "$HaikuModel"
`$env:ANTHROPIC_DEFAULT_OPUS_MODEL = "$OpusModel"
"@

if (Test-Path $psProfilePath) {
    $existingContent = Get-Content $psProfilePath -Raw -ErrorAction SilentlyContinue
    if ($existingContent -and $existingContent.Contains("CLAUDE_CODE_USE_BEDROCK")) {
        Write-Host "  Already present in $psProfilePath - skipping" -ForegroundColor DarkYellow
    } else {
        Add-Content -Path $psProfilePath -Value $profileBlock
        Write-Host "  Added to $psProfilePath" -ForegroundColor Green
    }
} else {
    Set-Content -Path $psProfilePath -Value $profileBlock
    Write-Host "  Created $psProfilePath" -ForegroundColor Green
}

# ── Step 4: Install Claude Code ──────────────────────────────
Write-Host ""
Write-Host "Checking Claude Code installation..." -ForegroundColor Yellow

try {
    $null = Get-Command claude -ErrorAction Stop
    Write-Host "  Claude Code already installed" -ForegroundColor Green
} catch {
    Write-Host "  Installing Claude Code..." -ForegroundColor Gray
    npm install -g @anthropic-ai/claude-code
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  npm install failed. Try running this script as Administrator." -ForegroundColor Red
        exit 1
    }
    Write-Host "  Claude Code installed" -ForegroundColor Green
}

# ── Step 5: Launch ───────────────────────────────────────────
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Setup complete!"                            -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Profile:  $ProfileName (via $credTool)"
Write-Host "  Region:   $AwsRegion"
Write-Host "  Models:   Sonnet 4.6, Haiku 4.5, Opus 4.7"
Write-Host ""
Write-Host "  Launching Claude Code..." -ForegroundColor Green
Write-Host ""

claude
