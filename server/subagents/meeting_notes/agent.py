"""
Meeting Notes Agent — 会议文字稿 → 结构化 JSON → Markdown 纪要。

Usage:
    python agent.py
    python agent.py --text "张三：我们下周发布..."
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage

SERVER_ROOT = Path(__file__).resolve().parents[2]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from llm_config import make_chat_llm

PROJECT_ROOT = SERVER_ROOT.parent
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(SERVER_ROOT / ".env")

NOTES_PROMPT = """你是专业会议纪要助手。将会议文字稿整理为 JSON，字段如下：
{
  "meeting_title": "推断的会议主题",
  "date": "今天或稿中提到的日期",
  "participants": ["姓名1", "姓名2"],
  "duration_estimate": "约 X 分钟",
  "summary": "2-3 句执行摘要",
  "key_decisions": ["决策1", "决策2"],
  "action_items": [
    {"task": "任务描述", "owner": "负责人或待定", "due": "日期/时间或待定"}
  ],
  "discussion_topics": ["议题1", "议题2"],
  "blockers": ["阻塞项，无则空数组"],
  "next_meeting": "下次会议时间或待定",
  "follow_up_questions": ["待澄清问题"]
}

要求：
- 所有文本字段使用简体中文
- 只输出一行 JSON，不要 markdown 代码块
- 从文字稿中提取事实，不要编造未提及的内容"""

SAMPLE_TRANSCRIPT = """
小王：大家早上好，今天讨论 Q4 客服系统上线计划。参会人有小李、小陈和我。

小李：支付模块联调还差退款回调，预计 11 月 10 日前完成。

小陈：知识库 FAQ 已更新，但 RAG 检索还要补测。

小王：那决策是：11 月 15 日功能冻结，社交登录本版不做，放到 Q1。

小李：我负责 11 月 8 日前把退款流程文档发给测试。

小陈：我从 11 月 9 日开始做回归测试。

小王：阻塞项是支付服务商 API 文档还没回复，我今天去催。下次会议 11 月 10 日同一时间。
"""

_HINT_REPLY = (
    "请直接粘贴会议文字稿（发言记录、逐字稿均可），我会生成结构化纪要，包含："
    "摘要、关键决策、待办、阻塞项等。\n\n"
    "示例格式：\n"
    "张三：我们先对齐发布日期…\n"
    "李四：我这边开发进度…"
)

_GREETINGS = frozenset({"你好", "您好", "hi", "hello", "嗨", "在吗"})


def _needs_hint(message: str) -> bool:
    text = message.strip()
    if not text:
        return True
    if text.lower() in _GREETINGS or text in _GREETINGS:
        return True
    return len(text) < 40


def parse_json_response(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)
    return json.loads(cleaned)


def generate_meeting_notes(transcript: str) -> dict:
    llm = make_chat_llm(temperature=0)
    messages = [
        SystemMessage(content=NOTES_PROMPT),
        HumanMessage(content=f"会议文字稿：\n\n{transcript}"),
    ]
    response = llm.invoke(messages)
    content = response.content if isinstance(response.content, str) else str(response.content)
    return parse_json_response(content)


def format_notes(notes: dict) -> str:
    participants = notes.get("participants") or []
    lines = [
        f"# {notes.get('meeting_title', '会议纪要')}",
        f"**日期：** {notes.get('date', date.today().isoformat())}  |  **时长：** {notes.get('duration_estimate', '未知')}",
        f"**参会人：** {', '.join(participants) if participants else '未提及'}",
        "",
        "## 摘要",
        notes.get("summary", ""),
        "",
        "## 关键决策",
        *[f"- {d}" for d in notes.get("key_decisions", [])],
        "",
        "## 待办事项",
    ]
    for item in notes.get("action_items", []):
        lines.append(
            f"- [ ] **{item.get('task', '任务')}** — 负责人：{item.get('owner', '待定')} | 截止：{item.get('due', '待定')}"
        )

    topics = notes.get("discussion_topics") or []
    if topics:
        lines += ["", "## 讨论议题", *[f"- {t}" for t in topics]]

    blockers = notes.get("blockers") or []
    if blockers:
        lines += ["", "## 阻塞项", *[f"- {b}" for b in blockers]]

    follow_ups = notes.get("follow_up_questions") or []
    if follow_ups:
        lines += ["", "## 待澄清问题", *[f"- {q}" for q in follow_ups]]

    next_meeting = notes.get("next_meeting")
    if next_meeting and next_meeting != "待定":
        lines += ["", f"**下次会议：** {next_meeting}"]

    return "\n".join(lines)


def run_turn(thread_id: str, message: str) -> dict:
    _ = thread_id
    if _needs_hint(message):
        return {"status": "complete", "response": _HINT_REPLY, "interrupt": None}

    notes = generate_meeting_notes(message)
    return {"status": "complete", "response": format_notes(notes), "interrupt": None}


def new_state() -> dict:
    return {"awaiting_resume": False, "interrupt": None, "thread_id": ""}


def main() -> None:
    parser = argparse.ArgumentParser(description="Meeting Notes Agent")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--transcript", help="会议文字稿文件路径")
    group.add_argument("--text", help="直接传入文字稿")
    args = parser.parse_args()

    if args.transcript:
        transcript = Path(args.transcript).read_text(encoding="utf-8")
    elif args.text:
        transcript = args.text
    else:
        print("使用示例文字稿…\n")
        transcript = SAMPLE_TRANSCRIPT

    result = run_turn("cli", transcript)
    print(result["response"])


if __name__ == "__main__":
    main()
