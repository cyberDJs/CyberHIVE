# ADR-0001 — Local-first modular baseline

**Status:** Accepted  
**Date:** 2026-08-23

## Context

CyberHIVE targets local consumer/prosumer hardware and must remain understandable, recoverable and portable.

## Decision

Start with a modular monolith for the control plane, isolated inference runtimes through adapters, headless Linux, web administration, OCI-compatible packaging where useful and no mandatory Kubernetes.

## Consequences

Lower operational complexity and easier single-node deployment. Module boundaries must still be explicit enough to allow later extraction when justified by measurement or isolation requirements.
