---
title: Introduction
layout: home
nav_order: 1
---

# Using AI to Secure the Modern SOC — Module 3 Hands-On Lab

**Cross-Layer Attack Lab (End-to-End)**

This hands-on lab is the practical core of **Module 3** of the *Using AI to Secure the Modern SOC* workshop. While the surrounding modules reason about AI threats, architecture, SOC operations, and executive value on a whiteboard, this module puts you in a **live tenant** to investigate and respond to a coordinated, AI-driven attack in real Microsoft tooling — and to produce the module's executive deliverable, the **Proof Through Scenario**, that feeds Modules 4 and 5.

## Scenario

You are a security Cloud Solution Architect advising **Zava**, a large enterprise scaling AI from pilots to production on a heavy but fragmented Microsoft security investment. Zava's SOC is understaffed and buried under alert volume — its analysts are **drowning in alerts**, with roughly **25 real-looking incidents** in the queue (routine risky sign-ins, benign DLP hits, commodity malware, failed-logon bursts, impossible-but-benign travel) on any given shift.

Over a short window, a coordinated AI-driven attack has moved across **identity, data/AI grounding, AI, infrastructure, and endpoint**. Each signal is individually low-risk — an anonymous IP sign-in, a phishing email, a saved "policy update," some inference traffic, an endpoint script — lands in a different console, and is **randomly interspersed among the ~25 decoy incidents**. From the SOC's view nothing stands out. In reality, the **Zava Refund Agent** — a real Azure OpenAI endpoint — and the infrastructure behind it have been compromised.

You are brought in to prove what happened, show why detection failed, and demonstrate the AI-driven SecOps response that should have fired. The lab rewards **system-level SecOps judgment** — correlating signals across layers and recognizing where telemetry and automation gaps let the chain through — not single-product feature clicks.

## What you'll do

| # | Exercise | Duration |
|---|----------|----------|
| 00 | [Access Your Lab Environment](docs/00_lab_environment/00_lab_environment.html) | ~10–15 min |
| 01 | [Triage & Scope the Cross-Layer Incident](docs/01_triage_and_scope/01_triage_and_scope.html) | ~20 min |
| 02 | [Reconstruct the Attack Lifecycle Across Layers](docs/02_reconstruct_the_lifecycle/02_reconstruct_the_lifecycle.html) | ~25 min |
| 03 | [Design & Execute the Coordinated Response](docs/03_coordinated_response/03_coordinated_response.html) | ~25 min |
| 04 | [Proof Through Scenario — Visualize the Attack & Failure Points](docs/04_proof_through_scenario/04_proof_through_scenario.html) | ~15 min |
| 05 | [Wrap-Up & Hand-Off](docs/05_wrap_up_and_hand_off/05_wrap_up_and_hand_off.html) | <15 min (or post-delivery) |

{: .note }
> Durations are proposed and will be finalized against the parent workshop's timing design.

## Prerequisites

| Requirement | Details |
|-------------|---------|
| Lab credentials | A pre-provisioned, Azure-capable Zava tenant account, supplied by your facilitator |
| Browser | A current Microsoft Edge or Chrome browser — no VM or local install required |
| Microsoft 365 / Security licensing | Provisioned in the lab tenant: Microsoft 365 E5, Security Copilot (SCUs), Defender XDR, Entra ID Protection / Conditional Access |
| Azure subscription components | Provisioned and pre-seeded in the lab tenant: Microsoft Sentinel + Log Analytics workspace, an Azure OpenAI endpoint (the Zava Refund Agent — `oai-soclab-v02`, `gpt-4o` deployment), and Microsoft Defender for Cloud — AI threat protection enabled on it |
| Background (recommended) | Familiarity with Defender XDR incidents, KQL basics, and the idea of RAG-grounded AI apps. Modules 1–2 of the workshop provide the conceptual grounding. |

{: .note }
> **Azure costs:** All resources are provisioned in the lab tenant by the facilitator. You will not incur personal charges, and there is no learner cleanup — the environment is reset between cohorts.

## Lab environment

You investigate from the **Microsoft Defender portal** (unified SecOps), with **Microsoft Sentinel** as the telemetry backbone and **standalone Security Copilot** as the cross-layer reasoning spine. Everything you need is reachable from the browser with your assigned credentials. Exercise 00 walks you through signing in and confirming access before the investigation begins.
