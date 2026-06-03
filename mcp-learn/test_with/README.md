# with / async with 学习 Demo

建议按顺序运行：

```bash
cd mcp-learn/test_with

python demo1_sync_class.py      # __enter__ / __exit__
python demo3_yield.py           # yield 前 = 打开，yield 后 = 关闭
python demo5_as_value.py        # as 后面是什么
python demo2_async_class.py     # __aenter__ / __aexit__
python demo4_async_yield.py     # 模拟 MCP 两层 async with
```

## 对照 MCP

| Demo | MCP |
|------|-----|
| demo3/demo4 yield 前 | spawn calc_server |
| demo3/demo4 yield 后 | 杀子进程 |
| demo2/demo4 session | ClientSession |
| 块内 await call | initialize / list_tools / call_tool |
