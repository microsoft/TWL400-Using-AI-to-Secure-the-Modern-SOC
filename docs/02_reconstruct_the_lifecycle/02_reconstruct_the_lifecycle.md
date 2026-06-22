---
title: 'Exercise 02: Reconstruct the Attack Lifecycle Across Layers'
layout: default
nav_order: 4
has_children: true
---

# Exercise 02: Reconstruct the Attack Lifecycle Across Layers

## Scenario

In Exercise 01 you pulled scattered alerts into one cross-domain narrative and captured the entities and an initial timeline. That narrative is persuasive, but it was built from correlated *alerts* — the events that happened to fire. Some stages of this attack barely registered, and the most consequential one (the AI layer) produced almost no native detection at all.

In this exercise you reconstruct the **full lifecycle** directly from telemetry. Using **Microsoft Sentinel** as the unified data backbone and **Defender for Identity** for the identity and lateral-movement view, you trace the attack end to end — from the AiTM sign-in for Mariya Petrova, through the poisoning of the Refund Agent's grounding source and the prompt-injection probing, to the move toward the AI/GPU inference infrastructure and the script execution on the endpoint. Then you do the harder part: you find exactly **where detection and response should have fired but didn't**, name the **telemetry that was never collected**, and reason about the **conflicting signals** that make this attack so hard to read while it is happening.

This is the "from one chain to a complete, evidence-backed lifecycle" step. The placed stages, the gap log, and the dependency notes you produce here are the raw material for the coordinated response you build in Exercise 03 and the **Proof Through Scenario** you assemble in Exercise 04.

## Objectives

After completing this exercise, you'll be able to:

* Trace the attack end to end across identity → endpoint → data/AI → infrastructure using unified Sentinel telemetry and Defender for Identity
* Hunt the Sentinel-backed tables with KQL to place each of the five attack stages on the lifecycle and link them to the entities from Exercise 01
* Reconstruct the lifecycle and bound each stage's blast radius
* Identify system-level **failure points** (signals that were present but uncorrelated) and **blind spots** (telemetry missing entirely — especially at the AI layer)
* Reason about the uncertainties and conflicting signals that make the attack hard to read in real time

## Duration

* **Estimated time:** 35 minutes

## Tasks

- Task 02.01 — [Hunt the unified Sentinel telemetry (KQL) and place each stage](02_01.md)
- Task 02.02 — [Confirm impossible travel and lateral movement (Defender for Identity)](02_02.md)
- Task 02.03 — [Mark detection-failure points and telemetry blind spots](02_03.md)
- Task 02.04 — [Record systemic dependencies and conflicting signals](02_04.md)
