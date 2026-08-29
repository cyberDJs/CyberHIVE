# Patch 013 — Node Agent & Action Dispatch MVP

## Purpose

Add a typed node-side action boundary between approved orchestration/execution
plans and node-local side effects.

## Adds

- `NodeDescriptor`
- `LocalNodeAgent`
- `NodeAgentRegistry`
- `NodeActionDispatcher`
- typed action requests/results
- node-local policy gates
- dry-run action dispatch
- live prewarm recording after approval token
- safe data-move intent dispatch without physical file movement
- schema, docs, ADR, validation, demo and tests

## Safety properties

The MVP does not:

- run arbitrary shell commands,
- SSH into nodes,
- perform physical data moves,
- mutate external services,
- bypass Policy/Approval gates.

It records structured action results and gives future real executors a narrow,
auditable interface.
