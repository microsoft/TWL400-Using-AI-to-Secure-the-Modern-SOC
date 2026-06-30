---
title: 'Exercise 03: Design & Execute the Coordinated Response'
layout: default
nav_order: 5
has_children: true
---

# Exercise 03: Design & Execute the Coordinated Response

## Scenario

You understand the attack. In Exercise 01 you cut the chain out of the ~25 decoy incidents into one cross-domain narrative; in Exercise 02 you reconstructed the full lifecycle from telemetry and marked every point where detection and response should have fired. The chain is no longer a mystery — it is a known sequence that touched **identity, AI, data, infrastructure, and endpoint**.

Knowing is not containing. The attacker phished Mariya Petrova, poisoned the Refund Agent's grounding source, probed the model, reached toward the GPU inference infrastructure, and ran a script on an endpoint — and as of right now, none of that has been undone. A traditional SOC would now open a half-dozen tickets across a half-dozen consoles and contain one layer at a time, slowly, by hand. That is exactly the gap that let the attacker reach high-value AI assets in roughly **75 minutes**.

In this exercise you do it the way an AI-driven SOC should: you design a **coordinated, cross-layer response** and execute it across every layer the attack touched — at machine speed where it is safe to, with a human in the loop where it is not. You use **Microsoft Security Copilot** to recommend and accelerate the response, **Microsoft Sentinel automation** to operationalize it, **Entra Conditional Access** to contain the identity, and **Microsoft Defender for Cloud — AI threat protection** (its AI-attack alert, queryable via `SecurityAlert` / `ExtendedProperties`) together with the injected Stage-2 event to bound the damage to the AI layer. Then you make the call every AI-SOC has to make: which of these actions may run **autonomously**, which require **human approval**, and what risk remains after the dust settles.

This is the "from understanding to containment" step. The executed response, the automation, the autonomy boundary, and the residual-risk note you produce here feed directly into the **Proof Through Scenario** you assemble in Exercise 04 and the SOC operating model in Module 4.

## Objectives

After completing this exercise, you'll be able to:

* Design a coordinated, cross-layer response to the reconstructed attack from Exercise 02
* Execute response actions spanning identity, data, and infrastructure layers
* Use Security Copilot to recommend and accelerate the response, and Sentinel automation to operationalize it
* Define a decision boundary for autonomous vs human-approved actions, with rationale
* Document the residual risk that remains after containment

## Duration

* **Estimated Time:** 25 minutes
