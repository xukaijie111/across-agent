# Eval — graph-chat-protocol-skill

Binary checks for the static protocol checker against this monorepo and a bundled broken fixture.

## Criteria

1. **spec-valid** — eval spec parses and references exist
2. **monorepo-passes** — checker exits 0 on CrossAgent repo root
3. **broken-fixture-fails** — checker exits non-zero on bundled violating mini-repo
4. **pipeline-passes** — full run_pipeline (protocol only, skip tsc) exits 0 on monorepo

## Golden cases

- `monorepo-current` — real repo path (see `golden/monorepo/repo_root.txt`)
- `broken-mini` — minimal tree missing `done` event
- `pipeline-smoke` — same repo, exercises orchestrator

```json
{
  "skill": "graph-chat-protocol-skill",
  "run": "python3 scripts/check_graph_protocol.py --repo-root $(cat {input}) > {output} 2>&1; test $? -eq 0",
  "criteria": [
    {
      "id": "spec-valid",
      "text": "Eval spec validates",
      "type": "command",
      "cmd": "python3 scripts/run_evals.py --validate"
    },
    {
      "id": "monorepo-passes",
      "text": "Checker passes on monorepo",
      "type": "command",
      "cmd": "python3 scripts/check_graph_protocol.py --repo-root $(cat evals/golden/monorepo/repo_root.txt)"
    },
    {
      "id": "broken-fixture-fails",
      "text": "Checker fails on broken fixture",
      "type": "command",
      "cmd": "python3 scripts/check_graph_protocol.py --repo-root evals/golden/broken-mini >/dev/null 2>&1; test $? -ne 0"
    },
    {
      "id": "pipeline-passes",
      "text": "Pipeline passes with --skip-tsc",
      "type": "command",
      "cmd": "python3 scripts/run_pipeline.py --repo-root $(cat evals/golden/monorepo/repo_root.txt) --skip-tsc"
    }
  ],
  "golden": [
    {
      "id": "monorepo-current",
      "input": "golden/monorepo/repo_root.txt",
      "expected": "golden/monorepo/expected.ok",
      "split": "val"
    },
    {
      "id": "broken-mini",
      "input": "golden/broken-mini/repo_root.txt",
      "expected": "golden/broken-mini/expected.fail",
      "split": "val"
    },
    {
      "id": "pipeline-smoke",
      "input": "golden/monorepo/repo_root.txt",
      "expected": "golden/monorepo/expected.ok",
      "split": "val"
    }
  ]
}
```
