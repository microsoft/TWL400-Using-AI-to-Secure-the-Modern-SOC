# TWL400 Lab Build — Retrospective

**Project:** TWL400-Securing-AI (Using AI to Secure the Modern SOC — Module 3)
**Period:** Multiple sessions, ~2026-06-27 through present
**Lab type:** Jekyll/Just the Docs, Microsoft security stack (Sentinel, Defender, Security Copilot, Azure OpenAI)

---

## What we set out to do

Build and validate a hands-on security lab from a design outline. The lab teaches cross-layer incident investigation and AI-driven SOC response using live Microsoft tooling. It was authored ahead of the lab tenant being provisioned — which is the root cause of almost everything that needed fixing.

---

## Phase 1 — Environment setup and seeding

### What worked

**Incremental scripting with immediate validation.** Every script (`provision_lab_identities.ps1`, `seed_events.ps1`, `plant_poisoned_doc.py`, `add_entity_mappings.py`, `update_rule_frequency.py`, `cleanup_incidents.py`) was written, tested in the live tenant, and fixed in the same session. Idempotency was built into every script from the start — this saved hours across subsequent re-runs.

**Re-seed mental model.** The correct re-seed cycle was non-obvious. The key insight: events are fuel (they persist), analytics rules are the engine (generate incidents only while enabled), and `cleanup_incidents.py` clears output only. The order matters: disable → cleanup → seed → enable → PT5M → wait → disable. Documenting this explicitly in `HOW_TO_RESEED.md` meant it was never re-derived.

**Staging in Compose actions.** The Logic App (`Zava-Contain-CrossLayer`) needed Microsoft Graph permissions on a managed identity. PIM blocked this for 60+ minutes before we determined it was a dead end. Decision to stub Steps 1 and 2 as Compose actions and document the design choice transparently was the right call — it unblocked progress without compromising the learning objective.

### What didn't work

**Purging `SocLabEvents_CL`.** Attempting to purge the custom Log Analytics table locked it. Hard rule established: never purge — cleanup incidents only, re-seed rows instead. The async nature of Log Analytics purge operations makes it a trap.

**TimeGenerated timestamps.** The Data Collector API sets TimeGenerated at ingestion time, not at a lab-specified time. All five attack stages land at the same timestamp. The right fix (DCR-based Logs Ingestion API) was identified but deferred as out of scope. The lab documents this as a known limitation with a `{: .warning }` callout.

**Entra ID replication timing.** Provisioning Mariya Petrova and confirming her as a risky user required multiple sessions because Entra ID Protection propagation to the Risky Users blade was slow (60+ min in some cases). The lesson: provision identity objects at the start of a session, then do other work while they propagate.

**`impossibleTravel` → `anonymousIpAddress`.** The lab originally used impossible-travel as the Stage 1 detection type. Live tenant testing showed `anonymousIpAddress` is more reliably triggerable (Tor browser, one-time manual sign-in) and more accurate for an AiTM scenario. Required a 7-file find-replace across the lab. Lesson: validate detection type assumptions before writing lab copy.

---

## Phase 2 — Exercise-by-exercise validation

### The core discovery: design-outline fiction

The lab was authored from a design outline before the tenant was built. This produced two classes of problems:

1. **Hard fictions** — entity names, resource names, detection types, file names that simply didn't exist or were wrong. Examples: `Vendor-Refund-Policy-Update-Q3.docx` (actual: `trusted-report.docx`), `refund-agent-prod` Foundry project (actual: none — standalone Azure OpenAI resource), `impossibleTravel` (actual: `anonymousIpAddress`), Defender for Identity for SP anomalies (actual: Entra workload identity logs).

2. **Soft fictions** — plausible-sounding claims that were unverified or aspirational. Examples: "sub-5-minute scripted reset", "the decoy incidents are re-created by the seeder" (they're real native tenant noise), timing claims not grounded in benchmarking.

Both classes erode learner trust if not caught. Hard fictions break exercises. Soft fictions create instructor embarrassment at delivery.

### What worked

**Macro-then-micro validation order.** Reading each exercise file end-to-end before touching anything surfaced the structural fictions fast (wrong titles, wrong entity names, impossible cross-references). Micro-inspection (table-by-table, step-by-step) came after and caught the precise errors that macro reading missed.

**Entity canon.** Once we had a confirmed set of canonical entities from the live tenant (confirmed by querying `SocLabEvents_CL` and `SecurityAlert` via KQL and the ARM API), holding every doc to that canon was mechanical. The canon:
- User: `mariya.petrova@AcesaDev.onmicrosoft.com`
- Source IP (seeded): `102.89.42.17` (Tor exit node, synthetic)
- Grounding doc: `trusted-report.docx` in `grounding` container
- AI resource: `oai-soclab-v02` (Azure OpenAI, `gpt-4o` model, deployment `gpt4o`)
- Service principal: `sp-refund-agent-inference`
- Device: `OPS-LT-0427`
- Script: `update_check.ps1`
- Logic App: `Zava-Contain-CrossLayer`
- Workspace: `law-soclab-v02`

**Live querying via Chrome extension + ARM API.** The single most powerful validation technique. Instead of trusting what the docs said, we queried the live tenant directly:
- `SocLabEvents_CL` via Log Analytics REST API (POST `.../api/query`, `api-version=2020-08-01`)
- `SecurityAlert` via KQL in the Defender/Sentinel portal
- ARM deployments API to verify Azure OpenAI model deployment names
- Resource group listing to confirm what actually exists vs. what was claimed

This caught the `refund-agent-prod` fiction definitively in five seconds.

**Live prompt testing via Security Copilot in Chrome.** Every Security Copilot prompt was live-tested before being finalized. This caught four failure modes that couldn't have been found any other way:
- Incident ID references cause "Couldn't complete your request" errors
- Table format silently drops columns (the "Why it failed" column vanished)
- "AI governance" triggers the Microsoft Purview plugin, returning "Couldn't find that information"
- Mermaid graph generation runs for 2+ minutes with no reliable output

**Inline failsafe pattern.** After each prompt was tested and producing good output, a `{: .note }` callout with sample output was added immediately below the prompt. This gives learners a reference when Copilot's non-determinism or tenant misconfiguration produces unexpected results. It also serves as documentation of what "correct" looks like.

**Never committing until explicitly asked.** This sounds obvious but the discipline matters. Keeping a clean working-but-uncommitted state meant every fix could be reconsidered before it went into version history.

### What didn't work

**Trusting the draft callout.** The `{: .important }` "Draft" banner at the top of `index.md` was meant to flag that entities were illustrative. In practice it became invisible — we still had to find and fix every fiction manually. The callout is not a substitute for validation.

**Copilot Mermaid/graph generation.** Attempted to use Copilot's built-in graph generation to replace the Mermaid code block in `04_01.md`. After 2+ minutes with no output, we ruled it out. The Mermaid code block is the correct and only reliable option for in-lab diagram rendering.

**Assuming Defender for Identity covers service principal anomalies.** It doesn't, at least not in this tenant setup. Entra workload identity logs is the correct reference for SP token anomalies.

---

## Patterns that should be carried forward

### The validation workflow

```
1. MACRO PASS
   Read the full exercise/module end-to-end
   Note: structural issues, impossible cross-references, entity name suspects

2. ENTITY CANON ESTABLISHMENT
   Query live tenant to confirm every named entity
   Build a canon table — this is the ground truth for all subsequent checks

3. MICRO PASS — table/step/prompt inspection
   Each table cell, each step instruction, each technical claim
   Hold every item to the entity canon
   Flag: hard fictions (wrong), soft fictions (unverified/aspirational)

4. LIVE PROMPT TESTING (if applicable)
   Test every prompt in the actual target tool
   Document failures and their root causes
   Fix until pass, then capture sample output as inline failsafe

5. CROSS-DOCUMENT CONSISTENCY CHECK
   The same entity/claim appears in multiple files
   Verify consistency: stage names, layer names, offsets, entity names, counts

6. FIX — surgical, one file at a time
   Never fix adjacent issues that weren't asked about
   Never commit until the user says so

7. VERIFY — read the changed section back
   Confirm the fix didn't introduce new text inconsistencies
```

### The fiction taxonomy

| Type | Description | Example |
|------|-------------|---------|
| Entity fiction | Wrong resource/user/file name | `refund-agent-prod`, `Vendor-Refund-Policy-Update-Q3.docx` |
| Detection fiction | Wrong alert/detection type | `impossibleTravel` vs `anonymousIpAddress` |
| Tool attribution fiction | Wrong product for a capability | Defender for Identity for SP anomalies |
| Timing fiction | Specific unverified claim | "sub-5-minute reset" |
| Architecture fiction | Claimed resource doesn't exist | AI Foundry project when it's a standalone OpenAI resource |
| Seeder fiction | Claiming seeded data is real or vice versa | "decoy incidents are re-created by the seeder" |
| Stale instruction fiction | Instruction contradicts the actual state | "Replace `<INCIDENT_ID>`..." after removing the incident reference |

### Copilot prompt failure modes

| Failure mode | Symptom | Fix |
|---|---|---|
| Incident ID lookup | "Couldn't complete your request" | Remove incident reference; embed chain data directly |
| Table format | Silent column drop (4th+ columns) | Switch to numbered list with explicit labels |
| Plugin trigger word | "Couldn't find that information" | Remove the trigger word (e.g., "AI governance" → "AI asset exposure") |
| Graph/Mermaid generation | 2+ minute hang, no output | Don't use; keep Mermaid code block in docs |
| Non-determinism | Wording varies run-to-run | Add sample output `{: .note }` callout as inline failsafe |

### Chrome extension techniques

- **ARM token retrieval:** `sessionStorage` key matching `management.core.windows.net` target; use `JSON.parse(sessionStorage.getItem(key)).secret` for the Bearer token
- **Log Analytics REST API:** `POST https://management.azure.com/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.OperationalInsights/workspaces/{ws}/api/query?api-version=2020-08-01`
- **ARM resource listing:** `GET .../resourceGroups/{rg}/resources?api-version=2021-04-01` to confirm what exists
- **ARM deployments:** `GET .../providers/Microsoft.CognitiveServices/accounts/{name}/deployments?api-version=2023-05-01`
- **`document.body.innerText`** for reading portal page text after `await new Promise(r => setTimeout(r, 4000))`
- Security Copilot live testing: navigate to `securitycopilot.microsoft.com`, use `javascript_tool` to set the React textarea value and dispatch input events, then read the response

---

## Outstanding items (as of this retrospective)

- Ex 03 docs not fully validated in this project (Ex03.02 Logic App walkthrough still needed — see memory `project_ex0302_validation_reminder.md`)
- Ex 00 paused at Task 00.02 (walkthrough, not fiction scan)
- `trusted-report.docx` rename still needed in `03_01.md`, `03_02.md`, `03_03.md` (deferred from Ex02 review)
- TimeGenerated timestamp fix (DCR-based Logs Ingestion API) deferred
- Risky Users blade confirmation for Mariya Petrova (may need re-check)

---

## Key principle: canon before copy

Everything in the lab must trace to either:
1. A confirmed live-tenant observation, or
2. A deliberate narrative choice explicitly marked as illustrative (`{: .warning }`)

Anything else is a fiction — regardless of how plausible it sounds.
