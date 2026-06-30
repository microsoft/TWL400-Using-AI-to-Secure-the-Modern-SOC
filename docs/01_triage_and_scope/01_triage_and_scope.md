---
title: 'Exercise 01: Triage & Scope the Cross-Layer Incident'
layout: default
nav_order: 3
has_children: true
---

# Exercise 01: Triage & Scope the Cross-Layer Incident

## Scenario

Zava's SOC queue is full of individually low-severity alerts touching different products — a flagged sign-in, a reported email, an endpoint detection, some AI-app telemetry. The catch: those five attack-chain signals are buried among **~25 real-looking decoy incidents** (routine risky sign-ins, benign DLP hits, commodity malware, failed-logon bursts, impossible-but-benign travel), randomly interspersed so nothing is conveniently first or last. Zava is "drowning in alerts" — nothing screams "incident." In this exercise you **cut the chain out of the ~25 decoys** and use **standalone Security Copilot** as a reasoning layer over Defender XDR, Entra, Defender for Cloud (AI), and endpoint signals to pull the scattered signals into a **single cross-domain narrative**.

This is the "from many alerts to one chain" step. The narrative, entities, and initial timeline you produce here are the raw material the rest of the lab builds on.

## Objectives

After completing this exercise, you'll be able to:

* Navigate the Defender XDR cross-layer incident and recognize how signal overload hides the real attack
* Use standalone Security Copilot as a reasoning layer over Defender, Entra, Defender for Cloud (AI), and endpoint signals
* Synthesize identity, email/poisoning, AI, infrastructure, and endpoint signals into one cross-domain incident narrative
* Extract the key entities and an initial timeline to carry into reconstruction

## Duration

* **Estimated Time:** 20 minutes
