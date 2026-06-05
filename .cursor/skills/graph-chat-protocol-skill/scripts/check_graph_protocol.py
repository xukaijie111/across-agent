#!/usr/bin/env python3
"""
Static compliance checker: apps/server/src/graph/ vs docs/chat-protocol.md.

Usage:
    python3 scripts/check_graph_protocol.py --repo-root /path/to/python-less
    python3 scripts/check_graph_protocol.py --repo-root . --json

Exit codes:
    0 - all checks passed
    1 - one or more violations
    2 - missing repo paths
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Violation:
    rule_id: str
    message: str
    doc_section: str
    file: str


def _read(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _must_contain(
    text: str,
    needle: str,
    *,
    rule_id: str,
    doc_section: str,
    file: str,
    label: str | None = None,
) -> Violation | None:
    if needle not in text:
        return Violation(
            rule_id=rule_id,
            message=f"Expected {label or repr(needle)} in {file}",
            doc_section=doc_section,
            file=file,
        )
    return None


def _must_match(
    text: str,
    pattern: str,
    *,
    rule_id: str,
    doc_section: str,
    file: str,
    label: str,
) -> Violation | None:
    if not re.search(pattern, text, re.MULTILINE | re.DOTALL):
        return Violation(
            rule_id=rule_id,
            message=f"Pattern not found ({label}) in {file}",
            doc_section=doc_section,
            file=file,
        )
    return None


def check_chat_events(src: str, rel: str) -> list[Violation]:
    out: list[Violation] = []
    for event_type, section in [
        ("tool_start", "§4.2"),
        ("tool_end", "§4.2"),
        ("text", "§4.2"),
        ("done", "§4.2"),
        ("error", "§4.2"),
    ]:
        v = _must_contain(
            src,
            f'type: "{event_type}"',
            rule_id=f"chat-event-{event_type}",
            doc_section=section,
            file=rel,
            label=f'ChatEvent type "{event_type}"',
        )
        if v:
            out.append(v)

    for needle, label, section in [
        ("delta:", "text.delta", "§4.2"),
        ("format:", "text.format", "§4.2"),
        ("name:", "tool_start.name", "§4.2"),
        ("args:", "tool_start.args", "§4.2"),
        ("message:", "error.message", "§4.2"),
    ]:
        v = _must_contain(
            src,
            needle,
            rule_id=f"chat-event-field-{label}",
            doc_section=section,
            file=rel,
            label=label,
        )
        if v:
            out.append(v)
    return out


def check_state(src: str, rel: str) -> list[Violation]:
    out: list[Violation] = []
    v = _must_match(
        src,
        r"reducer:\s*\([^)]*\)\s*=>\s*left\.concat\(right\)",
        rule_id="state-messages-concat",
        doc_section="§2.1",
        file=rel,
        label="messages concat reducer",
    )
    if v:
        out.append(v)
    v = _must_contain(
        src,
        "Annotation<ChatMessage[]>",
        rule_id="state-messages-annotation",
        doc_section="§2.1",
        file=rel,
        label="AgentState.messages annotation",
    )
    if v:
        out.append(v)
    return out


def check_stream_runner(src: str, rel: str) -> list[Violation]:
    out: list[Violation] = []
    checks = [
        ('streamMode: "updates"', "streamMode updates (not getState-per-step)", "§4.4"),
        ("toolStartEvent", "yield tool_start from agent updates", "§4.4"),
        ("toolEndEvent", "yield tool_end from tools updates", "§4.4"),
        ("textEvent", "yield text events", "§4.4"),
        ("doneEvent", "yield done at end of turn", "§4.4"),
        ("getUiMessages", "history API projection helper", "§5.2"),
        ('msg.role === "user"', "getUiMessages keeps user messages", "§5.4"),
        ("tool_calls", "getUiMessages skips assistant with tool_calls", "§5.4"),
        ("onTextDelta", "LLM token stream → text deltas", "§4.2–4.4"),
        ("textEvent(delta)", "emit text SSE on each LLM token", "§4.4"),
    ]
    for needle, label, section in checks:
        v = _must_contain(
            src,
            needle,
            rule_id=f"stream-{needle.replace(' ', '-')[:40]}",
            doc_section=section,
            file=rel,
            label=label,
        )
        if v:
            out.append(v)

    v = _must_match(
        src,
        r'if\s*\(\s*"agent"\s+in\s+update\s*\)',
        rule_id="stream-agent-branch",
        doc_section="§4.4",
        file=rel,
        label='handle "agent" in stream updates',
    )
    if v:
        out.append(v)

    v = _must_match(
        src,
        r'if\s*\(\s*"tools"\s+in\s+update\s*\)',
        rule_id="stream-tools-branch",
        doc_section="§4.4",
        file=rel,
        label='handle "tools" in stream updates',
    )
    if v:
        out.append(v)

    v = _must_match(
        src,
        r"format:\s*\"plain\"",
        rule_id="history-user-plain",
        doc_section="§5.3",
        file=rel,
        label='user history format "plain"',
    )
    if v:
        out.append(v)

    v = _must_match(
        src,
        r"format:\s*\"markdown\"",
        rule_id="history-assistant-markdown",
        doc_section="§5.3",
        file=rel,
        label='assistant history format "markdown"',
    )
    if v:
        out.append(v)
    return out


def check_graph(src: str, rel: str) -> list[Violation]:
    out: list[Violation] = []
    for needle, label in [
        ('addNode("agent"', "agent node"),
        ('addNode("tools"', "tools node"),
        ("routeAfterAgent", "conditional route after agent"),
        ('addEdge("tools", "agent")', "tools → agent loop"),
    ]:
        v = _must_contain(
            src,
            needle,
            rule_id=f"graph-{label.replace(' ', '-')}",
            doc_section="ReAct §2.3 / graph",
            file=rel,
            label=label,
        )
        if v:
            out.append(v)
    return out


def check_nodes(src: str, rel: str) -> list[Violation]:
    out: list[Violation] = []
    for needle, label in [
        ("stream: true", "OpenAI streaming completions"),
        ("tool_call_id", "tool messages with tool_call_id"),
        ('role: "tool"', "tool role messages"),
        ("routeAfterAgent", "route to tools or end"),
    ]:
        v = _must_contain(
            src,
            needle,
            rule_id=f"nodes-{label.replace(' ', '-')}",
            doc_section="§2.2 / nodes",
            file=rel,
            label=label,
        )
        if v:
            out.append(v)
    return out


def check_index(src: str, rel: str) -> list[Violation]:
    out: list[Violation] = []
    checks = [
        ('event: chat', "SSE event name chat", "§4.1"),
        ('"event: chat"', "SSE event line", "§4.1"),
        ('JSON.stringify(event)', "SSE data JSON payload", "§4.1"),
        ('"/chat/stream"', "POST /chat/stream", "§3"),
        ('"/session/histroy"', "POST /session/histroy (typo preserved)", "§3"),
        ("session_id", "request body session_id", "§3"),
        ("getUiMessages", "history uses getUiMessages", "§5.2"),
        ("defaultStreamRunner", "stream runner singleton", "§4.4"),
        ("errorEvent", "SSE error events", "§4.2"),
    ]
    for needle, label, section in checks:
        v = _must_contain(
            src,
            needle,
            rule_id=f"api-{needle[:30]}",
            doc_section=section,
            file=rel,
            label=label,
        )
        if v:
            out.append(v)
    return out


def check_protocol_doc(doc: str, rel: str) -> list[Violation]:
    """Doc must still describe files the checker watches."""
    out: list[Violation] = []
    for needle, label in [
        ("chatEvents.ts", "documents chatEvents.ts"),
        ("streamRunner.ts", "documents streamRunner.ts"),
        ("tool_start", "documents tool_start event"),
        ("getUiMessages", "documents getUiMessages"),
        ("stream_mode", "documents stream mode (or streamMode)"),
    ]:
        v = _must_contain(
            doc,
            needle,
            rule_id=f"doc-{label.replace(' ', '-')}",
            doc_section="doc integrity",
            file=rel,
            label=label,
        )
        if v:
            out.append(v)
    return out


def run_checks(repo_root: Path) -> list[Violation]:
    graph_dir = repo_root / "apps/server/src/graph"
    doc_path = repo_root / "docs/chat-protocol.md"
    index_path = repo_root / "apps/server/src/index.ts"

    if not graph_dir.is_dir():
        raise FileNotFoundError(f"Graph directory not found: {graph_dir}")
    if not doc_path.is_file():
        raise FileNotFoundError(f"Protocol doc not found: {doc_path}")

    violations: list[Violation] = []
    violations.extend(check_protocol_doc(_read(doc_path), str(doc_path.relative_to(repo_root))))

    files = {
        "apps/server/src/graph/chatEvents.ts": check_chat_events,
        "apps/server/src/graph/state.ts": check_state,
        "apps/server/src/graph/streamRunner.ts": check_stream_runner,
        "apps/server/src/graph/graph.ts": check_graph,
        "apps/server/src/graph/nodes.ts": check_nodes,
    }
    for rel, fn in files.items():
        path = repo_root / rel
        if not path.is_file():
            violations.append(
                Violation(
                    rule_id="missing-file",
                    message=f"Required file missing: {rel}",
                    doc_section="code map table",
                    file=rel,
                )
            )
            continue
        violations.extend(fn(_read(path), rel))

    if index_path.is_file():
        violations.extend(
            check_index(_read(index_path), str(index_path.relative_to(repo_root)))
        )
    else:
        violations.append(
            Violation(
                rule_id="missing-index",
                message="apps/server/src/index.ts not found",
                doc_section="§3",
                file="apps/server/src/index.ts",
            )
        )

    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Check graph/ vs chat-protocol.md")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="CrossAgent monorepo root (default: cwd)",
    )
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()

    try:
        violations = run_checks(repo_root)
    except FileNotFoundError as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}))
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(
            json.dumps(
                {
                    "ok": len(violations) == 0,
                    "repo_root": str(repo_root),
                    "violations": [
                        {
                            "rule_id": v.rule_id,
                            "message": v.message,
                            "doc_section": v.doc_section,
                            "file": v.file,
                        }
                        for v in violations
                    ],
                },
                indent=2,
            )
        )
    elif violations:
        print(f"FAIL: {len(violations)} chat-protocol violation(s)\n")
        for v in violations:
            print(f"  [{v.rule_id}] {v.file}")
            print(f"    {v.message}")
            print(f"    See docs/chat-protocol.md {v.doc_section}\n")
    else:
        print(f"OK: graph layer matches docs/chat-protocol.md ({repo_root})")

    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
