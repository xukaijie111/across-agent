---
name: graph-chat-protocol-skill
description: >-
  Verifies apps/server/src/graph/ changes against docs/chat-protocol.md (SSE
  ChatEvent types, StreamRunner streamMode updates, getUiMessages rules, state
  concat reducer). Activates after editing graph/, chatEvents, streamRunner,
  or when asked to check chat protocol compliance.
license: MIT
metadata:
  author: CrossAgent
  version: 1.0.0
  created: 2026-06-04
  last_reviewed: 2026-06-04
  review_interval_days: 90
  dependencies:
    - url: file://docs/chat-protocol.md
      name: CrossAgent chat protocol
      type: documentation
---

# /graph-chat-protocol-skill — Graph ↔ Chat Protocol Compliance

You enforce alignment between **TypeScript graph layer** (`apps/server/src/graph/`)
and the canonical spec **`docs/chat-protocol.md`**. After any graph change, run the
bundled checker before claiming the work is done.

## Trigger

User invokes `/graph-chat-protocol-skill` or edits under `apps/server/src/graph/`:

```
/graph-chat-protocol-skill
/graph-chat-protocol-skill check my last change
/graph-chat-protocol-skill I changed streamRunner — is it still valid?
```

Also activate when the user mentions: chat protocol, SSE events, `ChatEvent`,
`getUiMessages`, `streamRunner`, graph compliance.

## When to run (mandatory)

1. **Immediately after** modifying any file under `apps/server/src/graph/`.
2. **Before** suggesting frontend protocol changes that depend on backend events.
3. **When reviewing** PRs that touch graph streaming or history projection.

## One command (repo root)

From the CrossAgent monorepo root (`python-less`):

```bash
python3 .cursor/skills/graph-chat-protocol-skill/scripts/run_pipeline.py
```

Or with an explicit root:

```bash
python3 scripts/run_pipeline.py --repo-root /path/to/python-less
```

Exit `0` = all invariant checks passed. Exit `1` = violations printed with doc section hints.

## Workflow for agents

1. Run `run_pipeline.py` (static invariants + optional `tsc` if `apps/server` exists).
2. If failures: open the cited file, read the matching section in `references/protocol-invariants.md`, fix code, re-run.
3. If the change is **intentional protocol evolution**: update `docs/chat-protocol.md` first, then update `references/protocol-invariants.md` and `scripts/check_graph_protocol.py` rules together — never silence checks without doc + rule updates.
4. Summarize for the user: pass/fail list, and whether SSE vs history alignment (§5 vs §4) is still a known gap per the doc.

## What the checker enforces

| Area | Protocol doc | Code |
|------|----------------|------|
| SSE event union | §4.2 | `chatEvents.ts` |
| SSE wire format | §4.1 | `index.ts` |
| Stream projection | §4.4 | `streamRunner.ts` `runTurn` |
| History projection | §5.4 | `streamRunner.ts` `getUiMessages` |
| Checkpoint reducer | §2.1 | `state.ts` |
| Graph topology | ReAct loop | `graph.ts`, `nodes.ts` |

**Not automated** (document-only / frontend): `ChatTurn` reducer (`apps/web`), Python `api-py` parity, proposed `toUiMessages` unification (§9.2). Flag these manually if the user changes related behavior.

## Optional: TypeScript build

When `apps/server/package.json` exists, the pipeline runs `npm run build` in `apps/server`.
Fix type errors before re-running the protocol checker.

## References (load on demand)

- `references/protocol-invariants.md` — machine-checked rules ↔ doc sections
- `references/troubleshooting.md` — common failures after edits
- `docs/chat-protocol.md` (repo) — human-readable source of truth

## Anti-goals

- Does not replace integration tests against a live LLM.
- Does not validate frontend `useAgentChat` unless the user asks separately.
- Does not auto-edit graph files; only reports violations.
