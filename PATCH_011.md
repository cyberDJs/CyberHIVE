# Patch 011 — Policy & Governance MVP

## Purpose

Patch 011 adds a deterministic policy guard above orchestration and execution.
Patch 010 created auditable execution runs. This patch adds the layer that
answers: **is this plan allowed, does it need approval, or must it be denied?**

## Added

- `PolicyGuard`
- `PolicyContext`
- `PolicyDecision`
- `PolicyFinding`
- `GovernanceJournal`
- approval tokens for live execution, data moves, prewarm and exposure
- orchestration-plan policy evaluation
- exposure-request policy evaluation
- policy decision JSON schema
- validation script
- demo script
- unit tests
- ADR `ADR-0013-policy-governance-mvp.md`

## Behavior

The MVP policy layer:

1. allows dry-run plans by default,
2. requires approval for live execution,
3. requires approval for physical data moves,
4. requires approval for prewarm side effects,
5. denies rejected routes unless explicitly overridden,
6. denies secret exposure,
7. requires explicit approval for public exposure, recording and download,
8. writes auditable policy decisions to optional JSONL governance journal.

## Validation

```bash
PYTHONPATH=src python3 scripts/validate_policy_governance_mvp.py
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 scripts/demo_policy_governance.py
```
