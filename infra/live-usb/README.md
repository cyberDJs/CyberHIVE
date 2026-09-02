# CyberHIVE Live USB

Repository skeleton for the first CyberHIVE bootable runtime artifact.

## Goal

Build a portable live environment that can boot a compatible machine into a CyberHIVE node without installing to or mutating the host disk by default.

## Runtime roles

- `controller-worker` — local controller plus local worker
- `worker-only` — enrolled peer contributing capabilities
- `devbridge` — explicit development / MCP bridge mode
- `offline-diagnostics` — local hardware, cache and log checks
- `rescue-inventory` — safe hardware inventory and evidence export

## Product boundary

The live USB is the first bootstrap artifact, not the full platform boundary.

CyberHIVE remains a multi-platform peer-to-peer AI/compute/cache fabric. Future peers include Linux, macOS, Windows, Android, iOS/iPadOS where allowed, watchOS-constrained micro-peers, Raspberry Pi/ARM, NAS/edge devices, VPS and optional cloud nodes.

## Safety default

- no secrets in image
- no automatic inbound remote access
- no write to internal disks by default
- no trusted anonymous LAN compute
- no MCP/SSH/DevBridge exposure without explicit local enablement
- no destructive host operations in the first implementation

## Planned layout

```text
infra/live-usb/
├── README.md
├── build-plan.md
├── safety-boundary.md
└── debian-live/
    └── README.md
```
