"""
Context 工程：
- analyze：发送前看 messages 里有什么（按 role 统计）
- trim：发送前裁剪，防止 history / tool 结果过长
- 发送后用 resp.usage 看真实 token（在 agent_loop 里打）
"""

MAX_TOOL_CONTENT_CHARS = 2000
KEEP_LAST_MESSAGES = 12


def message_chars(msg: dict) -> int:
    n = len(msg.get("content") or "")
    for tc in msg.get("tool_calls") or []:
        fn = tc.get("function") or {}
        n += len(fn.get("name") or "")
        n += len(fn.get("arguments") or "")
    return n


def analyze_messages(messages: list[dict]) -> dict:
    by_role: dict[str, dict] = {}
    for msg in messages:
        role = msg.get("role", "unknown")
        if role not in by_role:
            by_role[role] = {"count": 0, "chars": 0}
        by_role[role]["count"] += 1
        by_role[role]["chars"] += message_chars(msg)
    return {
        "total_messages": len(messages),
        "total_chars": sum(message_chars(m) for m in messages),
        "by_role": by_role,
    }


def format_analysis(analysis: dict) -> str:
    lines = [
        f"messages={analysis['total_messages']}, chars≈{analysis['total_chars']}",
    ]
    for role, data in analysis["by_role"].items():
        lines.append(f"  {role}: count={data['count']}, chars={data['chars']}")
    return "\n".join(lines)


def truncate_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    half = max_chars // 2 - 24
    left = text[:half]
    right = text[-half:]
    return f"{left}\n... [truncated, total {len(text)} chars] ...\n{right}"


def shrink_tool_content(content: str) -> str:
    if not content:
        return content
    lower = content.lower()
    if any(k in lower for k in ("error", "fail", "✗")):
        lines = content.splitlines()
        picked: list[str] = []
        picked.extend(lines[:5])
        for line in lines:
            if any(k in line.lower() for k in ("error", "fail", "✗")):
                picked.append(line)
        picked.extend(lines[-5:])
        seen: set[str] = set()
        unique: list[str] = []
        for line in picked:
            if line not in seen:
                seen.add(line)
                unique.append(line)
        return truncate_text("\n".join(unique), MAX_TOOL_CONTENT_CHARS)
    return truncate_text(content, MAX_TOOL_CONTENT_CHARS)


def _copy_and_shrink_tools(messages: list[dict]) -> list[dict]:
    out: list[dict] = []
    for msg in messages:
        m = msg.copy()
        if m.get("role") == "tool" and isinstance(m.get("content"), str):
            m["content"] = shrink_tool_content(m["content"])
        out.append(m)
    return out


def trim_messages(messages: list[dict]) -> list[dict]:
    if not messages:
        return []
    system_msgs = [m for m in messages if m.get("role") == "system"]
    rest_msgs = [m for m in messages if m.get("role") != "system"]
    if len(rest_msgs) > KEEP_LAST_MESSAGES:
        rest_msgs = rest_msgs[-KEEP_LAST_MESSAGES:]
    return system_msgs + _copy_and_shrink_tools(rest_msgs)
