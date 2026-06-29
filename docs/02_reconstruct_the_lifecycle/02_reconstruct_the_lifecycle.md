---
title: 'Exercise 02: Reconstruct the Attack Lifecycle Across Layers'
layout: default
nav_order: 4
has_children: true
---

# Exercise 02: Reconstruct the Attack Lifecycle Across Layers

## Scenario

In Exercise 01 you cut the cross-layer chain out of the ~25 decoy incidents and captured the entities and an initial timeline. That narrative is persuasive, but it was built from correlated *alerts* — the events that happened to fire. Several of those signals fired in isolation and were buried in the noise, including a **real Defender for Cloud — AI threat protection alert** for the AI-layer attack that never got correlated into the cross-layer incident.

In this exercise you reconstruct the **full lifecycle** directly from telemetry. Using **Microsoft Sentinel** as the unified data backbone and **Defender for Identity** for the identity and lateral-movement view, you trace the attack end to end — from the AiTM sign-in for Mariya Petrova, through the poisoning of the Refund Agent's grounding source and the prompt-injection probing, to the move toward the AI/GPU inference infrastructure and the script execution on the endpoint. Then you do the harder part: you find exactly **where detection and response should have fired but didn't** — signals that were present but **uncorrelated and buried in the ~25-decoy noise** — and reason about the **conflicting signals** that make this attack so hard to read while it is happening.

This is the "from one chain to a complete, evidence-backed lifecycle" step. The placed stages, the gap log, and the dependency notes you produce here are the raw material for the coordinated response you build in Exercise 03 and the **Proof Through Scenario** you assemble in Exercise 04.

## Objectives

After completing this exercise, you'll be able to:

* Trace the attack end to end across identity → email/poisoning → AI → infrastructure → endpoint using unified Sentinel telemetry, the Defender for Cloud AI alert, and Defender for Identity
* Hunt the Sentinel-backed tables with KQL to place each of the five attack stages on the lifecycle and link them to the entities from Exercise 01
* Reconstruct the lifecycle and bound each stage's blast radius
* Identify system-level **failure points** — signals that were present (including a real AI-layer alert) but **uncorrelated and buried in the ~25-decoy noise**
* Reason about the uncertainties and conflicting signals that make the attack hard to read in real time

## Duration

* **Estimated time:** 25 minutes

## Tasks

- Task 02.01 — [Hunt the unified Sentinel telemetry (KQL) and place each stage](02_01.html)
- Task 02.02 — [Confirm anonymous IP sign-in and lateral movement (Defender for Identity)](02_02.html)
- Task 02.03 — [Mark detection-failure points and telemetry blind spots](02_03.html)
- Task 02.04 — [Record systemic dependencies and conflicting signals](02_04.html)
