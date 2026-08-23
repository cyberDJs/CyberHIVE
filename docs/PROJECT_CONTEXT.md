# CyberHIVE AI — Project Context

**Status:** Discovery / Architecture  
**Current milestone:** M0 — Architecture and runnable local prototype  
**Last updated:** 2026-08-23  
**Canonical repository:** `cyberDJs/CyberHIVE`  
**Canonical Drive folder:** `CyberHIVE` (`14LjBzaT5vjbULTKqAK6zt3UUydixVqUW`)

## Mission

CyberHIVE is an open-source, local-first platform for secure operation, orchestration and management of AI models, agents, tools, skills and compute nodes on owned hardware, servers and optional cloud infrastructure.

## Initial target

- Ryzen-class x86_64 CPU
- 32 GB RAM reference profile
- NVIDIA RTX 3070 reference GPU
- headless Linux
- web administration
- optional kiosk mode
- one controller and one or more workers

## Core capabilities

- physical, VM and cloud installation
- local inference
- model catalog
- worker-node management
- secure enrollment and discovery
- API and web console
- skill registry and later skill composition
- updates, rollback and recovery
- monitoring and audit
- optional remote administration
- future compute/skill marketplace

## Architecture principles

- local-first
- privacy-first
- secure-by-default
- modular monolith before microservices
- OCI-compatible workloads
- reproducible builds
- explicit trust boundaries
- no mandatory Kubernetes
- open APIs and portable formats
- measurable performance
- graceful offline operation

## Non-goals for MVP

- own foundation model
- global decentralized compute network
- public marketplace
- full enterprise multi-tenancy
- cryptocurrency incentives
- universal GPU/OS support

## Terminology

- **Hive Controller** — orchestration/control node
- **Worker Node** — compute node
- **Appliance** — self-contained CyberHIVE installation
- **Model Runtime** — inference backend
- **Skill** — reusable operational workflow
- **Connector** — integration with an external service

## Current decisions

- no desktop environment in the base install
- web UI as primary administration surface
- RTX 3070 as first reference GPU
- containers allowed; Kubernetes optional
- cloud features optional
- updates must support rollback

## Open decisions

- base Linux distribution
- inference runtime(s)
- API gateway strategy
- service/node discovery
- model registry format
- LiveUSB/appliance distribution path
- node identity and enrollment protocol

## Definition of done

A change is complete only when implementation works, relevant tests run, security impact is documented, verification is defined, rollback/recovery is known, docs are updated and no undocumented dependency is introduced.

## Sources of truth

- code/config/docs: GitHub repository
- architectural decisions: `docs/adr/`
- current project state: this file
- roadmap: `docs/ROADMAP.md`
- large/source assets: Google Drive
- approved exports: repository `assets/`
