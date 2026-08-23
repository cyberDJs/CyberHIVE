# ADR-0002: Base operating system for M0

Status: Proposed
Date: 2026-08-23

## Context

CyberHIVE needs a conservative Linux baseline for headless NVIDIA inference on the first reference node: Ryzen 7 5800X, 32 GB RAM and GeForce RTX 3070.

The base image must favor NVIDIA driver/CUDA compatibility, reproducibility, long maintenance windows and broad ecosystem support over novelty.

## Decision

Use **Ubuntu Server 24.04 LTS amd64** as the M0 reference operating system.

Do not make Ubuntu a permanent product dependency. Keep host-specific logic behind installation and hardware-adapter boundaries so additional distributions can be certified later.

## Why

- NVIDIA CUDA documentation explicitly qualifies Ubuntu 24.04 LTS in current Linux support matrices.
- Ubuntu 24.04 LTS has a stable server ecosystem and standard security support through May 2029.
- Current AI runtimes, container tooling and NVIDIA packaging have broad Ubuntu support.
- Ubuntu 26.04 LTS is newer, but the M0 goal is compatibility and repeatability rather than chasing the newest host release.

## Alternatives considered

### Ubuntu Server 26.04 LTS

Longer lifecycle, but not selected for the first reference image until the exact CUDA/runtime matrix used by CyberHIVE is validated end-to-end on it.

### Debian

Excellent minimal base and a future certification target. Ubuntu wins M0 on NVIDIA ecosystem friction and common deployment documentation.

### Fedora / immutable Fedora variants

Interesting for appliance-style operation, but faster release cadence increases validation burden for the initial NVIDIA baseline.

## Consequences

- M0 install and benchmark automation targets Ubuntu Server 24.04 LTS first.
- Host adapters must avoid unnecessary Ubuntu-only assumptions.
- A later ADR may replace the appliance host with an immutable image once the runtime contract is stable.

## Validation gates

Before accepting this ADR:

1. Clean Ubuntu Server 24.04 LTS installation boots headless.
2. NVIDIA driver and container GPU access work on RTX 3070.
3. Reference inference runtimes pass the M0 benchmark matrix.
4. Reboot preserves GPU/runtime functionality.
5. Installation and rollback steps are documented.
