from __future__ import annotations

import typer

from services.agent_loop import chat_with_tools
from services.session import ConversationStore

app = typer.Typer(help="CrossAgent CLI")
session_app = typer.Typer(help="会话管理")
app.add_typer(session_app, name="session")

store = ConversationStore()


def _run_turn(session_id: str, user_input: str, verbose: bool) -> str:
    history = store.get(session_id)
    reply, delta = chat_with_tools(user_input, history=history, verbose=verbose)
    store.extend(session_id, delta)
    return reply


@app.command("chat")
def chat(
    message: str | None = typer.Argument(None, help="单轮问题；省略则进入交互模式"),
    session: str = typer.Option("default", "--session", "-s", help="会话 ID"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="打印 context / usage"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="多轮 REPL"),
) -> None:
    """与 Agent 对话（Tool Calling），历史写入 data/sessions/{id}.json"""
    if interactive or message is None:
        typer.echo(f"会话: {session}（输入 exit 退出）\n")
        while True:
            try:
                user_input = typer.prompt("You").strip()
            except (EOFError, KeyboardInterrupt):
                typer.echo()
                break
            if not user_input or user_input.lower() in ("exit", "quit", "q"):
                break
            reply = _run_turn(session, user_input, verbose)
            typer.echo(f"\nAssistant: {reply}\n")
        return

    reply = _run_turn(session, message, verbose)
    typer.echo(reply)


@session_app.command("list")
def session_list() -> None:
    """列出已保存的 session"""
    ids = store.list()
    if not ids:
        typer.echo("（暂无会话）")
        return
    for sid in ids:
        n = len(store.get(sid))
        typer.echo(f"{sid}\t{n} messages")


@session_app.command("clear")
def session_clear(
    session_id: str = typer.Argument(..., help="要清空的 session ID"),
) -> None:
    store.clear(session_id)
    typer.echo(f"已清空: {session_id}")
