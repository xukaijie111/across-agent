from __future__ import annotations

import json
import subprocess
from pathlib import Path

from services.tools.registry import register_tool
from services.tools.workspace import tool_error, tool_ok, workspace_root

BUILD_TIMEOUT_SEC = 600
BUILD_OUTPUT_TAIL = 4000

TARGET_SCRIPTS: dict[str, list[str]] = {
    "weixin": ["build:weapp", "build:mp-weixin", "build:weixin", "dev:mp-weixin"],
    "alipay": ["build:alipay", "build:mp-alipay", "dev:mp-alipay"],
    "h5": ["build:h5", "build:web", "build"],
    "tt": ["build:tt", "build:mp-toutiao"],
    "baidu": ["build:swan", "build:mp-baidu"],
}


def _read_package_json(root: Path) -> dict | None:
    pkg = root / "package.json"
    if not pkg.is_file():
        return None
    try:
        data = json.loads(pkg.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _collect_deps(pkg: dict) -> dict[str, str]:
    deps: dict[str, str] = {}
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        raw = pkg.get(key) or {}
        if isinstance(raw, dict):
            deps.update({str(k): str(v) for k, v in raw.items()})
    return deps


def _detect_signals(root: Path, deps: dict[str, str]) -> list[str]:
    signals: list[str] = []
    if any(k.startswith("@tarojs/") for k in deps):
        signals.append("taro")
    if (root / "config" / "index.ts").is_file() or (root / "config" / "index.js").is_file():
        if "taro" not in signals and any("taro" in k.lower() for k in deps):
            signals.append("taro")
    if any(k.startswith("@dcloudio/") or "uni-app" in k for k in deps):
        signals.append("uni-app")
    if (root / "pages.json").is_file() or (root / "manifest.json").is_file():
        if "uni-app" not in signals:
            signals.append("uni-app-like")
    if any("morjs" in k.lower() for k in deps) or (root / "mor.config.js").is_file():
        signals.append("morjs")
    if (root / "project.config.json").is_file() or (root / "project.private.config.json").is_file():
        signals.append("wechat-miniprogram-config")
    return signals


def _package_manager(root: Path) -> str:
    if (root / "pnpm-lock.yaml").is_file():
        return "pnpm"
    if (root / "yarn.lock").is_file():
        return "yarn"
    return "npm"


def _run_script(root: Path, script_name: str) -> subprocess.CompletedProcess[str]:
    pm = _package_manager(root)
    if pm == "pnpm":
        cmd = ["pnpm", "run", script_name]
    elif pm == "yarn":
        cmd = ["yarn", script_name]
    else:
        cmd = ["npm", "run", script_name]
    return subprocess.run(
        cmd,
        cwd=root,
        capture_output=True,
        text=True,
        timeout=BUILD_TIMEOUT_SEC,
        check=False,
    )


def _pick_build_script(scripts: dict[str, str], target: str) -> str | None:
    for name in TARGET_SCRIPTS.get(target, []) + ["build"]:
        if name in scripts:
            return name
    return None


@register_tool()
def detect_framework() -> str:
    """检测工作区项目使用的多端框架（uni-app/Taro/Morjs 等）及可用构建脚本。"""
    root = workspace_root()
    pkg = _read_package_json(root)
    if pkg is None:
        return tool_error("未找到可解析的 package.json")

    deps = _collect_deps(pkg)
    signals = _detect_signals(root, deps)
    scripts = pkg.get("scripts") or {}
    script_names = list(scripts.keys()) if isinstance(scripts, dict) else []

    framework = "unknown"
    if "taro" in signals:
        framework = "taro"
    elif "uni-app" in signals or "uni-app-like" in signals:
        framework = "uni-app"
    elif "morjs" in signals:
        framework = "morjs"
    elif signals:
        framework = signals[0]

    return tool_ok(
        framework=framework,
        signals=signals,
        name=pkg.get("name"),
        package_manager=_package_manager(root),
        scripts=script_names,
        suggested_build={
            target: _pick_build_script(scripts, target) if isinstance(scripts, dict) else None
            for target in TARGET_SCRIPTS
        },
    )


@register_tool()
def run_build(target: str = "weixin") -> str:
    """执行项目构建。target 可选 weixin、alipay、h5、tt、baidu。"""
    root = workspace_root()
    pkg = _read_package_json(root)
    if pkg is None:
        return tool_error("未找到 package.json，无法推断构建命令")

    scripts = pkg.get("scripts") or {}
    if not isinstance(scripts, dict):
        return tool_error("package.json scripts 无效")

    target = target.strip().lower() or "weixin"
    script_name = _pick_build_script(scripts, target)
    if script_name is None:
        return tool_error(
            f"未找到适合 target={target!r} 的构建脚本",
            available=list(scripts.keys()),
            supported_targets=list(TARGET_SCRIPTS),
        )

    try:
        proc = _run_script(root, script_name)
        output = (proc.stdout or "") + (proc.stderr or "")
        tail = output[-BUILD_OUTPUT_TAIL:] if len(output) > BUILD_OUTPUT_TAIL else output
        if proc.returncode != 0:
            return tool_error(
                f"构建失败: {_package_manager(root)} run {script_name}",
                exit_code=proc.returncode,
                output=tail,
            )
        return tool_ok(
            script=script_name,
            target=target,
            package_manager=_package_manager(root),
            output=tail,
        )
    except subprocess.TimeoutExpired:
        return tool_error(f"构建超时（>{BUILD_TIMEOUT_SEC}s）: {script_name}")
    except FileNotFoundError:
        return tool_error(f"未找到包管理器: {_package_manager(root)}")
    except Exception as exc:
        return tool_error(str(exc))
