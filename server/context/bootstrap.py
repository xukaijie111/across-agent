"""应用启动时一次性加载上下文治理；在 main lifespan 里 import 即可。

子 Agent 不 import 本模块，也不直接 register_plugin。
"""

# 未来在此 register_plugin(MyPlugin())
