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

**4. Add fresh fuel.**
```
.\seed_events.ps1 -Domain AcesaDev.onmicrosoft.com
```
Expect `HTTP 200 -- all events posted OK` (30 events).

> Optional: `python seed_ai_attacks.py` and `python plant_poisoned_doc.py` to (re)generate the AI jailbreak alert + grounding doc (a separate incident, 15–30 min).

**5. Turn the generators on and force one fast cycle.**
```
python update_rule_frequency.py --enable --all
```
```
python update_rule_frequency.py PT5M --all
```

**6. Wait ~5–10 minutes**, then verify in Defender (Incidents, Status = **New + In Progress**): ~26 incidents (≈25 noise + 1 cross-layer), plus the jailbreak if you seeded it.

**7. Freeze the batch — turn the generators off.**
```
python update_rule_frequency.py --disable --all
```
This is the step that makes the batch stable. No frequency reset is needed — a disabled rule doesn't fire regardless of its PT5M/PT1H setting. **Do not skip it.**

## Notes

- **Do NOT purge `SocLabEvents_CL`.** Purging locks the table against ingestion for hours; accumulated events are harmless (see above).
- **Sentinel Logs opens in Simple mode** — switch to KQL mode for queries.
- **PowerShell:** one command per line; never use backtick line continuation.
