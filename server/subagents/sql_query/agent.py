"""
SQL Query Agent — 自然语言查 MySQL 数据库，自动生成并执行 SQL。

内置 demo e-commerce 表（customers / products / orders），
首次运行自动建表并写入示例数据。

Usage:
    python agent.py
    python agent.py --question "每个国家的客户数量"
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from urllib.parse import quote_plus as urlquote

from dotenv import load_dotenv
from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase

SERVER_ROOT = Path(__file__).resolve().parents[2]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from db import _mysql_config
from llm_config import make_chat_llm

PROJECT_ROOT = SERVER_ROOT.parent
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(SERVER_ROOT / ".env")

DEMO_SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(200) UNIQUE,
    country VARCHAR(50),
    created_at DATE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS products (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(200) NOT NULL,
    category VARCHAR(100),
    price DECIMAL(10,2) NOT NULL,
    stock INT DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS orders (
    id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT,
    product_id INT,
    quantity INT NOT NULL,
    total DECIMAL(10,2) NOT NULL,
    order_date DATE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

DEMO_DATA = """-- customers
INSERT INTO customers (id, name, email, country, created_at) VALUES
    (1,'张敏','zhangmin@example.com','中国','2024-01-15'),
    (2,'李强','liqiang@example.com','中国','2024-02-20'),
    (3,'王芳','wangfang@example.com','英国','2024-03-10'),
    (4,'陈杰','chenjie@example.com','美国','2024-01-05')
ON DUPLICATE KEY UPDATE
    name=VALUES(name), email=VALUES(email), country=VALUES(country), created_at=VALUES(created_at);

-- products
INSERT INTO products (id, name, category, price, stock) VALUES
    (1,'轻薄笔记本 Pro','数码',1299.99,45),
    (2,'无线鼠标','数码',29.99,200),
    (3,'Python 编程入门','图书',49.99,120),
    (4,'升降书桌','家具',599.99,15)
ON DUPLICATE KEY UPDATE
    name=VALUES(name), category=VALUES(category), price=VALUES(price), stock=VALUES(stock);

-- orders
INSERT INTO orders (id, customer_id, product_id, quantity, total, order_date) VALUES
    (1,1,1,1,1299.99,'2024-04-01'),
    (2,1,2,2,59.98,'2024-04-01'),
    (3,2,3,1,49.99,'2024-04-05'),
    (4,3,4,1,599.99,'2024-04-10'),
    (5,4,1,1,1299.99,'2024-04-12'),
    (6,2,2,3,89.97,'2024-04-15')
ON DUPLICATE KEY UPDATE
    customer_id=VALUES(customer_id), product_id=VALUES(product_id),
    quantity=VALUES(quantity), total=VALUES(total), order_date=VALUES(order_date);
"""

SQL_PREFIX = """你是「数据问数」助手，连接 MySQL 演示电商库。

可用表：
- customers：客户（姓名、邮箱、国家、注册日期）
- products：商品（名称、分类、价格、库存）
- orders：订单（客户、商品、数量、金额、下单日期）

当用户问客户数、销量、库存、订单金额、谁消费最多等可量化问题时：
1. 用工具查看表结构
2. 编写正确的 {dialect} 查询并执行
3. 用简体中文总结结果

以下情况不要调用任何 SQL 工具，直接用 Final Answer 回复（不要查库）：
- 问候、闲聊、感谢、告别
- 退换货政策、尺码建议等客服问题（说明本助手只查 demo 数据，可去「服装客服」咨询）

回答要求：
- 一律使用简体中文，语气友好自然
- 禁止回复英文或只说「I don't know」
- 非查库场景：简短说明你能做什么，并给 1～2 个示例问题
- 查库时结论清晰，默认最多 {top_k} 条，不要 SELECT *
- 禁止 INSERT/UPDATE/DELETE/DROP 等写操作
- 执行 SQL 前务必核对语句
"""

SQL_TOOL_SUFFIX = "需要查库时先用工具看表结构和数据；不需要查库时用中文直接回答用户。"

_GREETINGS = frozenset(
    {"你好", "您好", "hi", "hello", "嗨", "在吗", "在不在", "早上好", "下午好", "晚上好", "哈喽"}
)
_THANKS = frozenset({"谢谢", "感谢", "thanks", "thank you", "多谢"})
_FAREWELLS = frozenset({"再见", "拜拜", "bye", "goodbye"})

_GREETING_REPLY = (
    "你好！我是数据问数助手，可以帮你查演示库里的客户、商品和订单。"
    "试试问：「每个国家有多少客户？」或「销量最好的商品是什么？」"
)


def _try_small_talk(message: str) -> str | None:
    text = message.strip()
    if not text:
        return None
    lower = text.lower()
    if lower in _GREETINGS or text in _GREETINGS:
        return _GREETING_REPLY
    if lower in _THANKS or text in _THANKS:
        return "不客气！还有数据问题随时问我。"
    if lower in _FAREWELLS or text in _FAREWELLS:
        return "再见！需要查数据时再来找我。"
    if len(text) <= 6 and any(g in text for g in ("你好", "您好", "嗨", "哈喽")):
        return _GREETING_REPLY
    return None


def _mysql_uri() -> str:
    cfg = _mysql_config()
    password = urlquote(cfg["password"]) if cfg["password"] else ""
    user = urlquote(cfg["user"])
    host = cfg["host"]
    port = cfg["port"]
    db = cfg["database"]
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{db}"


_agent = None
_db = None


def _split_sql_script(script: str) -> list[str]:
    """按分号拆 SQL，去掉 -- 注释行。"""
    statements: list[str] = []
    for chunk in script.strip().split(";"):
        lines = [ln for ln in chunk.splitlines() if ln.strip() and not ln.strip().startswith("--")]
        sql = "\n".join(lines).strip()
        if sql:
            statements.append(sql)
    return statements


def _ensure_demo_data() -> None:
    import pymysql

    cfg = _mysql_config()
    conn = pymysql.connect(**cfg)
    try:
        with conn.cursor() as cur:
            for sql in _split_sql_script(DEMO_SCHEMA):
                cur.execute(sql)
            conn.commit()

            for sql in _split_sql_script(DEMO_DATA):
                cur.execute(sql)
            conn.commit()
    finally:
        conn.close()


def get_agent():
    global _agent, _db
    if _agent is None:
        _ensure_demo_data()
        _db = SQLDatabase.from_uri(_mysql_uri())
        llm = make_chat_llm(temperature=0)
        toolkit = SQLDatabaseToolkit(db=_db, llm=llm)
        _agent = create_sql_agent(
            llm=llm,
            toolkit=toolkit,
            agent_type="tool-calling",
            prefix=SQL_PREFIX,
            suffix=SQL_TOOL_SUFFIX,
            verbose=False,
            agent_executor_kwargs={"handle_parsing_errors": True},
        )
    return _agent, _db


def run_turn(thread_id: str, message: str) -> dict:
    """统一接口：自然语言 → SQL → 回答。thread_id 保留，当前无状态。"""
    _ = thread_id
    small_talk = _try_small_talk(message)
    if small_talk is not None:
        return {"status": "complete", "response": small_talk, "interrupt": None}

    agent, _ = get_agent()
    result = agent.invoke({"input": message})
    return {"status": "complete", "response": result["output"], "interrupt": None}


def new_state() -> dict:
    return {"awaiting_resume": False, "interrupt": None, "thread_id": ""}


def main() -> None:
    parser = argparse.ArgumentParser(description="SQL Query Agent (MySQL)")
    parser.add_argument("--question", help="单次查询（省略则进入交互模式）")
    args = parser.parse_args()

    agent, db = get_agent()
    print(f"\n📊 MySQL: {_mysql_uri().split('@')[1]}")  # 隐藏密码
    print(f"📋 Tables: {', '.join(db.get_table_names())}\n")

    if args.question:
        print(f"❓ {args.question}")
        result = agent.invoke({"input": args.question})
        print(f"\n✅ {result['output']}\n")
    else:
        print("💬 输入自然语言问题，输入 quit 退出\n")
        while True:
            question = input("你: ").strip()
            if question.lower() in ("quit", "exit", "q") or question in ("退出", "再见"):
                break
            if not question:
                continue
            result = agent.invoke({"input": question})
            print(f"\n助手: {result['output']}\n")


if __name__ == "__main__":
    main()
