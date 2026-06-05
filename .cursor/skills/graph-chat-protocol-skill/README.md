# graph-chat-protocol-skill

Verify `apps/server/src/graph/` against `docs/chat-protocol.md` after each change.

## Install (Cursor — this repo)

Already at `.cursor/skills/graph-chat-protocol-skill`. In chat:

```
/graph-chat-protocol-skill
```

## Run

From monorepo root:

```bash
python3 .cursor/skills/graph-chat-protocol-skill/scripts/run_pipeline.py
```

Skip TypeScript build:

```bash
python3 .cursor/skills/graph-chat-protocol-skill/scripts/run_pipeline.py --skip-tsc
```

## Evals

```bash
cd .cursor/skills/graph-chat-protocol-skill
python3 scripts/run_evals.py --validate
python3 scripts/run_evals.py
```

## Other platforms

```bash
./install.sh --platform cursor   # project .cursor/skills/
./install.sh --all
```

## Agent workflow

After editing any file under `apps/server/src/graph/`, run the pipeline before marking the task complete. If the protocol doc changes, update `references/protocol-invariants.md` and `scripts/check_graph_protocol.py` in the same PR.
