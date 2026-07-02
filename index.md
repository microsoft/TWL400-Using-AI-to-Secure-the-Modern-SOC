---
title: Introduction
layout: home
nav_order: 1
---

# TechWorkshop L400: Using AI to Secure the Modern SOC

This lab guides you through a series of practical exercises for investigating and responding to a coordinated, AI-driven attack as part of Module 3 of the *Using AI to Secure the Modern SOC* workshop. You advise Zava, an enterprise whose SOC is buried in routine, noisy alerts while a five-stage attack moves across identity, data/AI grounding, AI workloads, infrastructure, and endpoint — each signal individually low-risk and landing in a different console. Exercises cover triage and signal correlation, attack lifecycle reconstruction, coordinated automated response, and production of the Proof Through Scenario executive deliverable, using Microsoft Security Copilot, Microsoft Defender XDR, Microsoft Sentinel, Entra ID, and Microsoft Defender for Cloud. 

## Exercises

This lab has exercises on:

* Accessing the lab environment and verifying portal access
* Triaging and scoping a cross-layer attack incident using Security Copilot
* Reconstructing the full attack lifecycle across identity, data/AI grounding, AI, infrastructure, and endpoint
* Designing and executing a coordinated automated response using Microsoft Sentinel
* Packaging the Proof Through Scenario — end-to-end attack visualization, failure analysis, and executive business impact
* Wrapping up and handing off to subsequent workshop modules

## Prerequisites

For running this lab you will need:

* A pre-provisioned Zava lab tenant account with Azure access, supplied by your facilitator
* A current Microsoft Edge or Chrome browser (no VM or local install required)
* Microsoft 365 E5, Security Copilot (SCUs), Defender XDR, and Entra ID Protection / Conditional Access — provisioned in the lab tenant
* Microsoft Sentinel, an Azure OpenAI endpoint (the Zava Refund Agent — `oai-soclab-v02`, `gpt-4o` deployment), and Microsoft Defender for Cloud — AI threat protection — provisioned and pre-seeded in the lab tenant
* Familiarity with Defender XDR incidents, KQL basics, and RAG-grounded AI apps (recommended — Modules 1–2 provide the conceptual grounding)
