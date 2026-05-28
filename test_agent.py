"""手工联调：调用真实千问 API。推荐用 CLI：python -m cli chat -s demo -v"""

from services.agent_loop import chat_with_tools
from services.session import ConversationStore

if __name__ == "__main__":
    store = ConversationStore()
    session_id = "demo"

    reply, delta = chat_with_tools(
        "帮我检测 ./ 项目是什么框架，并编译成微信小程序",
        history=store.get(session_id),
        verbose=True,
    )
    store.extend(session_id, delta)
    print("\n=== 回复 ===\n", reply)
    print("session:", session_id, "messages:", len(store.get(session_id)))
