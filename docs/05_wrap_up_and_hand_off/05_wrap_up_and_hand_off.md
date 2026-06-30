---
title: 'Wrap-Up & Hand-Off'
layout: default
nav_order: 7
---

# Wrap-Up & Hand-Off

## Duration

**Estimated time:** <15 minutes (or post-delivery)

## What you produced

In one continuous incident you pulled the chain out of ~25 incidents — taking Zava from "a queue full of low-severity noise it was drowning in" to a defensible, executive-ready account of a coordinated, AI-driven attack. Along the way you produced the four artifacts that make up the module's **Proof Through Scenario**:

| Exercise | Artifact |
|----------|----------|
| 01 — Triage & Scope | Cross-domain incident narrative (one chain cut out of ~25 decoy incidents) + entity list + initial timeline |
| 02 — Reconstruct | Reconstructed attack lifecycle across all five stages + detection-failure / blind-spot log |
| 03 — Coordinated Response | Coordinated cross-layer response record + Sentinel automation + agent-autonomy boundary + residual-risk note |
| 04 — Proof Through Scenario | End-to-end attack visualization + failure-point summary tied to business impact |

## Key takeaways

- **The attack was always visible — just never assembled, and buried in noise.** Every stage emitted a signal — including a real Defender for Cloud — AI threat protection alert on the Refund Agent — but the signals sat uncorrelated and scattered among ~25 decoy incidents. The failure was correlation across layers and consoles, not missing detection. Cross-layer reasoning (Security Copilot over unified telemetry) is what turned five quiet alerts into one chain.
- **The AI layer fired — but no one connected it.** Defender for Cloud — AI threat protection raised a native alert on the prompt-injection probing of the real Azure OpenAI Refund Agent, and the poisoning of its grounding source was the most consequential stage. Yet that alert was present-but-uncorrelated into the cross-layer incident and lost in the decoy noise. Securing the modern SOC means pulling AI-layer telemetry into the same incident as identity, endpoint, and infrastructure.
- **Speed is a design decision.** With ~75 minutes from compromise to high-value AI assets, a manual, console-by-console response loses. Coordinated automation — bounded by an explicit autonomy boundary — is what closes the gap.

## Where this goes next

The **Proof Through Scenario** is the empirical centerpiece you hand to the rest of the workshop:

- **Module 4 (SOC Operations + Optimization)** uses your failure-point log to redesign the operating model — unified telemetry, correlation, and the automation that should have fired.
- **Module 5 (Business Value & Executive Engagement)** uses your business-impact summary to make the case to leadership — **Vikram** (CISO) on consolidated architecture and ROI, **Michelle** (CAIO) on shipping AI safely without slowing it down.

## Lab environment cleanup

None required for learners. The injected `SocLabEvents_CL` events and the planted grounding doc (`trusted-report.docx`) are managed by a scripted reset that re-seeds them between cohorts — there is no learner-owned resource to delete.

The ~25 decoy incidents and the real Microsoft Defender for Cloud — AI threat protection alert in `SecurityAlert` are native tenant artifacts; they persist across cohorts and do not need to be reset.

## Further learning

- [Microsoft Security Copilot documentation](https://learn.microsoft.com/en-us/copilot/security/){:target="_blank"}
- [Microsoft Defender XDR — unified SecOps](https://learn.microsoft.com/en-us/unified-secops-platform/overview-unified-security){:target="_blank"}
- [Threat protection for AI workloads in Defender for Cloud](https://learn.microsoft.com/en-us/azure/defender-for-cloud/ai-threat-protection){:target="_blank"}

Congratulations! You proved what happened to Zava, showed exactly why the current SOC missed it — uncorrelated signals buried in ~25 decoy incidents, and demonstrated the AI-driven response that contains it at machine speed — and you packaged that proof for leadership. That is the work of securing the modern SOC.
