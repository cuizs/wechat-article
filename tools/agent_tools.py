from __future__ import annotations

import ast
import json
import math
import os
from pathlib import Path
from urllib.request import Request, urlopen

from langchain_community.tools import StructuredTool, Tool

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
MAX_READ_CHARS = 20_000

ALLOWED_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "pi": math.pi,
    "e": math.e,
}


def _resolve_workspace_path(path: str) -> Path:
    raw = Path(path)
    target = raw if raw.is_absolute() else WORKSPACE_ROOT / raw
    target = target.resolve()
    if not str(target).startswith(str(WORKSPACE_ROOT)):
        raise ValueError(f"路径越界，不允许访问工作区外路径: {path}")
    return target


def search(query: str) -> str:
    """
    Search public web using Tavily Search API.
    Returns a compact plain-text summary for the agent.
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "搜索失败：缺少环境变量 TAVILY_API_KEY"

    endpoint = "https://api.tavily.com/search"
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "max_results": 5,
        "include_answer": True,
        "include_raw_content": False,
    }
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        endpoint,
        data=body,
        headers={
            "User-Agent": "react-agent/1.0",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return f"搜索失败：{exc}"

    parts = []
    answer = (payload.get("answer") or "").strip()
    if answer:
        parts.append(f"答案摘要: {answer}")

    results = payload.get("results") or []
    result_lines = []
    for item in results[:3]:
        title = (item.get("title") or "").strip()
        content = (item.get("content") or "").strip().replace("\n", " ")
        url = (item.get("url") or "").strip()
        text = f"{title} | {content}" if title else content
        if url:
            text = f"{text} ({url})"
        if text:
            result_lines.append(text)
    if result_lines:
        parts.append("结果: " + " || ".join(result_lines))

    if not parts:
        return f"未检索到可用摘要结果。query={query}"
    return "\n".join(parts)


def _safe_eval(node: ast.AST):
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _safe_eval(node.operand)
        return +value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.BinOp) and isinstance(
        node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.FloorDiv)
    ):
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.Pow):
            return left**right
        if isinstance(node.op, ast.Mod):
            return left % right
        return left // right
    if isinstance(node, ast.Name) and node.id in ALLOWED_FUNCTIONS:
        return ALLOWED_FUNCTIONS[node.id]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        fn_name = node.func.id
        if fn_name not in ALLOWED_FUNCTIONS:
            raise ValueError(f"不支持的函数: {fn_name}")
        fn = ALLOWED_FUNCTIONS[fn_name]
        args = [_safe_eval(arg) for arg in node.args]
        return fn(*args)
    raise ValueError(f"不支持的表达式节点: {type(node).__name__}")


def calculate(expression: str) -> str:
    """Safely evaluate arithmetic expression with a small whitelist."""
    try:
        tree = ast.parse(expression, mode="eval")
        value = _safe_eval(tree)
        return str(value)
    except Exception as exc:
        return f"计算失败：{exc}"


def read_file(path: str) -> str:
    target = _resolve_workspace_path(path)
    if not target.exists():
        return f"读取失败：文件不存在 {target}"
    if not target.is_file():
        return f"读取失败：不是文件 {target}"
    content = target.read_text(encoding="utf-8")
    if len(content) > MAX_READ_CHARS:
        return (
            f"[内容过长，已截断到前 {MAX_READ_CHARS} 字符]\n"
            + content[:MAX_READ_CHARS]
        )
    return content


def write_file(path: str, content: str) -> str:
    target = _resolve_workspace_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"写入成功: {target} (chars={len(content)})"


def finish_tool(answer: str) -> str:
    return answer


search_tool = Tool(
    name="Search",
    func=search,
    description="使用互联网搜索公开信息。参数: query。",
)

calculate_tool = Tool(
    name="Calculate",
    func=calculate,
    description="安全计算数学表达式。参数: expression。",
)

read_file_tool = Tool(
    name="ReadFile",
    func=read_file,
    description="读取工作区内文件内容。参数: path。",
)

finish_tool = Tool(
    name="Finish",
    func=finish_tool,
    description="仅在给出最终答案时使用。",
)

write_file_tool = StructuredTool.from_function(
    name="WriteFile",
    func=write_file,
    description="写入工作区内文件内容。参数: path, content。",
)
