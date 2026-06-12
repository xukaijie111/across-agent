"""可选插件包；默认不注册任何插件，由业务侧按需 register_plugin。"""

from context.plugins.base import BaseContextPlugin

__all__ = ["BaseContextPlugin"]
