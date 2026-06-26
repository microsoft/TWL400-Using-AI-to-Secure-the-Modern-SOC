# TWL400 AI Enabled SOC Lab — Master Runbook
## Variant 4: Azure / Sentinel / Defender XDR / Security Copilot (no Purview)

*Last updated: 2026-06-26*
*All issues and fixes from prior sessions are incorporated here. This is the single source of truth.*

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

These items are **per-deployment** and are deleted/recreated each cycle:
- Resource group `rg-soclab` and everything in it
- Log Analytics workspace (`law-soclab-v##`)
- Azure OpenAI resource (`oai-soclab-v##`)
- Security Copilot capacity (`scu-soclab`)
- XDR cleanup app registration (`SOC Lab — XDR Cleanup`)

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
Applies the KQL query, MITRE tactics, suppression (PT24H), SingleAlert grouping, and entity mappings to the "SOC Lab — cross-layer attack" analytics rule. The query emits **one row per attack stage** (1-Identity → 5-Endpoint, gated on ≥3 stages for the same account) and maps **5 entities** — Account×2 (user + service principal), Host (endpoint), AzureResource (AI resource), and MailMessage (phishing email), which is Sentinel's per-rule maximum. These aggregate into one incident whose graph spans user, service principal, AI resource, endpoint, and email.

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

**5a. Force analytics rules to fire:**
```
python update_rule_frequency.py PT5M --all
```

Wait 5–10 minutes for incidents to appear in the Defender portal.

**5b. Verify incidents in Defender:**

Go to: `https://security.microsoft.com/?tid=97cccd29-d389-4983-ac13-27a74d02cf2b`

Incidents queue → filter Status = **New + In Progress**

Expected: ~26 incidents (25 noise + 1 cross-layer attack).

**5c. Reset rule frequency then disable:**
```
python update_rule_frequency.py PT1H --all
python update_rule_frequency.py --disable --all
```

⚠️ Disabling rules after incidents are created prevents duplicate incident generation on subsequent rule cycles. Rules must be re-enabled before any re-seed.

**Before re-seeding (any time after initial setup):**
```
python update_rule_frequency.py --enable --all
python update_rule_frequency.py PT5M --all
```
Wait for incidents, then:
```
python update_rule_frequency.py PT1H --all
python update_rule_frequency.py --disable --all
```

---

### STEP 6 — Seed AI Attack + Plant Poisoned Doc

**6a. Run AI attack seeding:**
```
python seed_ai_attacks.py
```
Expected: `Responded: 3 | Blocked: 4 | Errors: 0`

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

### Step 1 — Re-enable and slow all analytics rules
```
python update_rule_frequency.py --enable --all
python update_rule_frequency.py PT1H --all
```
Re-enable first in case rules were disabled during the build (Step 5c). Then slow to PT1H.

⚠️ Always run this before cleanup. Rules firing at PT5M regenerate incidents faster than cleanup can delete them.

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
Always set Status = **New + In Progress** in the Defender incidents queue. 