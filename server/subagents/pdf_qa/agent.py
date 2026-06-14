"""
PDF / Document Q&A Agent — 文档 RAG + 多轮问答。

改编自 500-AI-Agents-Projects 03-pdf-qa-agent；Playground 使用内置示例文档，
无需上传 PDF。CLI 可选 --text 指定本地文本/Markdown 文件。

Usage:
    python agent.py
    python agent.py --question "试用期多长？"
    python agent.py --text path/to/doc.txt
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter

SERVER_ROOT = Path(__file__).resolve().parents[2]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from llm_config import make_chat_llm, make_embeddings

PROJECT_ROOT = SERVER_ROOT.parent
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(SERVER_ROOT / ".env")

SAMPLE_DOC = """
《家里蹲科技员工手册（2024 版）》摘要

一、公司简介
家里蹲科技成立于 2018 年，主营企业级 SaaS 与 AI 解决方案，总部设在上海，在北京、深圳设有分公司。
主要产品包括：家里蹲 CRM、家里蹲工单、家里蹲知识库。

二、工作时间与考勤
标准工作时间为周一至周五 9:30–18:30，午休 12:00–13:30。
弹性打卡：允许 9:30–10:00 到岗，对应延迟下班；每月弹性迟到不超过 3 次。
远程办公：需提前在 OA 申请，直属主管审批；每周远程不超过 2 天。
年假：工龄满 1 年享 5 天，满 3 年 10 天，满 5 年 15 天；当年未休可顺延至次年 3 月 31 日前。

三、薪酬与福利
发薪日：每月 10 日发放上月工资，遇节假日提前。
五险一金：按上海市标准缴纳，公积金比例 12%（公司+个人各 12%）。
餐补：工作日 30 元/天，随工资发放。
体检：正式员工每年一次集体体检，家属可自费加项。
股票期权：司龄满 2 年且绩效 B 及以上可参与期权计划，具体以董事会公告为准。

四、试用期与转正
试用期：劳动合同 3 年及以上者为 6 个月，1–3 年者为 3 个月。
试用期工资不低于转正工资的 80%。
转正条件：试用期满前 15 天提交转正申请，直属主管与 HR 联合评估；绩效需达到 B 及以上。
未通过转正：可延长试用期 1 个月（最多一次）或依法解除劳动合同。

五、请假制度
病假：需提交二级及以上医院证明；3 天以内向主管报备，3 天以上需 HR 备案。
事假：提前 1 个工作日申请；事假期间不计薪。
婚假：依法 10 天，需结婚证复印件。
产假：按国家及上海市规定执行，女员工 158 天起；陪产假 10 天。

六、信息安全与保密
员工须签署保密协议（NDA），不得泄露客户数据、源代码、财务信息。
开发环境代码禁止下载至个人设备；生产数据库访问需 VPN + 双因素认证。
违反保密义务可导致立即解雇并追究法律责任。

七、报销与差旅
差旅需提前在 OA 提交申请；机票由行政统一预订，酒店标准一线城市 500 元/晚、其他城市 350 元/晚。
报销周期：费用发生后 30 日内提交，逾期需书面说明。
客户招待费单次超过 2000 元需 VP 审批。

八、离职与交接
正式员工辞职需提前 30 天书面通知；试用期提前 3 天。
离职交接清单包括：设备归还、账号注销、文档移交、项目 handover，由 HR 与主管双方签字确认。
竞业限制：部分岗位可能适用，补偿与期限见单独协议。

九、常见问题
Q：能否兼职？A：需申报 HR，不得从事与本公司有竞争关系的业务。
Q：内推奖励？A：成功入职并转正后，推荐人可获得 3000–8000 元奖励，视岗位级别而定。
Q：培训预算？A：每人每年 5000 元学习额度，可用于课程、会议、认证考试。
"""

SYSTEM_PROMPT = """你是「文档问答」助手，根据检索到的文档片段回答用户问题。

要求：
- 仅依据文档内容作答，不要编造文档中不存在的信息
- 使用简体中文，回答简洁清楚
- 文档未提及或无法确定时，明确说「文档中未找到相关信息」
- 支持多轮对话，结合上下文理解追问

相关文档片段：
{context}"""

_HINT_REPLY = (
    "我是文档问答助手，当前基于内置《家里蹲科技员工手册》示例文档。\n\n"
    "你可以直接提问，例如：\n"
    "· 试用期多长？转正条件是什么？\n"
    "· 年假有多少天？\n"
    "· 远程办公有什么规定？\n\n"
    "我会仅根据文档内容回答，并支持多轮追问。"
)

_GREETINGS = frozenset({"你好", "您好", "hi", "hello", "嗨", "在吗"})

_BUILTIN_DOC_REVISION = "jialidun-2024-v1"

_vectorstore: FAISS | None = None
_doc_source = "builtin"
_index_revision: str | None = None


def _needs_hint(message: str) -> bool:
    text = message.strip()
    if not text:
        return True
    lower = text.lower()
    return lower in _GREETINGS or text in _GREETINGS


def _split_documents(text: str) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=80)
    return splitter.split_documents([Document(page_content=text.strip())])


def build_index(doc_text: str) -> FAISS:
    global _vectorstore, _doc_source, _index_revision
    docs = _split_documents(doc_text)
    embeddings = make_embeddings()
    _vectorstore = FAISS.from_documents(docs, embeddings)
    _doc_source = "custom"
    _index_revision = None
    return _vectorstore


def get_vectorstore() -> FAISS:
    global _vectorstore, _doc_source, _index_revision
    stale = _vectorstore is None or (
        _doc_source == "builtin" and _index_revision != _BUILTIN_DOC_REVISION
    )
    if stale:
        docs = _split_documents(SAMPLE_DOC)
        embeddings = make_embeddings()
        _vectorstore = FAISS.from_documents(docs, embeddings)
        _index_revision = _BUILTIN_DOC_REVISION
        _doc_source = "builtin"
    return _vectorstore


def _retrieve(query: str, k: int = 4) -> str:
    store = get_vectorstore()
    hits = store.similarity_search(query, k=k)
    if not hits:
        return "（未检索到相关片段）"
    return "\n\n---\n\n".join(d.page_content for d in hits)


def _to_langchain_messages(history: list[dict[str, str]], context: str) -> list:
    items: list = [SystemMessage(content=SYSTEM_PROMPT.format(context=context))]
    for msg in history:
        if msg["role"] == "user":
            items.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            items.append(AIMessage(content=msg["content"]))
    return items


def new_state() -> dict[str, Any]:
    return {"messages": [], "awaiting_resume": False, "interrupt": None}


def run_turn(state: dict[str, Any], message: str) -> str:
    history = state.get("messages", [])
    if _needs_hint(message):
        state["messages"] = [
            *history,
            {"role": "user", "content": message},
            {"role": "assistant", "content": _HINT_REPLY},
        ]
        return _HINT_REPLY

    context = _retrieve(message)
    llm = make_chat_llm(temperature=0)
    messages = [
        *_to_langchain_messages(history, context),
        HumanMessage(content=message),
    ]
    response = llm.invoke(messages)
    text = response.content if isinstance(response.content, str) else str(response.content)
    text = text.strip() or "抱歉，我未能从文档中找到合适答案。"

    state["messages"] = [
        *history,
        {"role": "user", "content": message},
        {"role": "assistant", "content": text},
    ]
    return text


def main() -> None:
    parser = argparse.ArgumentParser(description="Document Q&A Agent")
    parser.add_argument("--text", help="本地文本/Markdown 文件路径（默认使用内置示例文档）")
    parser.add_argument("--question", help="单次提问（省略则进入交互模式）")
    args = parser.parse_args()

    if args.text:
        doc = Path(args.text).read_text(encoding="utf-8")
        build_index(doc)
        print(f"已索引自定义文档：{args.text}\n")
    else:
        get_vectorstore()
        print("已加载内置《家里蹲科技员工手册》示例文档\n")

    if args.question:
        state = new_state()
        print(run_turn(state, args.question))
        return

    print("文档问答就绪，输入 quit 退出。\n")
    state = new_state()
    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if question.lower() in ("quit", "exit", "q"):
            break
        if not question:
            continue
        print(f"\nAgent: {run_turn(state, question)}\n")


if __name__ == "__main__":
    main()
