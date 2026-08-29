# ADR-0018: LAN Discovery & Enrollment Handshake MVP

## Status
Accepted

## Context
CyberHIVE worker nodes need a way to appear on the local network without becoming trusted automatically. Previous patches added node identity, sessions, heartbeat and action dispatch. The next safe step is discovery as an untrusted precursor to enrollment.

## Decision
Add LAN discovery records and an enrollment handshake coordinator. The handshake issues a short-lived bootstrap token through the existing `EnrollmentAuthority`, exposes only redacted public challenge material, and completes enrollment only after a signed HMAC response.

## Consequences
- Local discovery is structured and testable without sockets.
- Public endpoints are rejected by default.
- Discovery and trust remain separate.
- Later mDNS, QR provisioning and mTLS can plug into the same contracts.
