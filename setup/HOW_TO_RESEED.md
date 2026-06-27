# How to Re-seed the SOC Lab

*For lab environment builders. Last updated: 2026-06-26.*

## How this works (read this first)

Three things are separate, and confusing them is the source of every "why won't the incidents go away" headache:

- **Events** live in the `SocLabEvents_CL` table. They **persist** — re-seeding adds more, and nothing deletes them (never purge the table). Think of them as **fuel**.
- **Analytics rules** are **generators**: while a rule is **enabled** and matching fuel sits in its lookback window, it manufactures an incident — repeatedly.
- **Incidents** are the **output** you see in Defender. `cleanup_incidents.py` deletes the output, but an enabled rule re-manufactures it instantly from the fuel.

So the rule to live by:

> **Incidents only stay gone while the rules are disabled.** Cleanup + rules **off** = clean and stays clean. Cleanup + rules **on** = they regenerate immediately, from whatever fuel is in the table.

A re-seed is therefore just: **turn the generators off → wipe the output → add fresh fuel → turn the generators on for one batch → turn them off to freeze it.** Never enable the rules except right after seeding.

(Accumulating fuel is harmless: the cross-layer rule counts *distinct* stages — still 5, so one incident — and grouping merges duplicate noise rows. That's why you never purge the table.)

## Prerequisites

- `az` CLI signed in, on the lab subscription (`acesa-soc-development`). Confirm: `az account show -o table`.
- Run every command from the setup folder (where the scripts live).
- Know your tenant domain (e.g. `AcesaDev.onmicrosoft.com`).
- **Identity objects exist.** Verify that `mariya.petrova@AcesaDev.onmicrosoft.com` and the `sp-refund-agent-inference` service principal are present in the tenant (portal.azure.com → Microsoft Entra ID → Users / App registrations). If either is missing, run `provision_lab_identities.ps1` (see RUNBOOK.md § TENANT HYDRATION) before continuing.
- **Mariya has an active `anonymousIpAddress` risk event.** Check: Entra ID Protection → Risky users → find Mariya Petrova → Risk state should not be **Remediated** or **Dismissed**. If her risk was cleared since the last lab run (e.g. a Global Admin dismissed it), re-trigger the detection by signing in as Mariya from Tor Browser before students reach Exercise 02.02. See RUNBOOK.md § H2–H3 for the exact procedure.

## Procedure

Run one step at a time.

**1. Turn the generators off.**
```
python update_rule_frequency.py --disable --all
```

**2. (Only if you changed a rule definition — KQL or entity mappings.) Deploy it.** It lands **disabled**, so it won't fire yet.
```
python add_entity_mappings.py
```

**3. Wipe the output.**
```
python cleanup_incidents.py
```
Re-run until "No more matching incidents — cleanup complete." With the rules off, the queue now *stays* empty.

**4. Add fresh fuel — SocLabEvents_CL.**
```
.\seed_events.ps1 -Domain AcesaDev.onmicrosoft.com
```
Expect `HTTP 200 -- all events posted OK` (30 events).

**5. Seed the AI jailbreak attack.**

> ⚠️ Prerequisite: Defender for Cloud AI workloads must be **On** before running this. Check: Azure portal → **Microsoft Defender for Cloud** → **Environment settings** → select the subscription → **Defender plans** → **AI workloads** = On. If it is off, the script succeeds but no alert is generated.

```
python seed_ai_attacks.py
```
Expected: `Responded: 2–3 | Blocked: 4–5 | Errors: 0`. The Defender for Cloud jailbreak alert appears as a **separate incident** within **15–30 minutes** — it is not part of the cross-layer attack incident.

> **Note on Responded/Blocked variance:** Several prompts land near Azure's content-filter threshold. The filter's ML models are non-deterministic and updated periodically, so the same prompt can flip between responded and blocked between runs. The ratio doesn't matter for the lab — Defender for Cloud sees the traffic and raises the alert regardless of whether individual prompts were blocked or answered.

**6. Plant the poisoned grounding document.**
```
python plant_poisoned_doc.py
```

**7. Turn the generators on and force one fast cycle.**
```
python update_rule_frequency.py --enable --all
```
```
python update_rule_frequency.py PT5M --all
```

**8. Wait ~5–10 minutes**, then verify in Defender (Incidents, Status = **New + In Progress**): ~26 incidents (≈25 noise + 1 cross-layer). The jailbreak alert arrives separately within 15–30 minutes of Step 5.

**9. Freeze the batch — turn the generators off.**
```
python update_rule_frequency.py --disable --all
```
This is the step that makes the batch stable. No frequency reset is needed — a disabled rule doesn't fire regardless of its PT5M/PT1H setting. **Do not skip it.**

## Notes

- **Do NOT purge `SocLabEvents_CL`.** Purging locks the table against ingestion for hours; accumulated events are harmless (see above).
- **Sentinel Logs opens in Simple mode** — switch to KQL mode for queries.
- **PowerShell:** one command per line; never use backtick line continuation.
