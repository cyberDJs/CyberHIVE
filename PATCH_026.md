# PATCH_026 — Codex Alias Validation P1 Repair

## Scope

Fixes the fresh Codex P1 finding from the Block G re-review:

- `src/cyberhive_core/node_reconciliation.py` must validate every supplied correlation alias before accepting a matching task record.

## Problem

A forged receipt from node A could include both:

- a valid node A `delivery_id`, and
- a victim node B alias, for example `request_id`.

The reconciler accepted the first matching record before checking the later conflicting alias. When the accepted action result was indexed, the victim alias could be mapped to node A's record and block later reconciliation for node B.

## Fix

`_find_or_orphan` now scans all supplied candidate aliases before returning a matched record. It returns the matched record only when no supplied alias conflicts with another known record or with the authenticated node/session boundary. If a conflict exists, the receipt becomes an orphan and all supplied aliases are marked untrusted so `_index_record` cannot poison existing alias ownership.

## Regression coverage

Adds a regression test where node A submits a receipt containing its own valid `delivery_id` plus node B's `request_id`. The forged receipt becomes orphaned, neither original task mutates, and node B can still reconcile its legitimate result later.

## Safety

No merge, deploy, shell execution, privilege escalation, secret handling, force-push, or production access is introduced.
