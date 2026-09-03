# CyberHIVE AI — Project Context

**Status:** Active prototype / appliance hardening  
**Current milestone:** M1.1 — CyberHIVE Live Appliance v0.2  
**Last updated:** 2026-09-03  
**Canonical repository:** `cyberDJs/CyberHIVE`  
**Canonical Drive folder:** `CyberHIVE` (`14LjBzaT5vjbULTKqAK6zt3UUydixVqUW`)

## Mission

CyberHIVE is an open-source, local-first platform for secure operation, orchestration and management of AI models, agents, tools, skills and compute nodes on owned hardware, servers and optional cloud infrastructure.

## Initial target

- x86_64 owned hardware
- 32 GB RAM reference profile
- NVIDIA RTX 3070 reference GPU for later inference work
- headless-first Linux appliance
- browser-first administration
- optional later local desktop/kiosk profile
- one controller and one or more workers

## Proven Live USB baseline

The first Debian 12/bookworm CyberHIVE Live USB candidate was built from the PR #27 exact head `63c14dba7fd28b8a0d53c23bbda766b06d950260`, written to removable media, verified byte-for-byte, and physically booted on x86_64 hardware on 2026-09-03.

That evidence proves image creation, media integrity and a physical boot into the CyberHIVE live shell. It does not by itself prove every host-disk safety claim, remote-access behavior, deployment behavior or ADR acceptance.

## Core capabilities

- physical, VM and cloud installation
- local inference
- model catalog
- worker-node management
- secure enrollment and discovery
- API and web console
- skill registry and later skill composition
- updates, rollback and recovery
- monitoring, support evidence and audit
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
- browser-first control plane before desktop duplication

## Current decisions

- Debian 12/bookworm is the first proven Live USB candidate base; this does not yet freeze every future installation profile.
- web UI is the primary administration surface
- no desktop environment in the base image; a later optional desktop reuses the same web UI/API
- SSH server is part of Live Appliance v0.2
- SSH bootstrap uses key-first mode from a `CYBERHIVE_CFG` config medium, with an ephemeral password fallback only when no key is available
- root SSH login remains disabled
- local browser discovery uses mDNS with `cyberhive.local` plus an IPv4 fallback
- browser control requires a local pairing code for the boot session
- live root remains ephemeral/read-only by design; persistence must be explicit
- internal host-disk writes remain outside the default runtime boundary
- remote help remains disabled until an explicit local enable action
- containers allowed; Kubernetes optional
- cloud features optional
- updates must support rollback

## Open decisions

- inference runtime(s)
- stable local API implementation and versioning
- model registry format
- node identity and enrollment protocol
- supported persistence/config-media provisioning format
- release signing and Secure Boot strategy
- desktop profile and local prompt UX after the browser control plane stabilizes

## Definition of done

A change is complete only when implementation works, relevant tests run, security impact is documented, verification is defined, rollback/recovery is known, docs are updated and no undocumented dependency is introduced.

## Sources of truth

- code/config/docs: GitHub repository
- architectural decisions: `docs/adr/`
- current project state: this file
- roadmap: `docs/ROADMAP.md`
- large/source assets: Google Drive
- approved exports: repository `assets/`
