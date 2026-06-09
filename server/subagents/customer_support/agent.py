"""
Customer Support Agent using LangGraph with RAG + HITL interrupt.

Handles customer queries using a knowledge base (product docs).
When user explicitly requests return/refund, LLM calls a confirmation tool
and the graph interrupts until the user confirms or cancels.

Usage:
    python agent.py
    python agent.py --kb-dir docs/
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Annotated, Literal, TypedDict

from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from llm_config import make_chat_llm, make_embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from checkpoint_store import get_checkpointer
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import Command, interrupt

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")

BRAND_NAME = "衣汇商城"

RETURN_ADDRESS = """退货地址：上海市浦东新区张江路 88 号 衣汇商城退货仓
收件人：退货组  电话：400-123-4567
请随包裹附上订单号，保持吊牌完整、未洗涤。"""

SAMPLE_KB = [
    "店铺介绍：衣汇商城主营女装、男装及配饰，涵盖通勤、休闲、运动等风格。贴身内衣、袜子、定制款不支持七天无理由退换。",
    "商品规格：每款商品按颜色、尺码等规格分别售卖，不同规格库存与价格可能不同。下单前请在商品页点选具体规格，未选规格无法提交订单。",
    "颜色规格：颜色名称以商品详情页标注为准（如藏青、米白、碎花）。因拍摄光线与显示器差异，实物颜色可能略有色差，不属于质量问题。",
    "尺码规格：请对照详情页尺码表选择 S/M/L/XL 或数字码。介于两码之间建议选大一码；弹力面料可按日常尺码选。童装、裤装请重点看腰围、裤长、衣长数据。",
    "缺货与规格变更：某颜色或尺码显示「缺货」或灰色不可选时表示无库存。发货前可联系客服改规格；发货后需走换货流程，且目标规格需有货。",
    "换货与退换：签收 7 天内吊牌完整、未洗涤可申请退换或换规格（换颜色/换尺码）。退款原路返回，一般 3～7 个工作日到账。可在订单页提交申请并选择原因。",
    "退款与纠纷：用户提及退款、投诉、质量问题时，先了解订单情况与具体诉求，按退换货政策分步说明所需条件与操作路径；需要订单号或照片时再向用户索取。",
    "发错货与物流异常：发错规格/颜色或包裹长时间未更新时，请用户提供订单号，说明当前可协助登记核实，按换货或补发流程处理。",
    "配送说明：下单后 48 小时内发货，江浙沪 1～2 天送达，其他地区 3～5 天。运费以结算页显示为准。",
    "支付方式：支持微信、支付宝、银联，以结算页可选方式为准。",
    "洗护说明：羊毛羊绒建议手洗或干洗；深色衣物首次单独冷水洗涤；熨烫参照吊牌温度标识。",
    "常见问题：物流未更新先等 24 小时；改地址仅限发货前；下单后规格以订单快照为准，与商品页实时库存无关。",
]

_compiled_graph = None


@tool
def request_return_confirmation(reason: str) -> str:
    """当用户明确提出退货或退款诉求时调用，触发用户二次确认。不要自行发送退货地址。"""
    return f"已记录用户意向：{reason}"


class SupportState(TypedDict):
    messages: Annotated[list, add_messages]
    user_input: str
    retrieved_context: str
    response: str
    confirm_decision: str | None


def retrieve_context(state: SupportState) -> SupportState:
    query = state["user_input"]
    if not hasattr(retrieve_context, "vectorstore"):
        texts = getattr(retrieve_context, "kb_texts", SAMPLE_KB)
        splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=20)
        docs_split = splitter.create_documents(texts)
        embeddings = make_embeddings()
        retrieve_context.vectorstore = FAISS.from_documents(docs_split, embeddings)

    docs = retrieve_context.vectorstore.similarity_search(query, k=3)
    context = "\n".join(d.page_content for d in docs)
    return {"retrieved_context": context}


def build_system_prompt(retrieved_context: str) -> str:
    return f"""你是「{BRAND_NAME}」的在线客服，主营服装销售（女装、男装、配饰）。

请根据以下知识库内容准确回答用户问题：
{retrieved_context}

回答要求：
- 使用简体中文，语气亲切、专业
- 支持多轮对话：退款、投诉、质量问题、发错货、物流异常等均由你继续跟进
- 当用户明确要求退货或退款时，必须调用 request_return_confirmation 工具，不要直接发送退货地址
- 优先解答规格相关问题（颜色、尺码、换规格、缺货、尺码表怎么看）
- 缺少订单号、照片等信息时，礼貌追问，结合对话历史继续处理
- 不要主动推销优惠、活动、会员或优惠券；用户未问不谈折扣
- 知识库没有的信息请诚实说明，不要编造
- 回复简洁，一般不超过 150 字"""


def agent_node(state: SupportState) -> SupportState:
    conversation = state["messages"][:-1]
    messages = [
        SystemMessage(content=build_system_prompt(state["retrieved_context"])),
        *conversation,
        HumanMessage(content=state["user_input"]),
    ]
    llm = make_chat_llm(temperature=0.2).bind_tools([request_return_confirmation])
    response = llm.invoke(messages)
    return {"messages": [response]}


def route_after_agent(state: SupportState) -> Literal["confirm_return", "finalize_normal"]:
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        for tool_call in last.tool_calls:
            if tool_call["name"] == "request_return_confirmation":
                return "confirm_return"
    return "finalize_normal"


def confirm_return(state: SupportState) -> SupportState:
    last = state["messages"][-1]
    reason = "退货/退款"
    if isinstance(last, AIMessage) and last.tool_calls:
        for tool_call in last.tool_calls:
            if tool_call["name"] == "request_return_confirmation":
                reason = tool_call.get("args", {}).get("reason", reason)

    decision = interrupt(
        {
            "type": "return_confirm",
            "prompt": f"您正在申请{reason}，请确认是否继续？确认后将为您发送退货地址。",
            "options": ["confirm", "cancel"],
        }
    )
    return {"confirm_decision": decision}


def finalize_return(state: SupportState) -> SupportState:
    decision = state.get("confirm_decision") or "cancel"
    last = state["messages"][-1]
    tool_messages: list[ToolMessage] = []
    if isinstance(last, AIMessage) and last.tool_calls:
        for tool_call in last.tool_calls:
            tool_messages.append(
                ToolMessage(
                    tool_call_id=tool_call["id"],
                    content="user_confirmation_received",
                    name=tool_call["name"],
                )
            )

    if decision == "confirm":
        text = f"好的，已确认您的退货/退款申请。\n\n{RETURN_ADDRESS}"
    else:
        text = "好的，已取消本次退货/退款申请。如需其他帮助请随时告诉我。"

    return {
        "response": text,
        "messages": [*tool_messages, AIMessage(content=text)],
        "confirm_decision": None,
    }


def finalize_normal(state: SupportState) -> SupportState:
    last = state["messages"][-1]
    text = last.content if isinstance(last, AIMessage) and last.content else "抱歉，我暂时无法回答，请稍后再试。"
    return {"response": text}


def build_graph():
    graph = StateGraph(SupportState)
    graph.add_node("retrieve", retrieve_context)
    graph.add_node("agent", agent_node)
    graph.add_node("confirm_return", confirm_return)
    graph.add_node("finalize_return", finalize_return)
    graph.add_node("finalize_normal", finalize_normal)
    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "agent")
    graph.add_conditional_edges("agent", route_after_agent, ["confirm_return", "finalize_normal"])
    graph.add_edge("confirm_return", "finalize_return")
    graph.add_edge("finalize_return", END)
    graph.add_edge("finalize_normal", END)
    return graph


def get_compiled_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph().compile(checkpointer=get_checkpointer())
    return _compiled_graph


def thread_config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _extract_interrupt(snapshot) -> dict | None:
    if not snapshot.tasks:
        return None
    for task in snapshot.tasks:
        if task.interrupts:
            return task.interrupts[0].value
    return None


def run_turn(thread_id: str, message: str) -> dict:
    graph = get_compiled_graph()
    config = thread_config(thread_id)
    payload = {
        "user_input": message,
        "messages": [HumanMessage(content=message)],
        "retrieved_context": "",
        "response": "",
        "confirm_decision": None,
    }
    for _ in graph.stream(payload, config, stream_mode="updates"):
        pass
    snapshot = graph.get_state(config)
    interrupt_payload = _extract_interrupt(snapshot)
    if interrupt_payload is not None:
        return {"status": "interrupt", "interrupt": interrupt_payload, "response": ""}
    values = snapshot.values or {}
    return {
        "status": "complete",
        "interrupt": None,
        "response": values.get("response", ""),
    }


def resume_turn(thread_id: str, decision: str) -> dict:
    if decision not in {"confirm", "cancel"}:
        raise ValueError("decision must be 'confirm' or 'cancel'")

    graph = get_compiled_graph()
    config = thread_config(thread_id)
    for _ in graph.stream(Command(resume=decision), config, stream_mode="updates"):
        pass
    snapshot = graph.get_state(config)
    interrupt_payload = _extract_interrupt(snapshot)
    if interrupt_payload is not None:
        return {"status": "interrupt", "interrupt": interrupt_payload, "response": ""}
    values = snapshot.values or {}
    return {
        "status": "complete",
        "interrupt": None,
        "response": values.get("response", ""),
    }


def new_state() -> dict:
    return {
        "awaiting_resume": False,
        "interrupt": None,
        "thread_id": "",
    }


def load_kb_texts(kb_dir: str | None) -> list[str]:
    if not kb_dir:
        return SAMPLE_KB

    root = Path(kb_dir)
    if not root.is_dir():
        raise ValueError(f"Knowledge base directory does not exist: {kb_dir}")

    texts = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".txt", ".md"}:
            texts.append(path.read_text(encoding="utf-8"))

    if not texts:
        raise ValueError(f"No .txt or .md files found in knowledge base directory: {kb_dir}")

    return texts


def main():
    parser = argparse.ArgumentParser(description="Customer Support Agent")
    parser.add_argument("--kb-dir", help="Directory containing .txt or .md support knowledge base files")
    args = parser.parse_args()

    retrieve_context.kb_texts = load_kb_texts(args.kb_dir)
    if hasattr(retrieve_context, "vectorstore"):
        delattr(retrieve_context, "vectorstore")

    thread_id = "cli-session"
    print(f"\n🎧 {BRAND_NAME} 在线客服")
    print("输入 quit 退出\n")

    while True:
        user_input = input("顾客: ").strip()
        if user_input.lower() in ("quit", "exit", "q") or user_input in ("退出", "再见"):
            break
        if not user_input:
            continue

        result = run_turn(thread_id, user_input)
        if result["status"] == "interrupt":
            prompt = result["interrupt"].get("prompt", "请确认是否继续？")
            print(f"\n客服: {prompt}")
            choice = input("继续请输入 y，取消请输入 n: ").strip().lower()
            decision = "confirm" if choice in {"y", "yes", "是", "确认", "继续"} else "cancel"
            result = resume_turn(thread_id, decision)

        print(f"\n客服: {result['response']}\n")


if __name__ == "__main__":
    main()
