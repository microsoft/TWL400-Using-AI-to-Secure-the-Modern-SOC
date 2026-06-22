---
title: 'Wrap-Up & Hand-Off'
layout: default
nav_order: 7
---

# Wrap-Up & Hand-Off

## What you produced

In one continuous incident you took Acesa from "a queue full of low-severity noise" to a defensible, executive-ready account of a coordinated, AI-driven attack. Along the way you produced the four artifacts that make up the module's **Proof Through Scenario**:

| Exercise | Artifact |
|----------|----------|
| 01 — Triage & Scope | Cross-domain incident narrative (one chain from many alerts) + entity list + initial timeline |
| 02 — Reconstruct | Reconstructed attack lifecycle across all five stages + detection-failure / blind-spot log |
| 03 — Coordinated Response | Coordinated cross-layer response record + Sentinel automation + agent-autonomy boundary + residual-risk note |
| 04 — Proof Through Scenario | End-to-end attack visualization + failure-point summary tied to business impact |

## Key takeaways

- **The attack was always visible — just never assembled.** Every stage emitted a signal; the failure was correlation across layers and consoles, not missing detection. Cross-layer reasoning (Security Copilot over unified telemetry) is what turned five quiet alerts into one chain.
- **The AI layer is the blind spot.** The poisoning of the Refund Agent's grounding source and the prompt-injection probing were the most consequential and the least connected to anything else. Securing the modern SOC means bringing AI-layer telemetry into the same incident as identity, endpoint, and infrastructure.
- **Speed is a design decision.** With ~75 minutes from compromise to high-value AI assets, a manual, console-by-console response loses. Coordinated automation — bounded by an explicit autonomy boundary — is what closes the gap.

## Where this goes next

The **Proof Through Scenario** is the empirical centerpiece you hand to the rest of the workshop:

- **Module 4 (SOC Operations + Optimization)** uses your failure-point log to redesign the operating model — unified telemetry, correlation, and the automation that should have fired.
- **Module 5 (Business Value & Executive Engagement)** uses your business-impact summary to make the case to leadership — **Vikram** (CISO) on consolidated architecture and ROI, **Michelle** (CAIO) on shipping AI safely without slowing it down.

## Lab environment cleanup

None required. This lab runs in a hosted tenant that your facilitator resets between cohorts — there are no learner-owned resources to delete.

## Further learning

- [Microsoft Security Copilot documentation](https://learn.microsoft.com/en-us/copilot/security/){:target="_blank"}
- [Microsoft Defender XDR — unified SecOps](https://learn.microsoft.com/en-us/unified-secops-platform/overview-unified-security){:target="_blank"}
- [Microsoft Purview Data Security Posture Management for AI](https://learn.microsoft.com/en-us/purview/ai-microsoft-purview){:target="_blank"}
- [Threat protection for AI workloads in Defender for Cloud](https://learn.microsoft.com/en-us/azure/defender-for-cloud/ai-threat-protection){:target="_blank"}

## Summary

You proved what happened to Acesa, showed exactly why the current SOC missed it, and demonstrated the AI-driven response that contains it at machine speed — and you packaged that proof for leadership. That is the work of securing the modern SOC.
