"""Pydantic 入门示例 — 运行: python test_pydantic.py

和 LangChain tool 的关系：
  函数签名 → Pydantic 模型 → JSON Schema → 给 LLM 的 parameters
  invoke 时 → Pydantic 校验 args → 再调你的函数
"""

from __future__ import annotations

import json

from pydantic import BaseModel, Field, ValidationError


def section(title: str) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


# ---------------------------------------------------------------------------
# 1. 最基础：定义模型 + 创建实例
# ---------------------------------------------------------------------------
def demo_basic() -> None:
    section("1. 基础：BaseModel 定义 + 创建")

    class User(BaseModel):
        name: str
        age: int

    user = User(name="张三", age=20)
    print("创建成功:", user)
    print("访问字段:", user.name, user.age)
    print("转成 dict:", user.model_dump())
    print("转成 JSON:", user.model_dump_json())


# ---------------------------------------------------------------------------
# 2. 校验：类型错、缺字段
# ---------------------------------------------------------------------------
def demo_validation() -> None:
    section("2. 校验失败时会怎样")

    class ReadFileInput(BaseModel):
        path: str

    # ✅ 正确
    ok = ReadFileInput(path="cli/main.py")
    print("OK:", ok)

    # ❌ 缺字段
    try:
        ReadFileInput()
    except ValidationError as e:
        print("\n缺 path 时:")
        print(e.errors()[0]["msg"])  # Field required

    # ❌ 类型错
    try:
        ReadFileInput(path=123)
    except ValidationError as e:
        print("\npath 传 int 时:")
        print(e.errors()[0]["msg"])


# ---------------------------------------------------------------------------
# 3. 必填 vs 可选（和 tool 的 required 对应）
# ---------------------------------------------------------------------------
def demo_required_optional() -> None:
    section("3. 必填 vs 可选（对应 tool schema 的 required）")

    class SearchInput(BaseModel):
        pattern: str                      # 无默认值 → 必填
        path: str = "."                   # 有默认值 → 可选
        max_count: int = 10

    a = SearchInput(pattern="*.py")
    print("只传必填:", a.model_dump())

    b = SearchInput(pattern="*.py", path="src", max_count=50)
    print("全传:", b.model_dump())

    schema = SearchInput.model_json_schema()
    print("\nJSON Schema（LLM 看的格式）:")
    print(json.dumps(schema, ensure_ascii=False, indent=2))
    print("required 列表:", schema.get("required", []))


# ---------------------------------------------------------------------------
# 4. Field：更细的约束 + 描述
# ---------------------------------------------------------------------------
def demo_field() -> None:
    section("4. Field：长度、范围、描述")

    class RunBuildInput(BaseModel):
        target: str = Field(
            default="weixin",
            description="构建目标：weixin / alipay / h5",
        )
        max_count: int = Field(default=10, ge=1, le=50, description="最多返回几条")

    ok = RunBuildInput()
    print("默认值:", ok.model_dump())

    try:
        RunBuildInput(max_count=0)  # ge=1，小于 1 报错
    except ValidationError as e:
        print("max_count=0 报错:", e.errors()[0]["msg"])

    schema = RunBuildInput.model_json_schema()
    print("\ntarget 字段描述:", schema["properties"]["target"].get("description"))


# ---------------------------------------------------------------------------
# 5. 从 dict 创建（模拟模型 tool_call 的 arguments）
# ---------------------------------------------------------------------------
def demo_from_dict() -> None:
    section("5. 从 dict 创建 — 模拟 LLM 传的 arguments")

    class GitLogInput(BaseModel):
        max_count: int = 10

    # 模型返回的 arguments 通常是 JSON，解析后是 dict
    args_from_llm = {"max_count": 3}

    validated = GitLogInput.model_validate(args_from_llm)
    print("校验通过:", validated)
    print("可以安全传给函数: git_log(max_count=", validated.max_count, ")")

    bad_args = {"max_count": "abc"}
    try:
        GitLogInput.model_validate(bad_args)
    except ValidationError as e:
        print("坏参数:", e.errors()[0]["msg"])


# ---------------------------------------------------------------------------
# 6. 和 LangChain tool 的关系
# ---------------------------------------------------------------------------
def demo_with_langchain_tool() -> None:
    section("6. 和 LangChain tool 的关系")

    from langchain_core.tools import tool

    @tool
    def read_file(path: str, max_bytes: int = 200_000) -> str:
        """读取工作区内的文本文件。"""
        return f"read {path}, limit {max_bytes}"

    print("tool 内部的 args_schema 就是 Pydantic 模型:")
    print("  类名:", read_file.args_schema.__name__)
    print("  schema:", json.dumps(read_file.args_schema.model_json_schema(), indent=2))

    print("\ninvoke 时 Pydantic 在校验:")
    print("  ", read_file.invoke({"path": "a.py"}))
    try:
        read_file.invoke({})
    except Exception as e:
        print("  缺 path:", type(e).__name__, str(e)[:80])


# ---------------------------------------------------------------------------
# 7. 自己手写 schema（不用函数签名时）
# ---------------------------------------------------------------------------
def demo_custom_schema() -> None:
    section("7. 手写 Pydantic 模型当 tool 参数（高级）")

    from langchain_core.tools import tool

    class WriteFileInput(BaseModel):
        path: str = Field(min_length=1, description="相对工作区的路径")
        content: str = Field(description="文件内容")

    @tool(args_schema=WriteFileInput)
    def write_file(path: str, content: str) -> str:
        """写入工作区内的文本文件。"""
        return json.dumps({"ok": True, "path": path}, ensure_ascii=False)

    print("schema:", json.dumps(write_file.args_schema.model_json_schema(), indent=2))
    print("invoke:", write_file.invoke({"path": "out.txt", "content": "hello"}))


if __name__ == "__main__":
    demo_basic()
    demo_validation()
    demo_required_optional()
    demo_field()
    demo_from_dict()
    demo_with_langchain_tool()
    demo_custom_schema()
