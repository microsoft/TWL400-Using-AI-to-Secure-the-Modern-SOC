<#
.SYNOPSIS
    Seeds SOC Lab attack-chain and noise events into SocLabEvents_CL.
    PowerShell equivalent of seed_events.py.

.PARAMETER Domain
    Tenant domain, e.g. AcesaDev.onmicrosoft.com

.PARAMETER HoursAgo
    How many hours ago the attack chain starts. Default: 2.

.PARAMETER DryRun
    Print events without posting.

.EXAMPLE
    .\seed_events.ps1 -Domain AcesaDev.onmicrosoft.com
    .\seed_events.ps1 -Domain AcesaDev.onmicrosoft.com -DryRun
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$Domain,
    [double]$HoursAgo = 2.0,
    [switch]$DryRun
)

$ResourceGroup = "rg-soclab"
$LogType       = "SocLabEvents"    # → SocLabEvents_CL in Log Analytics
$EventsFile    = Join-Path $PSScriptRoot "events.json"

function Get-WorkspaceName {
    $name = az monitor log-analytics workspace list -g $ResourceGroup --query "[0].name" --output tsv
    if (-not $name) {
        Write-Error "ERROR: No Log Analytics workspace found in $ResourceGroup."
        exit 1
    }
    return $name
}

function Get-WorkspaceCredentials {
    param([string]$WorkspaceName)

    $customerId = az monitor log-analytics workspace show --resource-group $ResourceGroup --workspace-name $WorkspaceName --query "customerId" --output tsv

    $sharedKey = az monitor log-analytics workspace get-shared-keys --resource-group $ResourceGroup --workspace-name $WorkspaceName --query "primarySharedKey" --output tsv

    return $customerId, $sharedKey
}

function Build-Signature {
    param($CustomerId, $SharedKey, $Date, $ContentLength)
    $stringToHash = "POST`n$ContentLength`napplication/json`nx-ms-date:$Date`n/api/logs"
    $bytesToHash  = [System.Text.Encoding]::UTF8.GetBytes($stringToHash)
    $keyBytes     = [System.Convert]::FromBase64String($SharedKey)
    $hmac         = New-Object System.Security.Cryptography.HMACSHA256
    $hmac.Key     = $keyBytes
    $signature    = [System.Convert]::ToBase64String($hmac.ComputeHash($bytesToHash))
    return "SharedKey ${CustomerId}:${signature}"
}

function Send-Events {
    param($CustomerId, $SharedKey, $Events, $BatchName)

    if ($DryRun) {
        Write-Host "  [dry-run] would POST $($Events.Count) event(s) for $BatchName"
        foreach ($e in $Events) {
            Write-Host "    [$($e.Stage)] $($e.Action) -- $($e.Account)  (T=$($e.TimeGenerated))"
        }
        return
    }

    $json    = $Events | ConvertTo-Json -Depth 5
    $body    = [System.Text.Encoding]::UTF8.GetBytes($json)
    $date    = [DateTime]::UtcNow.ToString("r")
    $auth    = Build-Signature -CustomerId $CustomerId -SharedKey $SharedKey -Date $date -ContentLength $body.Length

    $uri = "https://$CustomerId.ods.opinsights.azure.com/api/logs?api-version=2016-04-01"

    try {
        $response = Invoke-WebRequest -Uri $uri -Method POST -Body $body -ContentType "application/json" -UseBasicParsing -Headers @{ "Authorization" = $auth; "Log-Type" = $LogType; "x-ms-date" = $date; "time-generated-field" = "TimeGenerated" }
        Write-Host "  HTTP $($response.StatusCode) -- $BatchName posted OK"
    }
    catch {
        Write-Host "  ERROR posting ${BatchName}: $_"
    }
}

# Main

$WorkspaceName  = Get-WorkspaceName
$SubscriptionId = az account show --query id --output tsv

Write-Host "============================================================"
Write-Host "SOC Lab -- Event Seeding (PowerShell)"
Write-Host "Workspace    : $WorkspaceName"
Write-Host "Domain       : $Domain"
Write-Host "Attack start : $HoursAgo hours ago"
Write-Host "Mode         : $(if ($DryRun) { 'DRY RUN' } else { 'LIVE' })"
Write-Host "============================================================"

$raw         = Get-Content $EventsFile -Raw | ConvertFrom-Json
$attackStart = (Get-Date).ToUniversalTime().AddHours(-$HoursAgo)

$allEvents = @()
foreach ($item in $raw) {
    if (-not $item.Stage) { continue }
    $eventTime = $attackStart.AddMinutes($item.TimeOffsetMinutes)
    $account   = $item.Account -replace '\{DOMAIN\}', $Domain
    $allEvents += [PSCustomObject]@{
        TimeGenerated    = $eventTime.ToString("yyyy-MM-ddTHH:mm:ssZ")
        Stage            = $item.Stage
        Account          = $account
        Device           = $item.Device
        SourceIP         = $item.SourceIP
        Action           = $item.Action
        Severity         = $item.Severity
        Sender           = [string]$item.Sender
        Recipient        = ([string]$item.Recipient) -replace '\{DOMAIN\}', $Domain
        Subject          = [string]$item.Subject
        NetworkMessageId = [string]$item.NetworkMessageId
        AzureResourceId  = ([string]$item.AzureResourceId) -replace '\{SUBSCRIPTION\}', $SubscriptionId
        ServicePrincipal = [string]$item.ServicePrincipal
        Details          = $item.Details
    }
}

Write-Host ""
Write-Host "Loaded $($allEvents.Count) event(s) (attack stages interleaved with noise)."

if (-not $DryRun) {
    Write-Host ""
    Write-Host "Fetching workspace credentials..."
    $customerId, $sharedKey = Get-WorkspaceCredentials -WorkspaceName $WorkspaceName
    Write-Host "  Workspace ID : $customerId"
    Write-Host "  Shared key   : $('*' * 20)  (retrieved)"
} else {
    $customerId = $null
    $sharedKey  = $null
}

# Send all events in a single batch — preserves chronological interleaving