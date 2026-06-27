# TWL400 AI Enabled SOC Lab — Master Runbook
## Variant 4: Azure / Sentinel / Defender XDR / Security Copilot (no Purview)

*Last updated: 2026-06-26*
*All issues and fixes from prior sessions are incorporated here. This is the single source of truth.*

---

## TECHNICIAN PREREQUISITES

Install and verify all of the following on the setup technician's machine **before** beginning any build or hydration procedure.

### Required tools

**Azure CLI (`az`)**
Install: https://learn.microsoft.com/en-us/cli/azure/install-azure-cli
Verify: `az version`
Must be signed in and set to the lab subscription:
```powershell
az login
az account set --subscription 5c07e542-68ae-47ff-97cd-a6b3777b4fe1
az account show --query "{sub:id,tenant:tenantId}" -o table
```

**PowerShell 5.1 or later**
Ships with Windows 10/11. Verify: `$PSVersionTable.PSVersion`
Required for: `provision_lab_identities.ps1`, `seed_events.ps1`

**Microsoft Graph PowerShell modules**
```powershell
Install-Module Microsoft.Graph.Users, Microsoft.Graph.Groups, Microsoft.Graph.Applications, Microsoft.Graph.Identity.DirectoryManagement -Scope CurrentUser -Force
```
Note: the full `Microsoft.Graph` meta-module is not required and is much slower to install. Install only the four modules above.

**Python 3.8 or later**
Install: https://www.python.org/downloads/
Verify: `python --version`
All lab scripts use the standard library only — no `pip install` required.

**Git**
Install: https://git-scm.com/
Verify: `git --version`

### One-time tools (Tenant Hydration only)

**Tor Browser**
Required once to trigger the `anonymousIpAddress` risk detection for Mariya Petrova (TENANT HYDRATION § H2). Not needed for routine rebuilds unless her risk state was remediated.
Install: https://www.torproject.org/download/

### Required access

| What | Minimum role |
|------|-------------|
| Azure subscription `acesa-soc-development` | Owner or User Access Administrator |
| Entra ID tenant `AcesaDev.onmicrosoft.com` | Global Administrator (for tenant hydration); Security Administrator sufficient for routine rebuilds |
| Defender XDR portal | Security Administrator |
| Security Copilot | Security Administrator + Owner on the `law-soclab` workspace |

---

## Lab Environment Reference

| Item | Value |
|------|-------|
| Tenant | AcesaDev.onmicrosoft.com |
| Tenant ID | 97cccd29-d389-4983-ac13-27a74d02cf2b |
| Subscription | acesa-soc-development |
| Subscription ID | 5c07e542-68ae-47ff-97cd-a6b3777b4fe1 |
| Resource group | rg-soclab |
| Defender portal | https://security.microsoft.com/?tid=97cccd29-d389-4983-ac13-27a74d02cf2b |
| Security Copilot | https://securitycopilot.microsoft.com/?tid=97cccd29-d389-4983-ac13-27a74d02cf2b |
| Workspace name pattern | law-soclab-v## (e.g. law-soclab-v02) — never hardcode the suffix |
| SC workspace | law-soclab (persistent — survives teardowns, do NOT delete) |
| SC capacity | scu-soclab (recreated each rebuild) |

---

## Persistent vs. Per-Deployment Resources

These items are **tenant-level** and survive teardowns — do not delete them:
- Security Copilot workspace (`law-soclab`)
- Defender XDR tenant configuration
- Entra ID app registrations (unless explicitly listed in teardown)
- Entra ID user `mariya.petrova@AcesaDev.onmicrosoft.com` (Exercise 02 identity)
- Entra ID app registration + service principal `sp-refund-agent-inference` (Exercise 02 identity)
- Entra ID security group `AI-Infrastructure-Owners` (Exercise 02 sensitive group)

These items are **per-deployment** and are deleted/recreated each cycle:
- Resource group `rg-soclab` and everything in it
- Log Analytics workspace (`law-soclab-v##`)
- Azure OpenAI resource (`oai-soclab-v##`)
- Security Copilot capacity (`scu-soclab`)
- XDR cleanup app registration (`SOC Lab — XDR Cleanup`)

---

## TENANT HYDRATION (one-time — not repeated per rebuild)

These steps provision Entra ID objects that Defender for Identity needs to surface an identity timeline in Exercise 02, Task 02.02. They are **not per-deployment** — run once per tenant and skip on subsequent rebuilds unless the objects were deleted.

### H1 — Run the provisioning script

```powershell
.\provision_lab_identities.ps1
```

This script (idempotent — safe to re-run) creates:
- Disables Security Defaults (required for password-only Tor sign-in; this tenant has no CA policies)
- User `mariya.petrova@AcesaDev.onmicrosoft.com` with E5 license (Finance & Operations persona)
- App registration + service principal `sp-refund-agent-inference`
- Client secret for the SP (printed once to console — save it)
- Reader + Cognitive Services User roles on `rg-soclab` for the SP
- Security group `AI-Infrastructure-Owners` with the SP as a member
- 4 baseline ARM read calls under the SP's credentials (behavioral baseline for DFI)

**Required modules:** `Microsoft.Graph.Users`, `Microsoft.Graph.Groups`, `Microsoft.Graph.Applications`, `Microsoft.Graph.Identity.DirectoryManagement` (no Az module needed -- role assignments use az CLI)
**Required permissions:** Graph — `User.ReadWrite.All`, `Group.ReadWrite.All`, `Application.ReadWrite.All`, `Directory.ReadWrite.All`, `Policy.ReadWrite.ConditionalAccess`; Azure — Owner or User Access Administrator on subscription `acesa-soc-development`

### H2 — Trigger anonymousIpAddress risk detection (manual)

Entra ID Protection classifies sign-ins from Tor exit nodes as `anonymousIpAddress` risk events. This step cannot be automated.

1. Install Tor Browser: https://www.torproject.org/download/
2. Connect to the Tor network.
3. Navigate to: https://myapps.microsoft.com
4. Sign in as `mariya.petrova@AcesaDev.onmicrosoft.com` (password printed by script in H1).
5. Complete MFA if prompted. (If no MFA method is registered and CA blocks sign-in, register one via portal.azure.com → Users → mariya.petrova → Authentication methods first.)

Detection propagates in 5–15 minutes. If Tor exit node IPs are not yet flagged, retry with a second Tor sign-in.

### H3 — Confirm detection (manual)

1. Azure portal → Microsoft Entra ID → Security → **Identity Protection → Risky sign-ins**
2. Filter: User = `mariya.petrova`
3. Expected: risk event type = **Anonymous IP address**, level = Medium or High.
4. Optional: Entra ID Protection → **Risky users** → Mariya Petrova → **Confirm user compromised** (escalates to High; richer DFI timeline).

KQL verification (Log Analytics, allow ~24 h for full propagation):
```kql
AADUserRiskEvents
| where UserPrincipalName == "mariya.petrova@AcesaDev.onmicrosoft.com"
| where RiskEventType == "anonymousIpAddress"
| project TimeGenerated, RiskEventType, RiskLevel, IpAddress, Location
```

⚠️ Risk detections require an Entra ID P2 or E5 license on the user. The script assigns one; confirm under the user's Licenses blade if the detection does not appear.

---

## BUILD PROCEDURE

### PRE-DEPLOY — Data Gathering

Run before every deployment. Do not reuse values from a previous session.

**1. Confirm tenant and subscription:**
```powershell
az account show --query "{tenantId:tenantId, subscriptionId:id, name:name}" -o table
```
Expected: tenantId = `97cccd29-d389-4983-ac13-27a74d02cf2b`, subscriptionId = `5c07e542-68ae-47ff-97cd-a6b3777b4fe1`

If wrong: `az account set --subscription 5c07e542-68ae-47ff-97cd-a6b3777b4fe1`

**2. Choose deployment suffix:**

Pick the next available version number (e.g. `v02`, `v03`). This suffix is appended to all resource names.

**3. Find a deployable GPT model:**
```powershell
az cognitiveservices model list -l eastus --query "[?contains(model.name,'gpt-4o') && lifecycleStatus!='Deprecated'].{name:model.name, version:model.version, lifecycle:model.lifecycleStatus}" -o table
```
Pick the most recent non-Deprecated `gpt-4o` version. As of June 2026, `gpt-4o 2024-11-20` works.

⚠️ The list API lags enforcement — a model shown as "Deprecating" (not "Deprecated") will still deploy successfully.

---

### STEP 1 — Deploy Infrastructure

**1a. Create the resource group:**
```powershell
az group create -n rg-soclab -l eastus
```

**1b. Deploy Bicep:**
```powershell
az deployment group create -g rg-soclab -f main.bicep -p suffix=<suffix> modelName=gpt-4o modelVersion=2024-11-20 modelDeploymentName=gpt4o
```
Example: `suffix=v02`

⚠️ Allowed Bicep parameters: `location`, `modelDeploymentName`, `modelName`, `modelVersion`, `suffix`. There is no `deployerObjectId` parameter.

Wait for deployment to complete (~5 minutes).

**1c. Capture resource names (do not hardcode):**
```powershell
$SubId   = az account show --query id -o tsv
$WsName  = az monitor log-analytics workspace list -g rg-soclab --query "[0].name" -o tsv
$OaiName = az cognitiveservices account list -g rg-soclab --query "[?kind=='OpenAI'] | [0].name" -o tsv
Write-Host "Subscription: $SubId  |  Workspace: $WsName  |  OpenAI: $OaiName"
```

**1d. Post-deploy validation (all four must pass before continuing):**

Confirm model deployment:
```powershell
az cognitiveservices account deployment list -g rg-soclab -n $OaiName --query "[].{name:name, model:properties.model.name, version:properties.model.version, status:properties.provisioningState}" -o table
```
Expected: `gpt4o | gpt-4o | 2024-11-20 | Succeeded`

⚠️ Do NOT use the Azure portal to verify model deployments — it redirects to AI Foundry and forces project creation. Use the CLI above.

Confirm Sentinel onboarded:
```powershell
az rest --method get --url "https://management.azure.com/subscriptions/$SubId/resourceGroups/rg-soclab/providers/Microsoft.OperationalInsights/workspaces/$WsName/providers/Microsoft.SecurityInsights/onboardingStates/default?api-version=2024-03-01"
```
Expected: response with `"type": "Microsoft.SecurityInsights/onboardingStates"` and `"properties": {}`

Confirm storage grounding container:
```powershell
$StName = az storage account list -g rg-soclab --query "[0].name" -o tsv
az storage container list --account-name $StName --auth-mode login --query "[].name" -o tsv
```
Expected: `grounding`

Confirm workspace ID:
```powershell
az monitor log-analytics workspace show -g rg-soclab -n $WsName --query customerId -o tsv
```
Record this value for reference.

⚠️ The Bicep automatically configures diagnostic settings on the Azure OpenAI resource to send `RequestResponse` and `Audit` logs to the Sentinel workspace. This is required for Defender for Cloud AI threat detection (jailbreak alerts). No manual step needed.

⚠️ Wait 3–5 minutes after deployment before running post-deploy scripts. Sentinel's internal permissions take a few minutes to propagate. Running `add_entity_mappings.py` too soon returns `Unauthorized` — wait and retry.

**1e. Verify Defender XDR workspace connection:**

⚠️ Do this BEFORE running post-deploy scripts. Analytics rule API calls route to the Primary workspace — if it's wrong, `add_entity_mappings.py` and `setup_noise_rules.py` will target the wrong workspace.

1. Go to: `https://security.microsoft.com/?tid=97cccd29-d389-4983-ac13-27a74d02cf2b`
2. **Settings → Microsoft Sentinel**
3. Confirm `$WsName` (e.g. `law-soclab-v02`) is listed as **Connected** and **Primary**
4. If not Connected: click **Connect workspace** and select it
5. If Connected but not Primary: click three-dot menu → **Set as primary**
6. Disconnect any stale workspaces from prior builds

---

### STEP 2 — Run Post-Deploy Scripts

⚠️ **ORDERING IS CRITICAL. Follow exactly:**

**2a. Seed events FIRST — this creates the SocLabEvents_CL table:**
```
python seed_events.py --domain AcesaDev.onmicrosoft.com
```
Expected: `HTTP 200 | OK` — 30 events (5 attack + 25 noise) ingested.

⚠️ `SocLabEvents_CL` does not exist until events are seeded. Running `add_entity_mappings.py` or `setup_noise_rules.py` before seeding will fail with "One of the tables does not exist."

⚠️ **If you get `ERROR: No Log Analytics workspace found in rg-soclab`:**
The script queries `az monitor log-analytics workspace list -g rg-soclab` and found nothing. Diagnose in order:

1. Confirm you are in the correct subscription:
   ```powershell
   az account show --query "{tenantId:tenantId, subscriptionId:id, name:name}" -o table
   ```
   Expected: subscriptionId = `5c07e542-68ae-47ff-97cd-a6b3777b4fe1`. If wrong, run:
   ```powershell
   az account set --subscription 5c07e542-68ae-47ff-97cd-a6b3777b4fe1
   ```

2. Confirm the resource group exists and contains resources:
   ```powershell
   az resource list -g rg-soclab --query "[].{name:name, type:type}" -o table
   ```
   If the group is empty or missing, the Bicep deployment (Step 1b) did not complete. Go back and re-run Step 1b.

3. If the subscription is correct and resources are present, re-run Step 1c to capture `$WsName`, then retry `seed_events.py`.

**2b. Add entity mappings to the cross-layer attack rule:**
```
python add_entity_mappings.py
```
Applies the KQL query, MITRE tactics, entity mappings, and incident grouping to the "SOC Lab — cross-layer attack" analytics rule, and **deploys it disabled** (Step 5 enables it). The query emits **one row per attack stage** (1-Identity → 5-Endpoint, gated on ≥3 stages for the same account) and maps **5 entities** — Account×2 (user + service principal), Host (endpoint), AzureResource (AI resource), and MailMessage (phishing email), Sentinel's per-rule maximum. Incident grouping is **AnyAlert** — every firing of this rule collapses into a single incident — and there is **no suppression**. The result is one incident whose graph spans user, service principal, AI resource, endpoint, and email.

**2c. Create the 25 noise analytics rules:**
```
python setup_noise_rules.py
```
Creates 25 Sentinel analytics rules (one per noise event). Each fires when its matching event is in `SocLabEvents_CL` and generates a Defender-visible incident. Idempotent — safe to re-run.

**2d. Create the XDR cleanup app registration:**
```
python setup_cleanup_app.py
```
Creates the `SOC Lab — XDR Cleanup` app registration with `Incident.ReadWrite.All` on the Defender XDR API. Writes credentials to `.soclab_xdr_creds.json` (gitignored).

---

### STEP 3 — Set Up Security Copilot

Security Copilot has a persistent workspace (`law-soclab`) that survives teardowns. Each rebuild only requires creating new capacity and configuring the Sentinel plugin.

**3a. Create capacity:**
1. Go to: `https://securitycopilot.microsoft.com/?tid=97cccd29-d389-4983-ac13-27a74d02cf2b`
2. Upper right → **Workspaces** → **Manage workspaces**
3. On the `law-soclab` row, click **No capacity selected** → **Create a new capacity**
4. Fill in:
   - Capacity name: `scu-soclab`
   - Azure subscription: `acesa-soc-development`
   - Resource group: `rg-soclab`
   - Prompt evaluation location: United States
   - Capacity region: US East
   - SCUs: 1
5. Click **Create**

**3b. Verify capacity connected:**

Left nav → **Owner settings** → confirm:
- Capacity name: `scu-soclab`
- Subscription: `acesa-soc-development`
- Resource group: `rg-soclab`
- Security compute units: 1

**3c. Configure the Microsoft Sentinel plugin:**
1. In the Security Copilot prompt bar, click the **Sources/Plugins** button
2. Find **Microsoft Sentinel** → click the gear icon
3. Change **Configuration Level** from "User only" to **"Organization"** *(do this once — org-level settings apply to all users)*
4. Fill in:
   - Default workspace name: `law-soclab-v##` *(update this suffix each rebuild)*
   - Default subscription name: `acesa-soc-development`
   - Default resource group name: `rg-soclab`
5. Click **Save**
6. Click the **Security Copilot logo** (top left) to start a fresh session — the current session will not pick up the new settings

⚠️ The Sentinel plugin does NOT auto-detect the workspace. The workspace name must be updated after each rebuild with the new suffix. Without this step, Security Copilot returns empty responses to all Sentinel queries.

⚠️ After saving plugin settings, always start a fresh session from the home page before testing.

**Note on scripting:** The capacity resource (`Microsoft.SecurityCopilot/capacities`) is an ARM resource and is likely scriptable via `az rest`, but Microsoft has not published official CLI examples. The Sentinel plugin workspace settings have no documented public API — the portal is currently the only supported configuration path.

**3d. Verify Security Copilot — Sentinel connection:**

In a fresh session, run: `What incidents are in Sentinel?`

Expected: a table of incidents from the lab workspace.

---

### STEP 4 — Enable Defender for Cloud AI Workloads

⚠️ This must be done BEFORE running `seed_ai_attacks.py`. If it is off, the script will succeed but no jailbreak alert will be generated.

1. Azure portal → **Microsoft Defender for Cloud** → **Environment settings**
2. Select subscription `acesa-soc-development`
3. **Defender plans** → toggle **AI workloads** to **On** → **Save**

Confirm the toggle saved before proceeding.

---

### STEP 5 — Activate Incidents

**5a. Enable and force analytics rules to fire:**
```
python update_rule_frequency.py --enable --all
python update_rule_frequency.py PT5M --all
```
(The cross-layer rule deploys disabled, so `--enable --all` is required before it will fire.)

Wait 5–10 minutes for incidents to appear in the Defender portal.

**5b. Verify incidents in Defender:**

Go to: `https://security.microsoft.com/?tid=97cccd29-d389-4983-ac13-27a74d02cf2b`

Incidents queue → filter Status = **New + In Progress**

Expected: ~26 incidents (25 noise + 1 cross-layer attack).

**5c. Disable the rules:**
```
python update_rule_frequency.py --disable --all
```

⚠️ Disabling rules after incidents are created prevents duplicate incident generation on subsequent rule cycles. No need to reset the frequency first — a disabled rule doesn't fire regardless of its PT5M/PT1H setting. Rules must be re-enabled before any re-seed.

**To re-seed later (any time after initial setup):** follow the steps in **`HOW_TO_RESEED.md`** (in this same `setup/` folder). Note: `seed_ai_attacks.py` and `plant_poisoned_doc.py` are required steps in that procedure — not optional — and Defender for Cloud AI workloads must be **On** before running `seed_ai_attacks.py`.

---

### STEP 6 — Seed AI Attack + Plant Poisoned Doc

**6a. Run AI attack seeding:**
```
python seed_ai_attacks.py
```
Expected: `Responded: 2–3 | Blocked: 4–5 | Errors: 0` (ratio varies — Azure's content filter is non-deterministic and updated periodically; what matters is Errors: 0)

The Defender for Cloud jailbreak alert appears within **15–30 minutes** as a separate incident.

**6b. Plant the poisoned grounding document:**
```
python plant_poisoned_doc.py
```
Uploads `trusted-report.txt` to the `grounding` blob container. This simulates a poisoned document in the Azure OpenAI grounding data store.

---

### STEP 7 — Wait for Jailbreak Alert

The Defender for Cloud jailbreak alert takes 15–30 minutes after `seed_ai_attacks.py` to appear.

When it arrives, it shows as a separate incident: *"A Jailbreak attempt on your Azure AI model..."*

Verify in Defender portal → Incidents (Status = New + In Progress).

**Build is complete when:**
- ~26 noise + attack incidents visible in Defender
- Jailbreak alert incident visible
- Security Copilot returns Sentinel incidents
- All post-deploy validation checks passed

---

## TEARDOWN PROCEDURE

Run ONE STEP AT A TIME. Confirm each step before proceeding.

### Step 0 — Remove lab identity objects (optional — only if doing a full tenant reset)

⚠️ These objects are **persistent** (not per-deployment). Only remove them if you want a complete clean slate. Skip this step for routine rebuilds.

**Step 0a — Dismiss Mariya's risk state**

Before deleting the user, dismiss any open risk detections so they don't linger as orphaned entries.

1. Azure portal → Microsoft Entra ID → Security → Identity Protection → **Risky users**
2. Find Mariya Petrova → three-dot menu → **Dismiss user risk**

**Step 0b — Delete Mariya Petrova**
```powershell
Remove-MgUser -UserId (Get-MgUser -Filter "userPrincipalName eq 'mariya.petrova@AcesaDev.onmicrosoft.com'").Id
```
This soft-deletes the user. To permanently purge (frees the UPN immediately):
```powershell
Remove-MgDirectoryDeletedItemAsUser -DirectoryObjectId (Get-MgDirectoryDeletedItemAsUser | Where-Object { $_.UserPrincipalName -eq "mariya.petrova@AcesaDev.onmicrosoft.com" }).Id
```

**Step 0c — Delete the AI-Infrastructure-Owners group**
```powershell
Remove-MgGroup -GroupId (Get-MgGroup -Filter "displayName eq 'AI-Infrastructure-Owners'").Id
```

**Step 0d — Delete the sp-refund-agent-inference app registration (also removes SP)**
```powershell
Remove-MgApplication -ApplicationId (Get-MgApplication -Filter "displayName eq 'sp-refund-agent-inference'").Id
```
Deleting the app registration automatically soft-deletes the associated service principal and removes all role assignments. No separate SP deletion needed.

To purge the app registration from soft-delete (optional):
```powershell
Remove-MgDirectoryDeletedItemAsApplication -DirectoryObjectId (Get-MgDirectoryDeletedItem -DirectoryObjectId (Get-MgDirectoryDeletedItemAsApplication | Where-Object { $_.DisplayName -eq "sp-refund-agent-inference" }).Id)
```

**Step 0e — Re-enable Security Defaults**

`provision_lab_identities.ps1` disables Security Defaults to allow the password-only Tor sign-in. If you want to restore the tenant to its original posture after a full teardown, re-enable it:

```powershell
Invoke-MgGraphRequest -Method PATCH -Uri "https://graph.microsoft.com/v1.0/policies/identitySecurityDefaultsEnforcementPolicy" -Body '{"isEnabled": true}' -ContentType "application/json"
```

Confirm: `(Invoke-MgGraphRequest -Method GET -Uri "https://graph.microsoft.com/v1.0/policies/identitySecurityDefaultsEnforcementPolicy?`$select=isEnabled").isEnabled` — expected: `True`

⚠️ Re-enabling Security Defaults will block the Tor sign-in on the next hydration run. The provision script will detect and disable it again automatically (Part 0), so this step is safe to perform between cycles.

⚠️ After Step 0, re-run `provision_lab_identities.ps1` (Tenant Hydration § H1–H3) before the next lab build to re-create these objects and re-trigger the risk detection.

### Step 1 — Disable all analytics rules
```
python update_rule_frequency.py --disable --all
```
Ensure every rule is disabled before cleanup so nothing re-fires while you delete incidents. (`--disable` is idempotent — safe whether the rules were enabled or already off.)

⚠️ Always run this before cleanup. An enabled rule regenerates incidents faster than cleanup can delete them; disabling stops that entirely.

### Step 2 — Delete all Sentinel incidents
```
python cleanup_incidents.py
```
Run until output says "No more matching incidents — cleanup complete."

### Step 3 — Resolve all Defender XDR incidents
```
python cleanup_xdr_incidents.py --all
```
Resolves incidents and sets severity to Informational / determination to SecurityTesting.

⚠️ Defender XDR incidents cannot be deleted — only resolved. They remain visible in the portal under "All" filter. Use Status = New + In Progress filter to hide them.

### Step 4a — Capture variables BEFORE deleting the resource group
```powershell
$Location = az group show -n rg-soclab --query location -o tsv
$OaiName  = az cognitiveservices account list -g rg-soclab --query "[?kind=='OpenAI'] | [0].name" -o tsv
$WsName   = az monitor log-analytics workspace list -g rg-soclab --query "[0].name" -o tsv
Write-Host "Location: $Location  |  OpenAI: $OaiName  |  Workspace: $WsName"
```
Verify output looks correct before continuing. Once the group is deleted, these names cannot be recovered.

### Step 4b — Disconnect workspace from Defender XDR (portal)

Defender XDR workspace connections are tenant-level and survive resource group deletion. Disconnect before deleting.

1. Go to: `https://security.microsoft.com/?tid=97cccd29-d389-4983-ac13-27a74d02cf2b`
2. **Settings → Microsoft Sentinel**
3. Find the workspace matching `$WsName` → three-dot menu → **Disconnect workspace** → Confirm

⚠️ If you skip this step, the deleted workspace entry persists in Defender as a stale Connected workspace pointing at a gone resource.

### Step 4c — Delete the resource group
```powershell
az group delete -n rg-soclab --yes --no-wait
```
Runs in the background. Wait for `rg-soclab` to disappear from the Azure portal before proceeding (~3–5 minutes).

### Step 4d — Purge soft-deleted Azure OpenAI resource
```powershell
az cognitiveservices account purge -l $Location -g rg-soclab -n $OaiName
```
If this returns "still active", the resource group deletion isn't complete yet. Wait and retry.

No output = success.

### Step 4e — Permanently delete soft-deleted Log Analytics workspace
```powershell
az monitor log-analytics workspace delete --resource-group rg-soclab --workspace-name $WsName --force
```
Without this, the next deployment restores the old workspace (including stale analytics rules and table schemas).

No output = success.

### Step 5 — Delete the XDR cleanup app registration
```powershell
az ad app delete --id (az ad app list --display-name "SOC Lab — XDR Cleanup" --query "[0].appId" -o tsv)
```

### Step 6 — Delete Security Copilot capacity (portal)

⚠️ Delete the CAPACITY only. Do NOT delete the `law-soclab` workspace — it is persistent.

1. Go to: `https://securitycopilot.microsoft.com/?tid=97cccd29-d389-4983-ac13-27a74d02cf2b`
2. Left nav → **Owner settings**
3. Under **Azure resource links**, click **Switch capacity** → remove/delete `scu-soclab`

### Step 7 — Disable Defender for Cloud AI workloads (portal)

1. Azure portal → **Microsoft Defender for Cloud** → **Environment settings**
2. Select subscription `acesa-soc-development` → **Defender plans**
3. Toggle **AI workloads** to **Off** → **Save**

**Teardown is complete when:** `az group show -n rg-soclab` returns "not found" and Security Copilot capacity is deleted.

---

## KNOWN ISSUES & OPERATIONAL NOTES

**SocLabEvents_CL timestamp limitation**
The HTTP Data Collector API ignores the `time-generated-field` override. All seeded events land with `TimeGenerated` = ingestion time — no temporal spread across attack stages. The analytics rule and lab exercises function correctly despite this. Future fix: migrate to the DCR-based Logs Ingestion API.

**Do NOT purge SocLabEvents_CL**
Purging the table via the Log Analytics purge API locks it against new ingestion for hours to days. For cleanup, delete incidents only (`cleanup_incidents.py`) and re-seed. Old events in the table are harmless background noise.

**Cross-layer attack rule — entity-mapping cap (5)**
Sentinel scheduled rules allow a maximum of 5 entity mappings; a 6th returns `Invalid length of '6' for 'EntityMappings'`. The attack rule uses all five: Account×2 (user + `sp-refund-agent-inference`), Host (`OPS-LT-0427`), AzureResource (the AI resource), and MailMessage (the phishing email). The attacker IP is intentionally left unmapped (still present as a query column) to stay within the cap.

**Friendly synthetic AI-resource path**
The attack rule's AzureResource entity points at a friendly synthetic path — `.../resourceGroups/rg-zava-ai-prod/providers/Microsoft.CognitiveServices/accounts/refund-agent-prod` — so the graph node reads `refund-agent-prod` to match the lab story. It does NOT correspond to the real Azure OpenAI resource (`oai-soclab-v##` in `rg-soclab`); clicking the node opens a thin entity panel with no live resource. Intentional — do not repoint it to the real resource without re-checking the narrative.

**Empty "<No subject>" MailMessage node (cosmetic)**
The incident shows "2 Mail messages" — the real phishing email plus one empty entity created from the blank mail columns on the four non-email stage rows; neither currently shows its subject. Cosmetic only; a MailMessage-mapping refinement is tracked in the project backlog.

**Sentinel Logs defaults to Simple mode**
The Logs query interface opens in Simple mode. KQL queries will not work until the user switches to KQL mode.

**Defender for Cloud AI alerts take 15–30 minutes**
Expected. No action needed if the plan was enabled before `seed_ai_attacks.py` ran.

**Incidents filter**
Always set Status = **New + In Progress** in the Defender incidents queue. This hides all Resolved incidents from prior lab runs. Defender uses "New", "In Progress", and "Resolved" — there is no "Active" status.

**PowerShell line continuation**
Never use backtick (`` ` ``) line continuation in PowerShell commands. Always write commands as a single line.

---

## SCRIPTS REFERENCE

| Script | Purpose | When to run |
|--------|---------|-------------|
| `provision_lab_identities.ps1` | Creates Mariya Petrova (user + E5 license), `sp-refund-agent-inference` (app reg + SP + roles + group membership), baseline ARM calls; prints manual Tor sign-in instructions | **Once per tenant** (Tenant Hydration § H1). Re-run only if identity objects were deleted (Step 0 teardown). |
| `seed_events.py` | Seeds 5 attack + 25 noise events into `SocLabEvents_CL`, with typed entity columns (Sender/Recipient/Subject/NetworkMessageId, AzureResourceId, ServicePrincipal) on the attack stages; substitutes `{DOMAIN}` and `{SUBSCRIPTION}` at runtime | Every build, FIRST before other scripts |
| `seed_events.ps1` | Same as above, PowerShell | Every build |
| `add_entity_mappings.py` | Builds/patches the cross-layer attack rule: per-stage KQL, MITRE tactics, PT24H suppression, SingleAlert grouping, and 5 entity mappings (Account×2, Host, AzureResource, MailMessage) | Every build, after seed_events |
| `setup_noise_rules.py` | Creates 25 analytics rules (one per noise event) | Every build, after seed_events |
| `setup_cleanup_app.py` | Creates XDR cleanup app registration + credentials file | Every build |
| `seed_ai_attacks.py` | Sends jailbreak prompts to Azure OpenAI | Every build, after AI workloads enabled |
| `plant_poisoned_doc.py` | Uploads trusted-report.txt to grounding blob container | Every build |
| `update_rule_frequency.py` | Changes frequency or enables/disables analytics rules | PT5M to force fire; PT1H to reset; --disable after incidents created; --enable before re-seed |
| `cleanup_incidents.py` | Deletes all "SOC Lab —" Sentinel incidents | Teardown Step 2 |
| `cleanup_xdr_incidents.py` | Resolves all Defender XDR incidents | Teardown Step 3 |
| `save_to_github.py` | Commits and pushes all changes to GitHub | After any session with file changes |

---

## How to Re-seed the Lab

*(Also kept as the standalone `HOW_TO_RESEED.md`.)*

**The one thing to internalize:** `cleanup_incidents.py` deletes incidents, but **not** the events that feed them. Events persist in `SocLabEvents_CL` (fuel); analytics rules are generators that manufacture incidents whenever they're **enabled** and matching fuel is in their lookback window. So **incidents only stay gone while the rules are disabled** — cleanup + rules off = clean; cleanup + rules on = they regenerate instantly. A re-seed is just: **disable → wipe incidents → seed fresh → enable for one batch → disable to freeze.** Never enable except right after seeding. (Accumulating fuel is harmless — the cross-layer rule counts *distinct* stages, and grouping merges duplicate noise rows.)

Run one step at a time, from the setup folder, with `az` signed in:

```
python update_rule_frequency.py --disable --all      # 1. generators OFF
python add_entity_mappings.py                         # 2. ONLY if a rule definition changed (deploys disabled)
python cleanup_incidents.py                           # 3. wipe incidents (repeat until "cleanup complete")
.\seed_events.ps1 -Domain <tenant-domain>             # 4. fresh fuel (30 events)
python update_rule_frequency.py --enable --all        # 5. generators ON
python update_rule_frequency.py PT5M --all            #    force a fast cycle
                                                      # 6. wait ~5-10 min; verify ~26 incidents in Defender
python update_rule_frequency.py --disable --all       # 7. freeze the batch — do NOT skip
```

Optional after step 4: `python seed_ai_attacks.py` + `python plant_poisoned_doc.py` for the AI jailbreak alert (separate incident, 15–30 min). No frequency reset is needed at step 7 — a disabled rule doesn't fire regardless of PT5M/PT1H.

---

*Variant 4: Azure / Sentinel / Defender XDR / Security Copilot. Purview DSPM removed (retiring Sep 30, 2026).*
*Maintainer: Dan Beckett, Solliance/ideola*
