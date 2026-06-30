<#
.SYNOPSIS
    Re-seed the TWL400 SOC Lab — wipes incidents and seeds fresh events.

.DESCRIPTION
    Implements HOW_TO_RESEED.md as a single script. Re-uses existing Azure
    infrastructure — does not recreate any resources.

    Run from the setup\ directory with az CLI signed in.

.PARAMETER Domain
    Tenant domain, e.g. AcesaDev.onmicrosoft.com (auto-detected from az CLI if omitted)

.PARAMETER SeedAI
    Also runs seed_ai_attacks.py and plant_poisoned_doc.py after seeding events.
    Use when the Defender for Cloud jailbreak alert needs to be refreshed.

.PARAMETER DeployRule
    Re-runs add_entity_mappings.py before seeding. Use only if the cross-layer
    analytics rule definition changed since the last build.

.EXAMPLE
    .\reseed.ps1 -Domain AcesaDev.onmicrosoft.com
    .\reseed.ps1 -Domain AcesaDev.onmicrosoft.com -SeedAI
    .\reseed.ps1 -Domain AcesaDev.onmicrosoft.com -SeedAI -DeployRule
#>
param(
    [Parameter(Mandatory=$false)] [string] $Domain = "",
    [switch] $SeedAI,
    [switch] $DeployRule
)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

# ── Prerequisites check ───────────────────────────────────────────────────────

Write-Host "Checking prerequisites..." -ForegroundColor Green

$spAppId = az ad sp list --display-name "sp-refund-agent-inference" --query "[0].appId" -o tsv 2>$null
if ($spAppId) {
    $spEnabled = az ad sp show --id $spAppId --query "accountEnabled" -o tsv 2>$null
    if ($spEnabled -eq "false") {
        Write-Warning "sp-refund-agent-inference is disabled (may have been disabled during Ex03.01). Re-enable it before re-seeding."
        Write-Host "  Azure portal > Entra ID > Enterprise applications > sp-refund-agent-inference > Properties > Enabled = Yes"
        Read-Host "Press Enter when the SP is re-enabled"
    } else {
        Write-Host "  sp-refund-agent-inference: enabled. OK."
    }
} else {
    Write-Warning "sp-refund-agent-inference not found. Run provision_lab_identities.ps1 first."
}

# ── Step 1: Disable all rules ─────────────────────────────────────────────────

Write-Host ""
Write-Host "Step 1 — Disabling all analytics rules..." -ForegroundColor Green
python "$PSScriptRoot\update_rule_frequency.py" --disable --all

# ── Step 2: Re-deploy rule (optional) ────────────────────────────────────────

if ($DeployRule) {
    Write-Host ""
    Write-Host "Step 2 — Re-deploying cross-layer attack rule (add_entity_mappings.py)..." -ForegroundColor Green
    python "$PSScriptRoot\add_entity_mappings.py"
} else {
    Write-Host ""
    Write-Host "Step 2 — Skipping rule deploy (use -DeployRule only if the rule definition changed)." -ForegroundColor DarkGray
}

# ── Step 3: Wipe Sentinel incidents ───────────────────────────────────────────

Write-Host ""
Write-Host "Step 3 — Wiping Sentinel incidents..." -ForegroundColor Green
do {
    $output = (python "$PSScriptRoot\cleanup_incidents.py" 2>&1) -join "`n"
    Write-Host $output
} while ($output -notmatch "cleanup complete")

# ── Step 4: Seed fresh events ─────────────────────────────────────────────────

Write-Host ""
Write-Host "Step 4 — Seeding fresh events into SocLabEvents_CL..." -ForegroundColor Green
if ($Domain) {
    python "$PSScriptRoot\seed_events.py" --domain $Domain
} else {
    python "$PSScriptRoot\seed_events.py"
}

# ── Step 5: Enable rules + force PT5M ────────────────────────────────────────

Write-Host ""
Write-Host "Step 5 — Enabling rules and forcing PT5M fire cycle..." -ForegroundColor Green
python "$PSScriptRoot\update_rule_frequency.py" --enable --all
python "$PSScriptRoot\update_rule_frequency.py" PT5M --all
Write-Host "  Waiting 8 minutes for incidents to generate..."
Start-Sleep -Seconds 480

# ── Step 6: Verify + freeze ───────────────────────────────────────────────────

Write-Host ""
Write-Host "Step 6 — Verify incidents, then freeze the batch." -ForegroundColor Green
Write-Host "  Defender portal > https://security.microsoft.com/?tid=97cccd29-d389-4983-ac13-27a74d02cf2b"
Write-Host "  Incidents > Status = New + In Progress > expect ~26"
Read-Host "Press Enter when incidents are confirmed (or after waiting 2-3 more min if not all visible yet)"

python "$PSScriptRoot\update_rule_frequency.py" --disable --all
Write-Host "  Rules disabled — batch frozen."

# ── Optional: AI attacks ──────────────────────────────────────────────────────

if ($SeedAI) {
    Write-Host ""
    Write-Host "Seeding AI attacks (jailbreak prompts)..." -ForegroundColor Green
    python "$PSScriptRoot\seed_ai_attacks.py"
    Write-Host "Planting poisoned grounding document..." -ForegroundColor Green
    python "$PSScriptRoot\plant_poisoned_doc.py"
    Write-Host ""
    Write-Host "  Jailbreak alert will appear in Defender in 15-30 min." -ForegroundColor Cyan
    Write-Host "  Defender for Cloud AI workloads must be ON for the alert to fire."
}

Write-Host ""
Write-Host "Re-seed complete." -ForegroundColor Green
