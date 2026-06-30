<#
.SYNOPSIS
    Full TWL400 SOC Lab build — single script for all automated steps.

.DESCRIPTION
    Runs RUNBOOK Steps 1–7 in order. Pauses at the three steps that require
    manual portal action (XDR workspace connect, O365 API auth, Security Copilot
    capacity, Defender for Cloud AI plan). All other steps are automated.

    Run from the setup\ directory with az CLI signed in to the correct subscription.

.PARAMETER Suffix
    Build suffix, e.g. v02. Increment for each fresh deployment.

.PARAMETER Domain
    Tenant domain, e.g. AcesaDev.onmicrosoft.com

.PARAMETER ModelName
    Azure OpenAI model name (default: gpt-4o)

.PARAMETER ModelVersion
    Azure OpenAI model version (default: 2024-11-20)

.PARAMETER ModelDeploymentName
    Deployment name inside the OpenAI resource (default: gpt4o)

.EXAMPLE
    .\build.ps1 -Suffix v02 -Domain AcesaDev.onmicrosoft.com
#>
param(
    [Parameter(Mandatory=$true)]  [string] $Suffix,
    [Parameter(Mandatory=$true)]  [string] $Domain,
    [Parameter(Mandatory=$false)] [string] $ModelName           = 'gpt-4o',
    [Parameter(Mandatory=$false)] [string] $ModelVersion        = '2024-11-20',
    [Parameter(Mandatory=$false)] [string] $ModelDeploymentName = 'gpt4o'
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

function Write-Step([string]$label, [string]$msg) {
    Write-Host ""
    Write-Host "=== $label — $msg" -ForegroundColor Green
}

# ── PRE-DEPLOY: verify subscription ───────────────────────────────────────────

Write-Step "PRE" "Verify subscription"
$account = az account show --query "{sub:id,tenant:tenantId,name:name}" -o json | ConvertFrom-Json
Write-Host "  Subscription : $($account.name) ($($account.sub))"
Write-Host "  Tenant       : $($account.tenant)"
if ($account.sub -ne "5c07e542-68ae-47ff-97cd-a6b3777b4fe1") {
    Write-Warning "Unexpected subscription. Expected 5c07e542-68ae-47ff-97cd-a6b3777b4fe1."
    Read-Host "Run 'az account set --subscription 5c07e542-68ae-47ff-97cd-a6b3777b4fe1', then press Enter to continue, or Ctrl+C to abort"
}

# ── STEP 1a: Create resource group ────────────────────────────────────────────

Write-Step "1a" "Create resource group"
az group create -n rg-soclab -l eastus | Out-Null
Write-Host "  rg-soclab ready."

# ── STEP 1b: Deploy Bicep ─────────────────────────────────────────────────────

Write-Step "1b" "Deploy Bicep (main.bicep) — suffix=$Suffix"
az deployment group create -g rg-soclab -f "$PSScriptRoot\main.bicep" -p suffix=$Suffix modelName=$ModelName modelVersion=$ModelVersion modelDeploymentName=$ModelDeploymentName
Write-Host "  Bicep deployment complete."

# ── STEP 1c: Capture resource names ───────────────────────────────────────────

Write-Step "1c" "Capture resource names"
$WsName  = az monitor log-analytics workspace list -g rg-soclab --query "[0].name" -o tsv
$OaiName = az cognitiveservices account list -g rg-soclab --query "[?kind=='OpenAI'] | [0].name" -o tsv
$StName  = az storage account list -g rg-soclab --query "[0].name" -o tsv
$SubId   = az account show --query id -o tsv
Write-Host "  Workspace : $WsName"
Write-Host "  OpenAI    : $OaiName"
Write-Host "  Storage   : $StName"
if (-not $WsName -or -not $OaiName -or -not $StName) { throw "Failed to capture one or more resource names. Check Bicep deployment." }

# ── STEP 1d: Post-deploy validation ───────────────────────────────────────────

Write-Step "1d" "Post-deploy validation"
Write-Host "  Model deployment:"
az cognitiveservices account deployment list -g rg-soclab -n $OaiName --query "[].{name:name,model:properties.model.name,version:properties.model.version,status:properties.provisioningState}" -o table
Write-Host "  Sentinel onboarding:"
az rest --method get --url "https://management.azure.com/subscriptions/$SubId/resourceGroups/rg-soclab/providers/Microsoft.OperationalInsights/workspaces/$WsName/providers/Microsoft.SecurityInsights/onboardingStates/default?api-version=2024-03-01" | Out-Null
Write-Host "  Sentinel: OK"
Write-Host "  Grounding container:"
$containers = az storage container list --account-name $StName --auth-mode login --query "[].name" -o tsv
if ($containers -notmatch "grounding") { Write-Warning "grounding container not found — check Bicep deployment." }
else { Write-Host "  grounding: present" }

# ── STEP 1e: Connect workspace to Defender XDR (manual) ──────────────────────

Pause-ForPortal "STEP 1e — Connect workspace to Defender XDR

1. Open https://security.microsoft.com/?tid=97cccd29-d389-4983-ac13-27a74d02cf2b
2. Settings > Microsoft Sentinel
3. Confirm '$WsName' is Connected and Primary.
   - Not connected: click Connect workspace, select it.
   - Not Primary: three-dot menu > Set as primary.
4. Disconnect any stale workspaces from prior builds."

# ── STEP 1f-i: Deploy Logic App ───────────────────────────────────────────────

Write-Step "1f-i" "Waiting 3 min for Sentinel permissions to propagate"
Start-Sleep -Seconds 180

Write-Step "1f-i" "Deploy Zava-Contain-CrossLayer Logic App"
az deployment group create -g rg-soclab -n zava-contain-crosslayer -f "$PSScriptRoot\zava-contain-crosslayer.json" -p workspaceName=$WsName oaiResourceName=$OaiName
Write-Host "  Logic App deployed."

# ── STEP 1f-ii: Capture Logic App managed identity ────────────────────────────

Write-Step "1f-ii" "Capture Logic App managed identity"
$PrincipalId = az deployment group show -g rg-soclab -n zava-contain-crosslayer --query "properties.outputs.logicAppPrincipalId.value" -o tsv
if (-not $PrincipalId) { throw "Could not retrieve Logic App managed identity. Verify deployment outputs." }
Write-Host "  Logic App MI: $PrincipalId"

# ── STEP 1f-iii: Grant managed identity permissions ───────────────────────────

Write-Step "1f-iii" "Grant managed identity permissions"
$RgId = az group show -n rg-soclab --query id -o tsv
$WsId = az monitor log-analytics workspace show -g rg-soclab -n $WsName --query id -o tsv
$StId = az storage account show -n $StName -g rg-soclab --query id -o tsv

Write-Host "  Storage Blob Data Contributor on $StName..."
az role assignment create --assignee-object-id $PrincipalId --assignee-principal-type ServicePrincipal --role "Storage Blob Data Contributor" --scope $StId | Out-Null

Write-Host "  Contributor on rg-soclab..."
az role assignment create --assignee-object-id $PrincipalId --assignee-principal-type ServicePrincipal --role "Contributor" --scope $RgId | Out-Null

Write-Host "  Microsoft Sentinel Responder on $WsName..."
az role assignment create --assignee-object-id $PrincipalId --assignee-principal-type ServicePrincipal --role "Microsoft Sentinel Responder" --scope $WsId | Out-Null

Write-Host "  Enabling Sentinel workspace system-assigned managed identity..."
az monitor log-analytics workspace update -g rg-soclab -n $WsName --identity-type SystemAssigned | Out-Null
$SentinelPrincipalId = az monitor log-analytics workspace show -g rg-soclab -n $WsName --query identity.principalId -o tsv
if (-not $SentinelPrincipalId) { throw "Could not retrieve Sentinel workspace managed identity." }
Write-Host "  Sentinel workspace MI: $SentinelPrincipalId"

Write-Host "  Microsoft Sentinel Automation Contributor on rg-soclab (playbook selector)..."
az role assignment create --assignee-object-id $SentinelPrincipalId --assignee-principal-type ServicePrincipal --role "Microsoft Sentinel Automation Contributor" --scope $RgId | Out-Null

Write-Host "  Waiting 90 s for RBAC propagation..."
Start-Sleep -Seconds 90

# ── STEP 1f-iv: Authorize O365 API connection (manual) ───────────────────────

Pause-ForPortal "STEP 1f-iv — Authorize Office 365 API connection

1. Azure portal > rg-soclab > resource 'office365-zava' (type: API connection)
2. Click Edit API connection
3. Click Authorize > sign in with the Office 365 account that will send approval emails
4. Click Save

The account must have an Exchange Online mailbox in AcesaDev.onmicrosoft.com."

# ── STEP 1f-v: Verify playbook in Active Playbooks (manual) ──────────────────

Pause-ForPortal "STEP 1f-v — Verify Zava-Contain-CrossLayer in Sentinel Active Playbooks

1. Azure portal > Microsoft Sentinel > $WsName > Automation > Active playbooks
2. Confirm 'Zava-Contain-CrossLayer' is listed with Status = Enabled.
   If missing: wait 1-2 min and refresh."

# ── STEP 2a: Seed events ──────────────────────────────────────────────────────

Write-Step "2a" "Seed events (SocLabEvents_CL)"
python "$PSScriptRoot\seed_events.py" --domain $Domain
Write-Host "  Seed complete."

# ── STEP 2b: Add entity mappings ──────────────────────────────────────────────

Write-Step "2b" "Add entity mappings to cross-layer attack rule"
python "$PSScriptRoot\add_entity_mappings.py"

# ── STEP 2c: Create noise rules ───────────────────────────────────────────────

Write-Step "2c" "Create 25 noise analytics rules"
python "$PSScriptRoot\setup_noise_rules.py"

# ── STEP 2d: Create XDR cleanup app registration ─────────────────────────────

Write-Step "2d" "Create XDR cleanup app registration"
python "$PSScriptRoot\setup_cleanup_app.py"

# ── STEP 3: Security Copilot (manual) ─────────────────────────────────────────

Pause-ForPortal "STEP 3 — Set up Security Copilot

3a. Go to https://securitycopilot.microsoft.com/?tid=97cccd29-d389-4983-ac13-27a74d02cf2b
    Workspaces > Manage workspaces > law-soclab > No capacity selected > Create a new capacity:
      Name: scu-soclab | Subscription: acesa-soc-development | RG: rg-soclab
      Location: US East | SCUs: 1

3b. Owner settings > verify capacity = scu-soclab

3c. Sources/Plugins > Microsoft Sentinel > gear icon
    Config Level: Organization
    Workspace: $WsName | Subscription: acesa-soc-development | RG: rg-soclab
    Save > click Security Copilot logo (top left) to start a fresh session

3d. In the fresh session run: 'What incidents are in Sentinel?'
    Expected: a table of incidents."

# ── STEP 4: Enable Defender for Cloud AI workloads (manual) ──────────────────

Pause-ForPortal "STEP 4 — Enable Defender for Cloud AI workloads

1. Azure portal > Microsoft Defender for Cloud > Environment settings
2. Select subscription 'acesa-soc-development'
3. Defender plans > toggle 'AI workloads' to On > Save

This MUST be done before seed_ai_attacks.py runs."

# ── STEP 5: Activate incidents ────────────────────────────────────────────────

Write-Step "5a" "Enable analytics rules and force PT5M fire cycle"
python "$PSScriptRoot\update_rule_frequency.py" --enable --all
python "$PSScriptRoot\update_rule_frequency.py" PT5M --all
Write-Host "  Waiting 8 minutes for incidents to generate..."
Start-Sleep -Seconds 480

Pause-ForPortal "STEP 5b — Verify incidents in Defender portal

Go to https://security.microsoft.com/?tid=97cccd29-d389-4983-ac13-27a74d02cf2b
Incidents queue > filter Status = New + In Progress
Expected: ~26 incidents (25 noise + 1 cross-layer attack).
If fewer than expected, wait another 2-3 min and refresh."

Write-Step "5c" "Disable analytics rules (freeze the batch)"
python "$PSScriptRoot\update_rule_frequency.py" --disable --all

# ── STEP 6: AI attack + poisoned doc ──────────────────────────────────────────

Write-Step "6a" "Seed AI attacks (jailbreak prompts > Defender for Cloud alert)"
python "$PSScriptRoot\seed_ai_attacks.py"

Write-Step "6b" "Plant poisoned grounding document"
python "$PSScriptRoot\plant_poisoned_doc.py"

# ── STEP 7: Done ──────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "+=========================================================+" -ForegroundColor Green
Write-Host "|  BUILD COMPLETE                                         |" -ForegroundColor Green
Write-Host "+=========================================================+" -ForegroundColor Green
Write-Host ""
Write-Host "  Workspace : $WsName"
Write-Host "  OpenAI    : $OaiName"
Write-Host "  Storage   : $StName"
Write-Host ""
Write-Host "  The Defender for Cloud jailbreak alert takes 15-30 min to appear."
Write-Host "  Check: Defender portal > Incidents > Status = New + In Progress"
Write-Host "  Expected: 'A Jailbreak attempt on your Azure AI model...'"
Write-Host ""
Write-Host "  Build is complete when all three are true:"
Write-Host "    [ ] ~26 incidents visible (25 noise + 1 cross-layer)"
Write-Host "    [ ] Jailbreak alert incident visible"
Write-Host "    [ ] Security Copilot returns Sentinel incidents"
