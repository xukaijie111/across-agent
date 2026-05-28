import json
from typing import Any

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "detect_framework",
            "description": "检测项目相关内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": "项目路径",
                    },
                },
                "required": ["project_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_build",
            "description": "执行项目构建",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": "项目路径",
                    },
                },
                "required": ["project_path"],
            },
        },
    },
]

def execute_tool(tool_name: str, tool_args: dict[str, Any]) -> str:
    if (tool_name == "detect_framework"):
        return detect_framework(tool_args["project_path"])
    elif (tool_name == "run_build"):
        return run_build(tool_args["project_path"])
    else:
        raise ValueError(f"Unknown tool: {tool_name}")
    
def detect_framework(project_path: str) -> str:
    return json.dumps({

           "type": "object",
           "framework": "uni-app",
           "version": "3.0.0",
           "dependencies": ["uni-app", "uni-ui"],
           "plugins": ["uni-app-plus", "uni-app-plus-nvue"],
           "platforms": ["ios", "android"],
           "languages": ["javascript", "typescript"],
           "frameworks": ["react", "vue"],
           "libraries": ["react-native", "vue-native"],
           "tools": ["webpack", "babel", "eslint", "prettier"],
    })

def run_build(project_path: str) -> str:
    return json.dumps({
        "type": "object",
        "status": "success",
        "message": "build success",
    })
