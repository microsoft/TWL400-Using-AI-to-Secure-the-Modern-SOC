---
title: 'Exercise 01: Triage & Scope the Cross-Layer Incident'
layout: default
nav_order: 3
has_children: true
---

# Exercise 01: Triage & Scope the Cross-Layer Incident

## Scenario

Acesa's SOC queue is full of individually low-severity alerts touching different products — a flagged sign-in, a reported email, an endpoint detection, some AI-app telemetry. Nothing screams "incident." In this exercise you triage that noise and use **standalone Security Copilot** as a reasoning layer over Defender XDR, Entra, Purview, and endpoint signals to pull the scattered signals into a **single cross-domain narrative**.

This is the "from many alerts to one chain" step. The narrative, entities, and initial timeline you produce here are the raw material the rest of the lab builds on.

## Objectives

After completing this exercise, you'll be able to:

* Navigate the Defender XDR cross-layer incident and recognize how signal overload hides the real attack
* Use standalone Security Copilot as a reasoning layer over Defender, Entra, Purview, and endpoint signals
* Synthesize identity, email, endpoint, and data/AI signals into one cross-domain incident narrative
* Extract the key entities and an initial timeline to carry into reconstruction

## Duration

* **Estimated time:** 30 minutes

## Tasks

- Task 01.01 — [Open the unified incident in the Defender portal](01_01.md)
- Task 01.02 — [Correlate the scattered signals with Security Copilot](01_02.md)
- Task 01.03 — [Extract entities and assemble the initial timeline](01_03.md)
- Task 01.04 — [Recognize why signal overload hides the chain](01_04.md)
