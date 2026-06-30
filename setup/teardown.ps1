<#
.SYNOPSIS
    Tear down the TWL400 SOC Lab per-deployment resources.

.DESCRIPTION
    Runs RUNBOOK Teardown Steps 1-7. Pauses at steps that require manual portal
    action (Defender XDR disconnect, Security Copilot capacity, Defender for Cloud).

    Does NOT remove persistent tenant objects (Mariya Petrova, sp-refund-agent-inference,
    AI-Infrastructure-Owners) unless -Full is specified.

    Run from the setup\ directory with az CLI signed in.

.PARAMETER Full
    Also removes persistent tenant-level objects and re-enables Security Defaults.
    Only use for a complete tenant reset. You must re-run provision_lab_identities.ps1
    and the Tor sign-in before the next build.

.EXAMPLE
    .\teardown.ps1
    .\teardown.ps1 -Full
#>
param(
    [switch] $Full
)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

function Pause-ForPortal([string]$message) {
    Write-Host ""
    Write-Host "+---------------------------------------------------------+" -ForegroundColor Yellow
    Write-Host "|  MANUAL STEP REQUIRED                                   |" -ForegroundColor Yellow
    Write-Host "+---------------------------------------------------------+" -ForegroundColor Yellow
    Write-Host $message -ForegroundColor Cyan
    Write-Host ""
    Read-Host "Press Enter when done"
}

# ── Step 1: Disable all rules ─────────────────────────────────────────────────

Write-Host "Step 1 — Disabling all analytics rules..." -ForegroundColor Green
python "$PSScriptRoot\update_rule_frequency.py" --disable --all

# ── Step 2: Delete Sentinel incidents ─────────────────────────────────────────

Write-Host ""
Write-Host "Step 2 — Deleting Sentinel incidents..." -ForegroundColor Green
do {
    $output = (python "$PSScriptRoot\cleanup_incidents.py" 2>&1) -join "`n"
    Write-Host $output
} while ($output -notmatch "cleanup complete")

# ── Step 3: Resolve Defender XDR incidents ────────────────────────────────────

Write-Host ""
Write-Host "Step 3 — Resolving Defender XDR incidents..." -ForegroundColor Green
python "$PSScriptRoot\cleanup_xdr_incidents.py" --all

# ── Step 4a: Capture resource names before deletion ───────────────────────────

Write-Host ""
Write-Host "Step 4a — Capturing resource names before deleting resource group..." -ForegroundColor Green
$Location = az group show -n rg-soclab --query location -o tsv
$OaiName  = az cognitiveservices account list -g rg-soclab --query "[?kind=='OpenAI'] | [0].name" -o tsv
$WsName   = az monitor log-analytics workspace list -g rg-soclab --query "[0].name" -o tsv
Write-Host "  Location  : $Location"
Write-Host "  OpenAI    : $OaiName"
Write-Host "  Workspace : $WsName"
if (-not $Location -or -not $OaiName -or -not $WsName) {
    throw "Could not capture one or more resource names. Aborting to prevent data loss."
}

# ── Step 4b: Disconnect workspace from Defender XDR (manual) ─────────────────

Pause-ForPortal "STEP 4b — Disconnect workspace from Defender XDR

1. Go to https://security.microsoft.com/?tid=97cccd29-d389-4983-ac13-27a74d02cf2b
2. Settings > Microsoft Sentinel
3. Find '$WsName' > three-dot menu > Disconnect workspace > Confirm

If skipped, the deleted workspace persists as a stale Connected entry in Defender."

# ── Step 4c: Delete resource group ───────────────────────────────────────────

Write-Host ""
Write-Host "Step 4c — Deleting rg-soclab (background deletion, ~3-5 min)..." -ForegroundColor Green
az group delete -n rg-soclab --yes --no-wait
Write-Host "  Deletion running in background. Waiting 4 minutes..."
Start-Sleep -Seconds 240
Write-Host "  Check the Azure portal that rg-soclab is gone before continuing."
Read-Host "Press Enter when rg-soclab has disappeared from the portal"

# ── Step 4d: Purge soft-deleted OpenAI resource ───────────────────────────────

Write-Host ""
Write-Host "Step 4d — Purging soft-deleted OpenAI resource..." -ForegroundColor Green
az cognitiveservices account purge -l $Location -g rg-soclab -n $OaiName
Write-Host "  OpenAI purged."

# ── Step 4e: Permanently delete Log Analytics workspace ──────────────────────

Write-Host ""
Write-Host "Step 4e — Permanently deleting Log Analytics workspace..." -ForegroundColor Green
az monitor log-analytics workspace delete --resource-group rg-soclab --workspace-name $WsName --force
Write-Host "  Workspace permanently deleted."

# ── Step 5: Delete XDR cleanup app registration ───────────────────────────────

Write-Host ""
Write-Host "Step 5 — Deleting XDR cleanup app registration..." -ForegroundColor Green
$cleanupAppId = az ad app list --display-name "SOC Lab — XDR Cleanup" --query "[0].appId" -o tsv
if ($cleanupAppId) {
    az ad app delete --id $cleanupAppId
    Write-Host "  Deleted."
} else {
    Write-Host "  Not found (already deleted or never created)." -ForegroundColor DarkGray
}

# ── Step 6: Delete Security Copilot capacity (manual) ────────────────────────

Pause-ForPortal "STEP 6 — Delete Security Copilot capacity (delete CAPACITY only — NOT the workspace)

1. Go to https://securitycopilot.microsoft.com/?tid=97cccd29-d389-4983-ac13-27a74d02cf2b
2. Left nav > Owner settings > Azure resource links > Switch capacity > remove/delete scu-soclab

Do NOT delete the 'law-soclab' workspace — it is persistent across builds."

# ── Step 7: Disable Defender for Cloud AI workloads (manual) ─────────────────

Pause-ForPortal "STEP 7 — Disable Defender for Cloud AI workloads

1. Azure portal > Microsoft Defender for Cloud > Environment settings
2. Select subscription 'acesa-soc-development' > Defender plans
3. Toggle 'AI workloads' to Off > Save"

# ── Optional Step 0: Full tenant reset ───────────────────────────────────────

if ($Full) {
    Write-Host ""
    Write-Host "+---------------------------------------------------------+" -ForegroundColor Red
    Write-Host "|  FULL RESET — removing persistent tenant objects        |" -ForegroundColor Red
    Write-Host "+---------------------------------------------------------+" -ForegroundColor Red
    Write-Host "  After this you must re-run provision_lab_identities.ps1 + Tor sign-in before the next build." -ForegroundColor Yellow
    Read-Host "Press Enter to confirm, or Ctrl+C to abort"

    Pause-ForPortal "Step 0a — Dismiss Mariya Petrova's risk state before deleting her account

1. Azure portal > Microsoft Entra ID > Security > Identity Protection > Risky users
2. Find Mariya Petrova > three-dot menu > Dismiss user risk"

    Write-Host "  Deleting Mariya Petrova..."
    $mariyaId = az ad user show --id "mariya.petrova@AcesaDev.onmicrosoft.com" --query id -o tsv 2>$null
    if ($mariyaId) { az ad user delete --id $mariyaId; Write-Host "  Mariya Petrova deleted." }
    else { Write-Host "  Mariya Petrova not found (already deleted)." -ForegroundColor DarkGray }

    Write-Host "  Deleting AI-Infrastructure-Owners group..."
    $groupId = az ad group show --group "AI-Infrastructure-Owners" --query id -o tsv 2>$null
    if ($groupId) { az ad group delete --group $groupId; Write-Host "  AI-Infrastructure-Owners deleted." }
    else { Write-Host "  AI-Infrastructure-Owners not found." -ForegroundColor DarkGray }

    Write-Host "  Deleting sp-refund-agent-inference app registration..."
    $appId = az ad app list --display-name "sp-refund-agent-inference" --query "[0].appId" -o tsv 2>$null
    if ($appId) { az ad app delete --id $appId; Write-Host "  sp-refund-agent-inference deleted." }
    else { Write-Host "  sp-refund-agent-inference not found." -ForegroundColor DarkGray }

    Write-Host "  Re-enabling Security Defaults..."
    az rest --method PATCH --url "https://graph.microsoft.com/v1.0/policies/identitySecurityDefaultsEnforcementPolicy" --body '{"isEnabled": true}' --headers "Content-Type=application/json" | Out-Null
    Write-Host "  Security Defaults re-enabled."
    Write-Host ""
    Write-Host "  Full reset complete. Run provision_lab_identities.ps1 + Tor sign-in before the next build." -ForegroundColor Yellow
}

# ── Done ──────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "+=========================================================+" -ForegroundColor Green
Write-Host "|  TEARDOWN COMPLETE                                      |" -ForegroundColor Green
Write-Host "+=========================================================+" -ForegroundColor Green
Write-Host ""
Write-Host "  Verify: az group show -n rg-soclab   (expect: ResourceGroupNotFound)"
Write-Host "  Verify: Security Copilot capacity deleted"
