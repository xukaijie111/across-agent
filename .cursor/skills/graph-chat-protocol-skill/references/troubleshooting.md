# Troubleshooting

## Checker fails after renaming an event type

Update `chatEvents.ts`, `apps/web/src/lib/chat-protocol.ts`, and `docs/chat-protocol.md` together.
Add a matching `chat-event-*` rule in `check_graph_protocol.py`.

## `streamMode` removed or changed

§4.4 requires `stream_mode: "updates"`. Reverting to per-step `getState()` breaks the documented
streaming contract and will fail `stream-streamMode:-"updates"`.

## `getUiMessages` now returns tools

The doc (§5.4) currently **excludes** tools from history. Returning tools is a protocol change:
update §5, frontend `historyToTurns`, and add checker rules before merging.

## TypeScript build fails but protocol check passes

Run with pipeline only: `python3 scripts/run_pipeline.py --skip-tsc`, fix types, then full pipeline.

## False positive on doc rule `doc-documents stream mode`

Ensure `docs/chat-protocol.md` still mentions `stream_mode` or `streamMode` in §4.4.
