# Protocol invariants (machine-checked)

Source of truth: `docs/chat-protocol.md`. Checker: `scripts/check_graph_protocol.py`.

## chatEvents.ts — §4.2

| rule_id | Requirement |
|---------|-------------|
| chat-event-* | Union includes `tool_start`, `tool_end`, `text`, `done`, `error` |
| chat-event-field-* | `text` has `delta` + `format`; tools have `id`, `name`, `args`; `error` has `message` |

## state.ts — §2.1

| rule_id | Requirement |
|---------|-------------|
| state-messages-concat | `messages` reducer appends via `left.concat(right)` |
| state-messages-annotation | Typed as `Annotation<ChatMessage[]>` |

## streamRunner.ts — §4.4, §5.4

| rule_id | Requirement |
|---------|-------------|
| stream-* | `streamMode: "updates"`; branches on `"agent"` / `"tools"` |
| stream-* | Emits `toolStartEvent`, `toolEndEvent`, `textEvent`, `doneEvent` |
| stream-* | `onTextDelta` immediately `emit(textEvent(delta))` per LLM token |
| history-* | `getUiMessages` keeps `user`, assistant without `tool_calls`, sets `plain` / `markdown` |

## graph.ts — ReAct topology

| rule_id | Requirement |
|---------|-------------|
| graph-* | Nodes `agent`, `tools`; `routeAfterAgent`; edge `tools → agent` |

## nodes.ts — §2.2

| rule_id | Requirement |
|---------|-------------|
| nodes-* | Streaming LLM; tool messages with `tool_call_id`; `routeAfterAgent` |

## index.ts — §3, §4.1, §5.2

| rule_id | Requirement |
|---------|-------------|
| api-* | SSE `event: chat` + JSON `data`; routes `/chat/stream`, `/session/histroy` |
| api-* | History via `getUiMessages`; errors via `errorEvent` |

## Intentional gaps (not checked)

- SSE vs history rule unification (§9.1–9.2)
- `toUiMessages` helper (proposed, not implemented)
- Frontend `ChatTurn` / `applyChatEventToTurn` (§6–7)
- Python backend parity (`make api-py`)

When implementing §9.2, add rules here and in the checker in the same change as the code.
