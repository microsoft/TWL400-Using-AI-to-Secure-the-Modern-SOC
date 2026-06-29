// main.bicep - Module 3 SOC lab scaffolding (Part 1, before E5)
// Resource-group scoped.
//
// What this deploys:
//   - Log Analytics workspace (law-soclab) with Sentinel onboarded
//   - Azure OpenAI (oai-soclab) with Prompt Shield + model deployment
//   - Diagnostic settings on OpenAI → workspace (required for Defender for Cloud AI alerts)
//   - Storage account with grounding blob container
//
// What this does NOT deploy (handled by post-deploy scripts):
//   - SocLabEvents_CL table — created automatically by seed_events.py (HTTP Data Collector API)
//   - Analytics rules — created by add_entity_mappings.py and setup_noise_rules.py
//   - XDR cleanup app registration — created by setup_cleanup_app.py

// ── Model params (volatile — verify GA versions before deploying) ─────────────
// Run before deploying:
//   az cognitiveservices model list -l eastus \
//     --query "[?contains(model.name,'gpt-4o') && lifecycleStatus!='Deprecated'].{name:model.name,version:model.version,lifecycle:model.lifecycleStatus,sku:sku.name}" \
//     -o table
param location string = resourceGroup().location

// ── Suffix param — increment for each fresh build to avoid naming conflicts ───
// Format: v01, v02, v03 ...
// Avoids Sentinel workspace caching issues and soft-delete naming collisions.
// Use the same suffix for teardown purge commands (see Runbook_Update_Notes.md).
@description('Build suffix (e.g. v01, v02). Increment on each fresh deployment.')
param suffix string = 'v01'

@description('Azure OpenAI model name — must be GenerallyAvailable in your region')
param modelName string = 'gpt-4o'

@description('Azure OpenAI model version — must be GenerallyAvailable in your region')
param modelVersion string = '2024-11-20'

@description('Name of the deployment inside the OpenAI resource (used by seed_ai_attacks.py)')
param modelDeploymentName string = 'gpt4o'

var workspaceName = 'law-soclab-${suffix}'
var openAiName    = 'oai-soclab-${suffix}'

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: workspaceName
  location: location
  properties: { sku: { name: 'PerGB2018' }, retentionInDays: 30 }
}

resource sentinel 'Microsoft.SecurityInsights/onboardingStates@2024-03-01' = {
  scope: workspace
  name: 'default'
  properties: {}
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: toLower('stsoclab${uniqueString(resourceGroup().id)}')
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
}

resource blob 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storage
  name: 'default'
}

resource grounding 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blob
  name: 'grounding'
}

resource openai 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: openAiName
  location: location
  kind: 'OpenAI'
  sku: { name: 'S0' }
  properties: {
    customSubDomainName: openAiName
    publicNetworkAccess: 'Enabled'
  }
}

resource rai 'Microsoft.CognitiveServices/accounts/raiPolicies@2024-10-01' = {
  parent: openai
  name: 'promptshield'
  properties: {
    basePolicyName: 'Microsoft.Default'
    contentFilters: [
      { name: 'Jailbreak', source: 'Prompt', blocking: true, enabled: true }
    ]
  }
}

resource gpt 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openai
  name: modelDeploymentName
  sku: { name: 'Standard', capacity: 10 }
  properties: {
    model: { format: 'OpenAI', name: modelName, version: modelVersion }
    raiPolicyName: rai.name
  }
}

// ── Diagnostic settings: send OpenAI RequestResponse + Audit logs to Sentinel workspace ──
// Required for Defender for Cloud AI threat detection (jailbreak alerts).
// Without this, Defender for Cloud has no log stream to analyze and alerts will not fire.
resource oaiDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'oai-diagnostics'
  scope: openai
  properties: {
    workspaceId: workspace.id
    logs: [
      { category: 'RequestResponse', enabled: true }
      { category: 'Audit',           enabled: true }
    ]
    metrics: []
  }
}

output openAiEndpoint      string = openai.properties.endpoint
output workspaceResourceId string = workspace.id
