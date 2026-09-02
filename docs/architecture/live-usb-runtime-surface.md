# CyberHIVE Live USB Runtime Surface

## Purpose

Define the visible and operational surface of the first CyberHIVE Live USB runtime.

The runtime surface must make the fabric understandable at boot time: what this node is, what it can do, what it will not do, how it is connected, and whether it is safe.

## Required surfaces

### Boot splash

Shows:

- CyberHIVE branding,
- image version,
- live USB status,
- safety statement,
- boot progress or health stage.

### Boot role selector

Allows operator to select:

- Controller + Worker,
- Worker Only,
- DevBridge Mode,
- Offline Diagnostics,
- Rescue / Hardware Inventory.

The selector must clearly describe security implications for each role.

### Local dashboard

Minimum dashboard cards:

- node status,
- hardware inventory,
- capability map,
- cache health,
- network health,
- DevBridge/MCP state,
- logs/evidence,
- cluster peers/topology when joined.

### Health endpoint or command

A machine-readable health surface must exist before any large UI is treated as complete.

Candidate:

```text
GET /health
cyberhive health
```

### Hardware inventory

Hardware inventory should report capabilities, not just labels.

Capability dimensions:

- CPU,
- GPU/NPU where available,
- RAM,
- VRAM where available,
- storage type and free space,
- network interfaces and link state,
- battery state where available,
- thermal state where available,
- platform and architecture,
- current load.

## Peer class examples

- heavy compute peer,
- cache seed peer,
- controller peer,
- worker peer,
- mobile opportunistic peer,
- watchOS micro-peer,
- relay peer,
- diagnostics peer.

## Local-first behavior

The runtime should remain useful with no internet connection:

- show local health,
- collect inventory,
- inspect cache,
- export logs,
- run offline diagnostics,
- wait for local enrollment/discovery.

## Fabric behavior

When joined to a fabric, the runtime should expose:

- peer list,
- peer role,
- link quality,
- capability summary,
- cache state,
- current tasks,
- recent failures,
- evidence and receipts.

## Anti-goals

The runtime surface must not hide:

- whether DevBridge is enabled,
- whether remote access is enabled,
- whether persistent overlay is active,
- whether disks are mounted,
- whether the node is enrolled or anonymous,
- whether network links are weak or degraded.
