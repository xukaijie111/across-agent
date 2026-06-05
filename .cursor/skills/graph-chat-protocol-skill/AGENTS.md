# Graph Chat Protocol Skill

## Purpose

Keep `apps/server/src/graph/` aligned with `docs/chat-protocol.md` after every change.

## Activation

- User types `/graph-chat-protocol-skill`
- User edited `apps/server/src/graph/*.ts`
- User asks whether SSE / history / `ChatEvent` still match the protocol doc

## Usage

From repository root:

```bash
python3 .cursor/skills/graph-chat-protocol-skill/scripts/run_pipeline.py
```

Read full workflow, invariant table, and anti-goals in `SKILL.md`.

## Maintainer

When the protocol doc changes, update `references/protocol-invariants.md` and
`scripts/check_graph_protocol.py` in the same PR as `docs/chat-protocol.md`.
