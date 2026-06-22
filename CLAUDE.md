# CLAUDE.md

Guidance for Claude Code (and any author) working in this repository. This file is the **single source of truth** for the lab's scenario facts ("canon") and its MCAP authoring conventions. Read it before editing any page under `docs/`.

## Project overview

This repository is a **Jekyll-based training lab** (just-the-docs theme, published to GitHub Pages) in Microsoft's MCAP TechWorkshop format. It is the **Module 3 hands-on lab** — *Cross-Layer Attack Lab (End-to-End)* — of the L300/L400 workshop **Using AI to Secure the Modern SOC**.

Instructional content lives under `docs/`; image assets under `media/`. There is **no `src/` companion application** — this is a browser-only lab delivered in a pre-provisioned, hosted tenant (learners need only a browser and assigned credentials).

## Draft status — read this

This is a **full first draft authored from the lab outline before the lab tenant exists.** Portal navigation paths, KQL queries, Security Copilot prompts, screenshots, and every seeded entity below are **illustrative** and must be validated against the provisioned environment during the build (the JAM-208 hand-off). When the build resolves an open decision differently from this draft, update the canon here first, then the pages.

The recommended build (per the outline's Appendix A) is: **unified SecOps portal, Microsoft Sentinel as the data backbone (replay/injection of commodity signals), with the AI-layer signals detonated live using PyRIT.** Pages are written for that surface.

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

### Canonical (from the Acesa case study — do not change)
- **Org:** Acesa — large enterprise, 50–75 fragmented security tools, chronic alert fatigue, scaling AI to production under board/CIO/CAIO pressure. **~75 minutes** elapse from initial compromise to the attacker reaching high-value AI assets. Governing frameworks: OWASP LLM Top 10, NIST AI RMF, MITRE ATLAS, ISO/IEC 42001.
- **Learner role:** a security Cloud Solution Architect advising Acesa's SOC.
- **Stakeholder personas** (the workshop cast; reference them in framing, especially Ex04/Ex05): **Vikram** (CISO), **Michelle** (CAIO), **Phillip** (Identity & SecOps Lead), **Nancy** (Data Security & Governance Lead), **Amy** (App/AI Security Lead), **Quinton** (Infrastructure & Architecture Lead).
- **AI application under attack:** the **Acesa Refund Agent** — an internal, RAG-grounded generative-AI agent that helps staff resolve customer refund cases.
- **Microsoft products:** Microsoft Defender XDR (Defender for Identity, for Endpoint, for Office 365, for Cloud Apps), Microsoft Entra (ID Protection, Conditional Access), Microsoft Purview (DSPM for AI), Microsoft Sentinel, Microsoft Security Copilot, Azure AI Content Safety / Defender for Cloud threat protection for AI.
- **Module deliverable — "Proof Through Scenario":** an end-to-end attack visualization + a failure-point log + a business-impact summary, proving the current SOC missed the chain and the AI-driven SOC catches it. Feeds Module 4 (SOC operating model) and Module 5 (executive value).

### Invented for this lab (illustrative — confirm at build)
| Element | Value |
| --- | --- |
| Lab tenant | `acesa.onmicrosoft.com` |
| Compromised user (Stage 1) | **Mariya Petrova**, Refund Operations Analyst — `mariya.petrova@acesa.com`, Seattle |
| Victim endpoint (Stage 5) | **OPS-LT-0427** (Windows 11); malicious script `update_check.ps1` (encoded PowerShell beacon) |
| Service principal (Stage 4) | `sp-refund-agent-inference` |
| AI infra | Azure AI Foundry project `refund-agent-prod`, model deployment `gpt-4o`, resource group `rg-acesa-ai-prod`, West US 3 |
| RAG grounding source | SharePoint site **"Refund Policy Knowledge Base"** (`/sites/RefundKB`) |
| Poisoned document (Stage 2) | **`Vendor-Refund-Policy-Update-Q3.docx`** — carries a hidden prompt-injection payload |
| Attacker infra | phishing sender `billing@acesa-refunds[.]net` (look-alike domain); attacker sign-in IP `102.89.42.17` (Lagos, NG) |
| Unified incident title | **"Multi-stage incident involving Identity, AI, Data, and Infrastructure"** |
| Sentinel automation/playbook | Logic App **`Acesa-Contain-CrossLayer`** |
| KQL tables | `SigninLogs`, `AADUserRiskEvents`, `IdentityLogonEvents`, `EmailEvents`, `EmailUrlInfo`, `DeviceProcessEvents`, `DeviceNetworkEvents`, `AzureActivity`, `CloudAppEvents`; custom seeded: `RefundAgentPromptLogs_CL`, `AIInferenceAudit_CL` |

### The seeded attack chain (Day 0, Pacific time — rebased so it appears just before the session)
| # | Time | Layer | Event | Surfaces in |
| --- | --- | --- | --- | --- |
| 1 — Initial access | 08:31 | Identity | AiTM phishing email to Mariya → she authenticates through the proxy → session token + credentials stolen → impossible-travel sign-in (Seattle → Lagos) | Entra ID Protection (risky sign-in, medium) |
| 2 — Poisoning | 08:47 | Data / AI grounding | Using the stolen session, the attacker uploads `Vendor-Refund-Policy-Update-Q3.docx` into the Refund Policy Knowledge Base that grounds the Refund Agent | Defender for Office 365 (the delivery email); Purview DSPM for AI (sensitive/poisoned content in a grounding source) |
| 3 — Reasoning probe | 09:05–09:25 | AI | High-volume prompt-injection / jailbreak attempts against the Refund Agent endpoint | Defender for Cloud threat protection for AI; Azure AI Content Safety Prompt Shields |
| 4 — Lateral movement | 09:38 | Infrastructure | `sp-refund-agent-inference` makes anomalous token/compute requests toward the GPU inference infra in `rg-acesa-ai-prod` | Defender for Identity; Sentinel (`AzureActivity`) |
| 5 — Execution | 09:46 | Endpoint | `update_check.ps1` runs on OPS-LT-0427 (encoded PowerShell, outbound beacon) | Defender for Endpoint |

Each stage is individually low-severity and lands in a different console — the **signal-overload** problem. Only cross-layer correlation reveals the chain.

### Entities to surface (Exercise 01 output)
Mariya Petrova (user) · `sp-refund-agent-inference` (service principal) · OPS-LT-0427 (device) · `Vendor-Refund-Policy-Update-Q3.docx` (file) · Acesa Refund Agent / `refund-agent-prod` (AI workload) · `102.89.42.17` (sign-in IP, Lagos) · `billing@acesa-refunds[.]net` (sender) · Refund Policy Knowledge Base (grounding source).

### Coordinated response (Exercise 03) & autonomy boundary
- **Identity:** revoke Mariya's sessions + force reauthentication (Entra Conditional Access); disable and rotate `sp-refund-agent-inference`.
- **Data / AI:** quarantine `Vendor-Refund-Policy-Update-Q3.docx`; use Purview DSPM for AI to find which Refund Agent interactions drew on the poisoned grounding.
- **Infrastructure:** isolate / restrict the affected inference deployment via the `Acesa-Contain-CrossLayer` playbook.
- **Autonomy boundary (illustrative):** auto (no human) = revoke session tokens, quarantine the doc, disable the suspicious service principal; human-approved = isolating production inference infrastructure / disabling the Refund Agent (business-impacting).

### Failure points & blind spots (Exercise 02 / Ex04)
Signals existed but were **uncorrelated** across Entra, Defender for Office 365, the AI-threat surface, Defender for Identity, and Defender for Endpoint. The **blind spot** is the AI layer: no correlation between the poisoned grounding source → Refund Agent behavior → identity/endpoint activity. Business impact: 50–75 tools, alert fatigue, ~75-minute attacker dwell to high-value assets, and a manual response too slow to contain at machine speed.

## Common commands

```bash
bundle install              # install Jekyll + just-the-docs (Ruby 3.x required)
bundle exec jekyll serve    # preview at http://localhost:4000
bundle exec jekyll build    # build the static site into _site/
```

A Ruby 3.x dev container is provided in `.devcontainer/` for local preview.
