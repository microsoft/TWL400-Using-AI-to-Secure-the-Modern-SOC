# AGENTS.md

Guidance for AI coding agents (and any human author) working in this repository. This file is the **single source of truth** for the lab's scenario facts ("canon") and its MCAP authoring conventions. Read it before editing any page under `docs/`.

## Project overview

This repository is a **Jekyll-based training lab** (just-the-docs theme, published to GitHub Pages) in Microsoft's MCAP TechWorkshop format. It is the **Module 3 hands-on lab** — *Cross-Layer Attack Lab (End-to-End)* — of the L300/L400 workshop **Using AI to Secure the Modern SOC**.

Instructional content lives under `docs/`; image assets under `media/`. There is **no `src/` companion application** — this is a browser-only lab delivered in a pre-provisioned, hosted tenant (learners need only a browser and assigned credentials).

## Draft status — read this

This is a **full first draft authored from the lab outline before the lab tenant exists.** Portal navigation paths, KQL queries, Security Copilot prompts, screenshots, and every seeded entity below are **illustrative** and must be validated against the provisioned environment during the build (the JAM-208 hand-off). When the build resolves an open decision differently from this draft, update the canon here first, then the pages.

The recommended build (per the outline's Appendix A — the **Variant 4: Azure/Sentinel, No-Purview** design) is: **unified SecOps portal, Microsoft Sentinel as the data backbone (commodity signals + the ~25 decoy noise incidents injected via the Logs Ingestion API into a custom Log Analytics table, raised as incidents by Sentinel analytics rules), with the AI-layer (S3) signal detonated for real against an Azure OpenAI endpoint by a scripted `openai`-package call (PyRIT optional — dropped in validation for Python 3.13 / Windows path issues) and detected by Microsoft Defender for Cloud — AI threat protection.** Pages are written for that surface.

{: .warning }
> **Open decisions (flag in any affected page):**
> - **S4 form** — default is the **injected** service-principal infra/inference-reach (max determinism). An optional build alternative is OAuth illicit-consent + inbox rules (more realistic; would change the Ex03 infra-containment action). Pages stay on the injected default unless the build chooses otherwise.
> - **Runtime** — this draft targets the Variant-4 schedule (45-min core hunt + support, ~1h35m for Ex00–Ex04, Ex05 separate/post-delivery). Microsoft's 30–40 min ask may force later compression.

{: .important }
> **No Microsoft Purview.** This variant removes Purview entirely. Pages **must not** link to Purview Learn docs (`learn.microsoft.com/purview/...`, DSPM-for-AI, audit-solutions-overview, eDiscovery). Anchor the AI-data story to **Microsoft Defender for Cloud — AI threat protection** + the injected Stage-2 event + the planted grounding doc.

## Repo structure & taxonomy

| Path | Role |
| --- | --- |
| `_config.yml` | Jekyll config: theme (just-the-docs), `aux_links`, callouts, excludes. |
| `Gemfile` | Jekyll + just-the-docs dependencies. |
| `index.md` | Site landing page (`layout: home`, `nav_order: 1`) — intro, scenario, exercise list, prerequisites. Lives at repo root. |
| `docs/` | All instructional content (prose), organized as numbered exercises, each with numbered tasks. |
| `media/` | Image assets referenced by `docs/`, flat with an `NNMM_` prefix encoding exercise + task (e.g. `0102_incident_graph.png`). |
| `README.md`, `SECURITY.md`, `SUPPORT.md`, `LICENSE` | Standard Microsoft OSS repo files (excluded from the site). |
| `.github/workflows/jekyll-gh-pages.yml` | Builds and deploys the site to GitHub Pages on push to `main`. |

**Navigation is declarative** — driven entirely by front matter. Numbering is the spine: folder names, filenames, and `nav_order` share one ordinal scheme. There is no hand-maintained sidebar.

`nav_order` map: `index.md` = 1; exercise landings = 2 (Ex00) … 7 (Ex05); task pages = 1..N within their exercise.

## Page templates (MCAP)

### Landing — `index.md`
Front matter: `title`, `layout: home`, `nav_order: 1`. Body: H1; intro paragraph; `## Scenario`; `## What you'll do` (exercise table: #, exercise w/ link, duration); `## Prerequisites` (table); `## Lab environment`. A draft banner (`{: .important }`) up top.

### Exercise landing — `docs/NN_name/NN_name.md`
Front matter: `title: 'Exercise NN: <Title>'`, `layout: default`, `nav_order: N`, `has_children: true`. Body: H1 matching the title; `## Scenario`; `## Objectives` ("After completing this exercise, you'll be able to:" + bullets); `## Duration` (**Estimated time:** N minutes); `## Tasks` (a list linking each task page).

### Task page — `docs/NN_name/NN_MM.md`
Front matter: `title: 'M. <short title>'`, `layout: default`, `nav_order: M`, `parent: '<exact exercise landing title>'`. Body in this order:
- `# Task NN.MM — <Title>`
- `## Introduction` — why this task, where it sits in the story
- `## Description` — what the learner will do
- `## Success Criteria` — bullet checklist (fold the outline's Validation rows in here)
- `## Learning Resources` — Microsoft Learn links, each with `{:target="_blank"}`
- `## Key Tasks` — `### MM: <step>` headings; under each, a collapsible block of detailed steps:
  ```
  <details markdown="block">
  <summary><strong>Expand this section for detailed steps</strong></summary>

  1. Step…
  </details>
  ```
- `## Summary` — one short paragraph: what they accomplished + the artifact carried forward.

### Conventions
- **`parent:` must match the exercise landing `title:` byte-for-byte.** `nav_order` is unique within a parent.
- Callouts: `{: .note }`, `{: .tip }`, `{: .important }`, `{: .warning }`, `{: .caution }` on the line **before** a `>` blockquote.
- **Screenshot placeholders** (no real images exist yet): use a note callout, never a broken `![]()`:
  ```
  {: .note }
  > 📷 **Screenshot to capture:** <what the screenshot should show>
  ```
- Code in fenced blocks with a language hint (`kusto` for KQL, `powershell`, `text` for Copilot prompts/output).
- **Tag invented entities** the first time they appear on a page: e.g. _(illustrative — confirm at build)_.
- Surface unresolved outline decisions as `{: .warning }` build notes where they affect a step.
- Voice: second person, imperative, concise. Past/observed facts about the seeded incident are stated as fact (the tenant "shows" them).

## LAB CANON — single source of truth

Use these exact names and values on every page. Do not invent variants.

### Canonical (from the Zava case study — do not change)
- **Org:** Zava — large enterprise, 50–75 fragmented security tools, chronic alert fatigue, scaling AI to production under board/CIO/CAIO pressure. **~75 minutes** elapse from initial compromise to the attacker reaching high-value AI assets. Governing frameworks: OWASP LLM Top 10, NIST AI RMF, MITRE ATLAS, ISO/IEC 42001.
- **Learner role:** a security Cloud Solution Architect advising Zava's SOC.
- **Stakeholder personas** (the workshop cast; reference them in framing, especially Ex04/Ex05): **Vikram** (CISO), **Michelle** (CAIO), **Phillip** (Identity & SecOps Lead), **Nancy** (Data Security & Governance Lead), **Amy** (App/AI Security Lead), **Quinton** (Infrastructure & Architecture Lead).
- **AI application under attack:** the **Zava Refund Agent** — an internal, RAG-grounded generative-AI agent (a real **Azure OpenAI** endpoint, Azure AI Foundry project `refund-agent-prod`, `gpt-4o` deployment) that helps staff resolve customer refund cases. Stage 3 is a **real scripted detonation** against this endpoint, detected by Defender for Cloud — AI threat protection.
- **Microsoft products:** Microsoft Defender XDR (Defender for Identity, for Endpoint, for Office 365, for Cloud Apps), Microsoft Entra (ID Protection, Conditional Access), Microsoft Sentinel + Log Analytics, Microsoft Security Copilot, Azure OpenAI, **Microsoft Defender for Cloud — AI threat protection** (the AI-attack detection surface), Azure AI Content Safety / Prompt Shields.
  - **AI detection = Defender for Cloud _AI_, not Defender for Cloud _Apps_.** Defender for Cloud **AI threat protection** raises the native AI-attack alert on the Azure OpenAI endpoint. Defender for **Cloud Apps** is a separate, benign Defender XDR component in this scenario — never the AI-detection source. Keep them distinct on every page.
  - **No Microsoft Purview** — removed from this variant (see the draft-status note). The AI-data story is carried by Defender for Cloud AI + the injected Stage-2 event + the planted grounding doc, not DSPM for AI.
- **Module deliverable — "Proof Through Scenario":** an end-to-end attack visualization + a failure-point log + a business-impact summary, proving the current SOC missed the chain (buried in noise, uncorrelated) and the AI-driven SOC catches it. Feeds Module 4 (SOC operating model) and Module 5 (executive value).

### Invented for this lab (illustrative — confirm at build)
| Element | Value |
| --- | --- |
| Lab tenant | `zava.onmicrosoft.com` |
| Compromised user (Stage 1) | **Mariya Petrova**, Refund Operations Analyst — `mariya.petrova@zava.com`, Seattle |
| Endpoint (Stage 5) — **injected, synthetic asset** | **OPS-LT-0427** (Windows 11), a synthetic asset whose telemetry is **injected into Sentinel** (no real device, no facilitator-detonated endpoint); the encoded-PowerShell beacon `update_check.ps1` appears only as injected `SocLabEvents_CL` events |
| Service principal (Stage 4) | `sp-refund-agent-inference` |
| AI infra | Azure AI Foundry project `refund-agent-prod`, model deployment `gpt-4o`, resource group `rg-zava-ai-prod`, West US 3 |
| RAG grounding source | SharePoint site **"Refund Policy Knowledge Base"** (`/sites/RefundKB`) |
| Poisoned document (Stage 2) | **`Vendor-Refund-Policy-Update-Q3.docx`** — carries a hidden prompt-injection payload |
| Attacker infra | phishing sender `billing@zava-refunds[.]net` (look-alike domain); attacker sign-in IP `102.89.42.17` (Lagos, NG) |
| Unified incident title | **"Multi-stage incident involving Identity, AI, Data, Infrastructure, and Endpoint"** (stable substring for automation matching: **`Multi-stage incident involving Identity`**) |
| Sentinel automation/playbook | Logic App **`Zava-Contain-CrossLayer`** |
| KQL tables | **`SocLabEvents_CL`** (primary custom injection table — carries S1 identity, S2 email/poisoning, S4 infra lateral-movement, S5 endpoint commodity signals **plus the ~25 noise event-sets**); **`SecurityAlert` / `AlertEvidence`** (the real S3 Defender for Cloud — AI threat protection alert, via Advanced Hunting / the unified incident); native context tables `SigninLogs`, `AADUserRiskEvents`, `IdentityLogonEvents`, `EmailEvents`, `EmailUrlInfo`, `DeviceProcessEvents`, `DeviceNetworkEvents`; `AzureActivity` (corroborates S4); `CloudAppEvents` **(optional only** — an extra M365-Copilot AI-evidence pivot, never the primary AI source). **Dropped:** `RefundAgentPromptLogs_CL` and `AIInferenceAudit_CL` (their roles fold into `SocLabEvents_CL` for S4 and the Defender for Cloud AI alert for S3). |

### The seeded attack chain (Day 0, Pacific time — rebased so it appears just before the session)
| # | Time | Layer | Event | Surfaces in |
| --- | --- | --- | --- | --- |
| 1 — Initial access | 08:31 | Identity | AiTM phishing email to Mariya → she authenticates through the proxy → session token + credentials stolen → impossible-travel sign-in (Seattle → Lagos) | Entra ID Protection (risky sign-in, medium); injected via `SocLabEvents_CL` |
| 2 — Poisoning | 08:47 | Data / AI grounding | Using the stolen session, the attacker uploads `Vendor-Refund-Policy-Update-Q3.docx` into the Refund Policy Knowledge Base that grounds the Refund Agent | Injected `SocLabEvents_CL` event (the delivery email / poisoning); the doc is planted in the grounding store. **No Purview.** |
| 3 — Reasoning probe | 09:05–09:25 | AI | High-volume prompt-injection / jailbreak attempts against the **real Azure OpenAI** Refund Agent endpoint (scripted `openai`-package detonation; PyRIT optional) | **Microsoft Defender for Cloud — AI threat protection** raises a **real native alert** (queryable via `SecurityAlert` / `AlertEvidence`); Azure AI Content Safety Prompt Shields |
| 4 — Lateral movement | 09:38 | Infrastructure | `sp-refund-agent-inference` makes anomalous token/compute requests toward the GPU inference infra in `rg-zava-ai-prod` _(optional build alternative: OAuth illicit-consent + inbox rules)_ | Injected `SocLabEvents_CL`; corroborated by `AzureActivity` |
| 5 — Execution | 09:46 | Endpoint | `update_check.ps1` beacon on synthetic asset OPS-LT-0427 (encoded PowerShell, outbound beacon) | **Injected Sentinel telemetry** (`SocLabEvents_CL`) — synthetic asset, no real device |

**S3 framing (do not regress):** Defender for Cloud AI **does** raise a native alert for the AI attack. The AI layer's failure is **not** "no native detection / no signal / biggest blind spot." The failure is that the alert is **present but uncorrelated** into the cross-layer incident and **buried among the ~25 decoys**. Never write "no native detection," "never became an alert," "weakest native detection," or "largest blind spot (no signal)" for S3.

Each stage is individually low-severity and lands in a different console — the **signal-overload** problem. Only cross-layer correlation reveals the chain.

### The noise mechanic (the pedagogical core of this variant)
The tenant is seeded with **~25 real-looking decoy incidents** — routine risky sign-ins, benign DLP hits, commodity malware, failed-logon bursts, impossible-but-benign travel — with the five attack-chain signals **randomly interspersed among them**: each event's `TimeGenerated` is randomized across the lab window and the ordering is shuffled, so the chain is neither clumped nor obviously first/last. The **noise:signal ratio is a tunable seeder parameter** — high enough that Zava genuinely feels like it's "drowning in alerts" and the learner must hunt, but not so high that the chain can't be found inside the 45-minute core-hunt budget. The decoys and the chain are all injected into `SocLabEvents_CL` and raised as incidents by Sentinel analytics rules (the cross-layer correlation rule **plus the ~25 noise rules**). Surface this "drowning in alerts / cut the chain out of ~25 decoys" framing in Ex00 (orient to the noisy queue), Ex01 (triage = separate the chain from the decoys), and the Ex04 business-impact narrative.

### Entities to surface (Exercise 01 output)
Mariya Petrova (user) · `sp-refund-agent-inference` (service principal) · OPS-LT-0427 (synthetic endpoint) · `Vendor-Refund-Policy-Update-Q3.docx` (file) · Zava Refund Agent / `refund-agent-prod` (AI workload) · `102.89.42.17` (sign-in IP, Lagos) · `billing@zava-refunds[.]net` (sender) · Refund Policy Knowledge Base (grounding source).

### Coordinated response (Exercise 03) & autonomy boundary
- **Identity:** revoke Mariya's sessions + force reauthentication (Entra Conditional Access); disable and rotate `sp-refund-agent-inference`.
- **Data / AI:** quarantine `Vendor-Refund-Policy-Update-Q3.docx`; use **Defender for Cloud — AI threat protection** (the AI-attack alert + its `AlertEvidence`) together with the injected Stage-2 event to scope which Refund Agent activity touched the poisoned grounding. **No Purview / DSPM.**
- **Infrastructure:** isolate / restrict the affected inference deployment via the `Zava-Contain-CrossLayer` playbook _(optional build alternative: revoke the OAuth grant + remove inbox rules in the S4-OAuth option)_.
- **Autonomy boundary (illustrative):** auto (no human) = revoke session tokens, quarantine the doc, disable the suspicious service principal; human-approved = isolating production inference infrastructure / disabling the Refund Agent (business-impacting).

### Failure points & blind spots (Exercise 02 / Ex04)
Signals existed across every layer — including a **real Defender for Cloud — AI threat protection alert** for the AI attack — but were **uncorrelated** and **buried among the ~25 decoy incidents**. The AI-layer failure is **not** missing detection: the alert fired, but nothing tied the poisoned grounding source → Refund Agent behavior → identity/infra/endpoint activity into one incident, and it sat unnoticed in the noise. Business impact: 50–75 tools, alert fatigue, "drowning in alerts," ~75-minute attacker dwell to high-value assets, and a manual response too slow to contain at machine speed.

## Common commands

```bash
bundle install              # install Jekyll + just-the-docs (Ruby 3.x required)
bundle exec jekyll serve    # preview at http://localhost:4000
bundle exec jekyll build    # build the static site into _site/
```

A Ruby 3.x dev container is provided in `.devcontainer/` for local preview.
