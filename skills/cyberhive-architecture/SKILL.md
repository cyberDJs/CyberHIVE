---
name: cyberhive-architecture
description: Design and review CyberHIVE architecture, system boundaries, ADRs, deployment topology, security trade-offs and performance implications. Use when a CyberHIVE feature or technical problem requires an architectural decision, component boundary, protocol choice, topology, ADR, threat-impact review or comparison of implementation approaches. Prefer the simplest local-first design that remains secure, measurable and replaceable.
---

# CyberHIVE Architecture

Read the current project context and relevant architecture/security documents before deciding.

## Workflow

1. Restate the decision and constraints in one short section.
2. Separate verified facts from assumptions.
3. Recommend one primary design before alternatives.
4. Check impact on local-first operation, offline behavior, security boundaries, RTX-class resource constraints, upgrade/recovery and operator complexity.
5. Reject added distributed systems, databases or orchestration layers unless the benefit is measurable.
6. Produce an ADR when the decision is durable or changes a public/security boundary.
7. End with concrete verification criteria and unresolved risks.
