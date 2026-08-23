# Hardware Registry

## Reference profile: CH-M0-RTX3070

Status: Active reference target

| Component | Reference |
| --- | --- |
| CPU | AMD Ryzen 7 5800X |
| RAM | 32 GB |
| GPU | NVIDIA GeForce RTX 3070 |
| VRAM | 8 GB |
| Architecture | NVIDIA Ampere |
| Compute capability | 8.6 |
| OS candidate | Ubuntu Server 24.04 LTS amd64 |
| Display requirement | None; headless |

## Purpose

This profile is the minimum concrete M0 target used to prevent architecture decisions from drifting toward datacenter-only hardware.

CyberHIVE may support weaker and stronger machines, but a change that breaks this reference profile requires an explicit architecture decision.

## Facts to inventory per node

The node agent must eventually collect and expose:

- stable CyberHIVE node ID,
- CPU model, core/thread count and architecture,
- total and available RAM,
- GPU vendor/model/count,
- VRAM per GPU,
- GPU compute capability where applicable,
- driver/runtime versions,
- storage devices, capacity and free space,
- network interfaces and link speed where observable,
- OS, kernel and container runtime,
- supported inference runtime capabilities,
- current load and thermal/resource state where available.

## Future profiles

Planned certification classes:

- CPU-only / development node,
- low-VRAM NVIDIA node,
- 8 GB consumer NVIDIA node,
- 12-24 GB prosumer NVIDIA node,
- multi-GPU workstation,
- datacenter NVIDIA node,
- AMD ROCm node,
- Apple Silicon node.

Profiles are capability targets, not vendor lock-in contracts.
