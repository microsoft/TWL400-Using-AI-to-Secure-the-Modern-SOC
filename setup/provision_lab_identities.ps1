# ==============================================================================
# provision_lab_identities.ps1
# TWL400 AI Enabled SOC Lab -- Entra ID Identity Provisioning
#
# PURPOSE
#   Creates the real Entra ID objects required by Exercise 02, Task 02.02.
#   Defender for Identity can only surface an identity timeline for objects
#   that actually exist in the tenant. These identities are referenced by
#   synthetic events in SocLabEvents_CL but must be real for DFI to work.
#
#   Objects created / configured:
#     Security Defaults  disabled (allows password-only sign-in for Tor step)
#     User               mariya.petrova@AcesaDev.onmicrosoft.com
#     App registration   sp-refund-agent-inference
#     Service principal  sp-refund-agent-inference (from above app reg)
#     Entra ID group     AI-Infrastructure-Owners
#
# IDEMPOTENT
#   Every block checks for existence before creating. Safe to re-run.
#
# REQUIRED PERMISSIONS
#   Microsoft Graph (delegated -- run interactively as a Global Admin or
#   a user with User Administrator, Application Administrator,
#   Groups Administrator, License Administrator roles):
#     User.ReadWrite.All
#     Group.ReadWrite.All
#     Application.ReadWrite.All
#     Directory.ReadWrite.All            (license assignment)
#     Policy.ReadWrite.ConditionalAccess (disable Security Defaults)
#
#   Azure RBAC (for SP role assignments on rg-soclab):
#     Owner or User Access Administrator on subscription acesa-soc-development
#
# REQUIRED MODULES
#   Install-Module Microsoft.Graph.Users, Microsoft.Graph.Groups, Microsoft.Graph.Applications, Microsoft.Graph.Identity.DirectoryManagement -Scope CurrentUser -Force
#
#   NOTE: Az PowerShell module is NOT required. Role assignments use az CLI,
#   which avoids the Azure.Identity.Broker version conflict in Az.Resources.
#   Prerequisite: az CLI signed in to subscription acesa-soc-development.
#   Verify: az account show --query "{sub:id}" -o tsv
#
# MANUAL STEPS
#   After running this script, two steps require human action:
#     1. Sign in as Mariya Petrova from Tor Browser (see end of script).
#     2. Confirm the anonymousIpAddress risk detection in the portal.
#   The script prints exact instructions when it completes.
#
# TENANT / ENVIRONMENT
#   Tenant ID       : 97cccd29-d389-4983-ac13-27a74d02cf2b
#   Tenant domain   : AcesaDev.onmicrosoft.com
#   Subscription ID : 5c07e542-68ae-47ff-97cd-a6b3777b4fe1
#   Resource group  : rg-soclab
# ==============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$TenantId       = "97cccd29-d389-4983-ac13-27a74d02cf2b"
$TenantDomain   = "AcesaDev.onmicrosoft.com"
$SubscriptionId = "5c07e542-68ae-47ff-97cd-a6b3777b4fe1"
$ResourceGroup  = "rg-soclab"

# ------------------------------------------------------------------------------
# CONNECT
# ------------------------------------------------------------------------------

Write-Host "`n[AUTH] Connecting to Microsoft Graph..." -ForegroundColor Cyan
Connect-MgGraph -TenantId $TenantId -Scopes "User.ReadWrite.All","Group.ReadWrite.All","Application.ReadWrite.All","Directory.ReadWrite.All","Policy.ReadWrite.ConditionalAccess" -NoWelcome

# Azure role assignments use az CLI (not Az PowerShell module) to avoid the
# Azure.Identity.Broker version conflict. Verify az is signed in to the right
# subscription before proceeding.
Write-Host "[AUTH] Verifying az CLI subscription..." -ForegroundColor Cyan
$AzAccount = az account show --query "{sub:id,tenant:tenantId}" -o json | ConvertFrom-Json
if ($AzAccount.sub -ne $SubscriptionId) {
    Write-Error "[AUTH] az CLI is on subscription '$($AzAccount.sub)'. Run: az account set --subscription $SubscriptionId"
}
Write-Host "[AUTH] az CLI subscription OK: $($AzAccount.sub)" -ForegroundColor Green

# ==============================================================================
# PART 0 -- DISABLE SECURITY DEFAULTS
# Security Defaults enforce MFA for all users, which would block the
# password-only Tor sign-in needed to trigger the anonymousIpAddress detection.
# This tenant has no Conditional Access policies, so disabling Security Defaults
# is the correct approach for this lab environment.
# ==============================================================================

Write-Host "`n[PART 0] Security Defaults" -ForegroundColor Yellow

$SecDefUri     = "https://graph.microsoft.com/v1.0/policies/identitySecurityDefaultsEnforcementPolicy"
$SecDefCurrent = (Invoke-MgGraphRequest -Method GET -Uri $SecDefUri).isEnabled

if ($SecDefCurrent -eq $false) {
    Write-Host "  [SKIP] Security Defaults already disabled."
} else {
    Write-Host "  [DISABLE] Disabling Security Defaults..."
    Invoke-MgGraphRequest -Method PATCH -Uri $SecDefUri -Body '{"isEnabled": false}' -ContentType "application/json"
    $SecDefVerify = (Invoke-MgGraphRequest -Method GET -Uri $SecDefUri).isEnabled
    if ($SecDefVerify -eq $false) {
        Write-Host "  [OK] Security Defaults disabled." -ForegroundColor Green
    } else {
        Write-Error "  [FAIL] Security Defaults still enabled after PATCH. Check permissions."
    }
}

# ==============================================================================
# PART 1 -- USER: MARIYA PETROVA
# ==============================================================================

Write-Host "`n[PART 1] Mariya Petrova" -ForegroundColor Yellow

$MariyaUPN = "mariya.petrova@$TenantDomain"

# --- 1a. Create user (idempotent) ---
$MariyaUser = Get-MgUser -Filter "userPrincipalName eq '$MariyaUPN'" -ErrorAction SilentlyContinue

if ($MariyaUser) {
    Write-Host "  [SKIP] User $MariyaUPN already exists (Id: $($MariyaUser.Id))"
} else {
    Write-Host "  [CREATE] Creating user $MariyaUPN..."

    # Generate a temporary password. Printed once -- not stored anywhere.
    # ForceChangePasswordNextSignIn is false so the Tor sign-in is not
    # interrupted by a password-change prompt.
    $TempPassword    = "SocLab-$(Get-Random -Minimum 10000 -Maximum 99999)!"
    $PasswordProfile = @{ Password = $TempPassword; ForceChangePasswordNextSignIn = $false }

    $UserParams = @{
        DisplayName       = "Mariya Petrova"
        UserPrincipalName = $MariyaUPN
        MailNickname      = "mariya.petrova"
        AccountEnabled    = $true
        PasswordProfile   = $PasswordProfile
        JobTitle          = "Financial Operations Analyst"
        Department        = "Finance & Operations"
        UsageLocation     = "US"
    }
    $MariyaUser = New-MgUser -BodyParameter $UserParams

    Write-Host "  [OK] Created $MariyaUPN (Id: $($MariyaUser.Id))" -ForegroundColor Green
    Write-Host ""
    Write-Host "  *** SAVE THIS PASSWORD -- printed once, never stored ***" -ForegroundColor Magenta
    Write-Host "  UPN      : $MariyaUPN" -ForegroundColor Magenta
    Write-Host "  Password : $TempPassword" -ForegroundColor Magenta
    Write-Host ""
}

$MariyaId = $MariyaUser.Id

# --- 1b. Assign E5 license (idempotent) ---
# Entra ID Protection risk detections require Entra ID P2 (included in E5).
# SKU is resolved dynamically -- do not hardcode the GUID.
Write-Host "  [LICENSE] Looking for Microsoft 365 E5 SKU..."

$E5Sku = Get-MgSubscribedSku | Where-Object { $_.SkuPartNumber -eq "SPE_E5" }

if (-not $E5Sku) {
    # Fallback: standalone Entra ID P2 also covers Identity Protection.
    $E5Sku = Get-MgSubscribedSku | Where-Object { $_.SkuPartNumber -eq "AAD_PREMIUM_P2" }
}

if (-not $E5Sku) {
    Write-Warning "  [WARN] No E5 or Entra ID P2 SKU found. Available SKUs:"
    Get-MgSubscribedSku | Select-Object SkuPartNumber, SkuId, ConsumedUnits | Format-Table
    Write-Warning "  Assign a license manually before the Tor sign-in step."
} else {
    Write-Host "  [LICENSE] Found SKU: $($E5Sku.SkuPartNumber) (Id: $($E5Sku.SkuId))"
    $AssignedLicenses = @(Get-MgUserLicenseDetail -UserId $MariyaId | Select-Object -ExpandProperty SkuId)
    if ($AssignedLicenses -contains $E5Sku.SkuId) {
        Write-Host "  [SKIP] License $($E5Sku.SkuPartNumber) already assigned to $MariyaUPN"
    } else {
        Write-Host "  [ASSIGN] Assigning $($E5Sku.SkuPartNumber) to $MariyaUPN..."
        $LicenseBody = @{ addLicenses = @(@{ skuId = $E5Sku.SkuId }); removeLicenses = @() } | ConvertTo-Json -Depth 3
        Invoke-MgGraphRequest -Method POST -Uri "https://graph.microsoft.com/v1.0/users/$MariyaId/assignLicense" -Body $LicenseBody -ContentType "application/json" | Out-Null
        Write-Host "  [OK] License assigned." -ForegroundColor Green
    }
}

# ==============================================================================
# PART 2 -- SERVICE PRINCIPAL: sp-refund-agent-inference
# ==============================================================================

Write-Host "`n[PART 2] Service principal: sp-refund-agent-inference" -ForegroundColor Yellow

$AppDisplayName = "sp-refund-agent-inference"

# --- 2a. Create app registration (idempotent) ---
$App = Get-MgApplication -Filter "displayName eq '$AppDisplayName'" -ErrorAction SilentlyContinue

if ($App) {
    Write-Host "  [SKIP] App registration '$AppDisplayName' already exists (AppId: $($App.AppId))"
} else {
    Write-Host "  [CREATE] Creating app registration '$AppDisplayName'..."
    $App = New-MgApplication -DisplayName $AppDisplayName -Notes "TWL400 SOC Lab -- Refund Agent inference workload. Created by provision_lab_identities.ps1."
    Write-Host "  [OK] App registration created (AppId: $($App.AppId), ObjectId: $($App.Id))" -ForegroundColor Green
}

$AppId       = $App.AppId
$AppObjectId = $App.Id

# --- 2b. Create service principal (idempotent) ---
$Sp = Get-MgServicePrincipal -Filter "appId eq '$AppId'" -ErrorAction SilentlyContinue

if ($Sp) {
    Write-Host "  [SKIP] Service principal for '$AppDisplayName' already exists (Id: $($Sp.Id))"
} else {
    Write-Host "  [CREATE] Creating service principal..."
    $Sp = New-MgServicePrincipal -AppId $AppId -Notes "TWL400 SOC Lab -- sp-refund-agent-inference"
    Write-Host "  [OK] Service principal created (Id: $($Sp.Id))" -ForegroundColor Green
}

$SpId = $Sp.Id

# --- 2c. Create a client secret ---
# Always creates a fresh secret (old secrets remain valid until expiry).
# Used below for baseline ARM calls and printed once for reference.
# Expires in 180 days -- sufficient for lab use.
Write-Host "  [SECRET] Creating client secret (180-day expiry)..."

$SecretExpiry = (Get-Date).AddDays(180).ToString("yyyy-MM-ddTHH:mm:ssZ")
$SecretParams = @{ PasswordCredential = @{ DisplayName = "lab-baseline-$(Get-Date -Format 'yyyyMMdd')"; EndDateTime = $SecretExpiry } }
$SecretResult = Add-MgApplicationPassword -ApplicationId $AppObjectId -BodyParameter $SecretParams
$ClientSecret = $SecretResult.SecretText

Write-Host ""
Write-Host "  *** SAVE THIS SECRET -- printed once, never stored ***" -ForegroundColor Magenta
Write-Host "  AppId        : $AppId" -ForegroundColor Magenta
Write-Host "  Client secret: $ClientSecret" -ForegroundColor Magenta
Write-Host "  Expires      : $SecretExpiry" -ForegroundColor Magenta
Write-Host ""

# --- 2d. Assign Reader role on rg-soclab (idempotent) ---
# Uses az CLI instead of Az PowerShell module to avoid the
# Azure.Identity.Broker version conflict that affects Az.Resources.
Write-Host "  [RBAC] Checking Reader role assignment on $ResourceGroup..."

$RoleScope     = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup"
$ExistingReader = az role assignment list --assignee $SpId --role "Reader" --scope $RoleScope --query "[0].id" -o tsv 2>$null

if ($ExistingReader) {
    Write-Host "  [SKIP] Reader role already assigned on $ResourceGroup"
} else {
    Write-Host "  [ASSIGN] Assigning Reader on $ResourceGroup to $AppDisplayName..."
    az role assignment create --assignee-object-id $SpId --assignee-principal-type ServicePrincipal --role "Reader" --scope $RoleScope | Out-Null
    Write-Host "  [OK] Reader role assigned." -ForegroundColor Green
}

# --- 2e. Assign Cognitive Services User on rg-soclab (idempotent) ---
# Represents "reaches toward AI/GPU infrastructure" for the lab narrative.
Write-Host "  [RBAC] Checking Cognitive Services User role assignment on $ResourceGroup..."

$ExistingCsUser = az role assignment list --assignee $SpId --role "Cognitive Services User" --scope $RoleScope --query "[0].id" -o tsv 2>$null

if ($ExistingCsUser) {
    Write-Host "  [SKIP] Cognitive Services User role already assigned on $ResourceGroup"
} else {
    Write-Host "  [ASSIGN] Assigning Cognitive Services User on $ResourceGroup to $AppDisplayName..."
    az role assignment create --assignee-object-id $SpId --assignee-principal-type ServicePrincipal --role "Cognitive Services User" --scope $RoleScope | Out-Null
    Write-Host "  [OK] Cognitive Services User role assigned." -ForegroundColor Green
}

# --- 2f. Create AI-Infrastructure-Owners group and add SP (idempotent) ---
# Security group flagged as sensitive so DFI can surface
# "Suspicious additions to sensitive groups" for Stage 4 corroboration.
Write-Host "  [GROUP] Checking AI-Infrastructure-Owners group..."

$GroupName    = "AI-Infrastructure-Owners"
$SensitiveGrp = Get-MgGroup -Filter "displayName eq '$GroupName'" -ErrorAction SilentlyContinue

if ($SensitiveGrp) {
    Write-Host "  [SKIP] Group '$GroupName' already exists (Id: $($SensitiveGrp.Id))"
} else {
    Write-Host "  [CREATE] Creating group '$GroupName'..."
    $GroupParams = @{
        DisplayName     = $GroupName
        MailNickname    = "ai-infrastructure-owners"
        SecurityEnabled = $true
        MailEnabled     = $false
        Description     = "Owners of AI inference infrastructure. Sensitive group -- monitored by Defender for Identity."
    }
    $SensitiveGrp = New-MgGroup -BodyParameter $GroupParams
    Write-Host "  [OK] Group created (Id: $($SensitiveGrp.Id))" -ForegroundColor Green
}

$GroupId = $SensitiveGrp.Id

$ExistingMember = Get-MgGroupMember -GroupId $GroupId | Where-Object { $_.Id -eq $SpId }
if ($ExistingMember) {
    Write-Host "  [SKIP] $AppDisplayName already a member of '$GroupName'"
} else {
    Write-Host "  [MEMBER] Adding $AppDisplayName to '$GroupName'..."
    New-MgGroupMember -GroupId $GroupId -DirectoryObjectId $SpId
    Write-Host "  [OK] Added." -ForegroundColor Green
}

# ==============================================================================
# PART 3 -- BASELINE ARM ACTIVITY FOR SP
# Acquires an access token using the SP's client credentials and makes a small
# number of read-only ARM calls. This gives Defender for Identity / Entra ID
# a behavioral baseline so that future anomalous calls stand out.
# ==============================================================================

Write-Host "`n[PART 3] Generating baseline ARM activity for $AppDisplayName..." -ForegroundColor Yellow

$TokenUri  = "https://login.microsoftonline.com/$TenantId/oauth2/v2.0/token"
$TokenBody = @{ client_id = $AppId; client_secret = $ClientSecret; scope = "https://management.azure.com/.default"; grant_type = "client_credentials" }

Write-Host "  [TOKEN] Acquiring ARM token for $AppDisplayName..."
$TokenResponse = Invoke-RestMethod -Method Post -Uri $TokenUri -Body $TokenBody -ContentType "application/x-www-form-urlencoded"
$ArmToken      = $TokenResponse.access_token
$ArmHeaders    = @{ Authorization = "Bearer $ArmToken" }
$ArmBase       = "https://management.azure.com"

Write-Host "  [OK] Token acquired."

Write-Host "  [ARM] Call 1/4: List resource groups..."
Invoke-RestMethod -Method Get -Uri "$ArmBase/subscriptions/$SubscriptionId/resourceGroups?api-version=2021-04-01" -Headers $ArmHeaders | Out-Null
Start-Sleep -Seconds 2

Write-Host "  [ARM] Call 2/4: List resources in $ResourceGroup..."
Invoke-RestMethod -Method Get -Uri "$ArmBase/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup/resources?api-version=2021-04-01" -Headers $ArmHeaders | Out-Null
Start-Sleep -Seconds 2

Write-Host "  [ARM] Call 3/4: List Cognitive Services accounts..."
Invoke-RestMethod -Method Get -Uri "$ArmBase/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.CognitiveServices/accounts?api-version=2023-05-01" -Headers $ArmHeaders | Out-Null
Start-Sleep -Seconds 2

Write-Host "  [ARM] Call 4/4: Get subscription details..."
Invoke-RestMethod -Method Get -Uri "$ArmBase/subscriptions/$($SubscriptionId)?api-version=2022-12-01" -Headers $ArmHeaders | Out-Null

Write-Host "  [OK] Baseline ARM activity recorded." -ForegroundColor Green

# ==============================================================================
# PART 4 -- SUMMARY AND MANUAL STEPS
# ==============================================================================

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " PROVISIONING COMPLETE -- MANUAL STEPS REQUIRED" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Objects provisioned:" -ForegroundColor White
Write-Host "  Security Defaults : disabled"
Write-Host "  User              : $MariyaUPN (Id: $MariyaId)"
Write-Host "  App reg           : $AppDisplayName (AppId: $AppId)"
Write-Host "  SP                : $AppDisplayName (Id: $SpId)"
Write-Host "  Group             : $GroupName (Id: $GroupId)"
Write-Host "  SP roles          : Reader + Cognitive Services User on $ResourceGroup"
Write-Host ""
Write-Host "------------------------------------------------------------" -ForegroundColor Yellow
Write-Host " MANUAL STEP 1 -- Trigger anonymousIpAddress risk detection" -ForegroundColor Yellow
Write-Host "------------------------------------------------------------" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Entra ID Protection classifies sign-ins from Tor exit nodes"
Write-Host "  as 'anonymousIpAddress' risk events. This step requires a"
Write-Host "  human to perform the sign-in -- it cannot be automated."
Write-Host ""
Write-Host "  Security Defaults are now disabled, so sign-in requires only"
Write-Host "  username and password -- no MFA prompt."
Write-Host ""
Write-Host "  Steps:"
Write-Host "    1. Install Tor Browser: https://www.torproject.org/download/"
Write-Host "    2. Launch Tor Browser and click Connect."
Write-Host "    3. Navigate to: https://myapps.microsoft.com"
Write-Host "    4. Sign in as: $MariyaUPN"
Write-Host "    5. Use the password printed above in Part 1."
Write-Host "    6. A successful sign-in from a Tor exit node triggers the detection."
Write-Host ""
Write-Host "  If sign-in fails with a block error (not an MFA prompt):"
Write-Host "    - Tor exit node may be flagged by Entra Smart Lockout."
Write-Host "    - Close Tor Browser, reopen, reconnect (gets a new exit node), retry."
Write-Host ""
Write-Host "------------------------------------------------------------" -ForegroundColor Yellow
Write-Host " MANUAL STEP 2 -- Confirm detection in Entra ID Protection" -ForegroundColor Yellow
Write-Host "------------------------------------------------------------" -ForegroundColor Yellow
Write-Host ""
Write-Host "  After the Tor sign-in (allow 5-15 minutes for propagation):"
Write-Host ""
Write-Host "  1. Azure portal -> Microsoft Entra ID -> Security -> Identity Protection"
Write-Host "     -> Risky sign-ins"
Write-Host "  2. Filter: User = mariya.petrova"
Write-Host "  3. Expected: risk event type = 'Anonymous IP address',"
Write-Host "     risk level = Medium or High."
Write-Host ""
Write-Host "  If the detection does not appear after 30 minutes:"
Write-Host "    - Verify the sign-in appears in Entra Sign-in logs."
Write-Host "    - Tor exit node IPs rotate; try a second sign-in from Tor."
Write-Host "    - Confirm Mariya has an Entra ID P2 or E5 license (assigned above)."
Write-Host ""
Write-Host "  KQL to verify (Log Analytics -- allow ~24h for full propagation):"
Write-Host "    AADUserRiskEvents"
Write-Host "    | where UserPrincipalName == '$MariyaUPN'"
Write-Host "    | where RiskEventType == 'anonymousIpAddress'"
Write-Host "    | project TimeGenerated, RiskEventType, RiskLevel, IpAddress, Location"
Write-Host ""
Write-Host "------------------------------------------------------------" -ForegroundColor Yellow
Write-Host " MANUAL STEP 3 -- Confirm compromised (optional but recommended)" -ForegroundColor Yellow
Write-Host "------------------------------------------------------------" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Entra ID Protection -> Risky users -> Mariya Petrova"
Write-Host "  -> three-dot menu -> 'Confirm user compromised'."
Write-Host "  Escalates risk state to High and makes the DFI timeline richer."
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " Setup complete. See RUNBOOK.md TENANT HYDRATION for context." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
