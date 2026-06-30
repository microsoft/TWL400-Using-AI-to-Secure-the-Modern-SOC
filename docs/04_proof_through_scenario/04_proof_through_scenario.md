---
title: 'Exercise 04: Proof Through Scenario'
layout: default
nav_order: 6
has_children: true
---

# Exercise 04: Proof Through Scenario

## Scenario

You've done the hard analytical work: in Exercise 01 you scoped a cross-layer incident into one narrative, in Exercise 02 you reconstructed the full attack lifecycle and named every detection failure and blind spot, and in Exercise 03 you ran the coordinated response and drew the autonomy boundary. Now you have to make it *land* — for people who will never open a KQL pane.

This exercise turns the investigation into the module's executive-facing deliverable: the **Proof Through Scenario**. You'll use **Security Copilot** to synthesize the lab into a clear end-to-end attack visualization and a summary of the main failure points — the concrete evidence that Zava's current SOC missed the chain and that an AI-driven SOC catches it. The artifact you produce here is the hand-off into Module 4 (the SOC operating model) and Module 5 (the executive-value case). Frame everything for **Vikram** (the CISO) and **Michelle** (the CAIO): they are the audience.

This is the "from one chain to one decision" step. You're not finding anything new — you're packaging what you found so it changes how Zava runs its SOC.

## Objectives

After completing this exercise, you'll be able to:

* Synthesize the investigation into a single end-to-end attack visualization spanning identity, data/AI, AI, infrastructure, and endpoint
* Summarize the main detection and response failure points and explain why each one broke down
* Tie those failures to Zava's SOC-overload business impact and articulate what the AI-driven response changes
* Produce the **Proof Through Scenario** deliverable that feeds the operating-model (Module 4) and executive-value (Module 5) modules

## Duration

* **Estimated Time:** 15 minutes
