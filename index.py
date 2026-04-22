from __future__ import annotations

import argparse
import os

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

from tools.agent_tools import calculate_tool, read_file_tool, search_tool, write_file_tool
from utils.files import read_markdown_file


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name, str(default))
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"环境变量 {name} 必须是数字，当前值: {raw}") from exc


def build_llm() -> ChatOpenAI:
    provider = os.getenv("LLM_PROVIDER", "dashscope").strip().lower()
    temperature = _float_env("MODEL_TEMPERATURE", 0.5)

    if provider == "openclaw":
        model = os.getenv("LLM_MODEL") or os.getenv("OPENCLAW_MODEL", "openclaw-chat")
        api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENCLAW_API_KEY")
        base_url = os.getenv("LLM_BASE_URL") or os.getenv("OPENCLAW_BASE_URL")
        if not api_key:
            raise ValueError("LLM_PROVIDER=openclaw 时缺少 API Key，请设置 LLM_API_KEY 或 OPENCLAW_API_KEY")
        if not base_url:
            raise ValueError("LLM_PROVIDER=openclaw 时缺少 Base URL，请设置 LLM_BASE_URL 或 OPENCLAW_BASE_URL")
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=api_key,
            base_url=base_url,
        )

    if provider == "openai":
        model = os.getenv("LLM_MODEL") or os.getenv("MODEL_NAME", "gpt-4o-mini")
        api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL")
        if not api_key:
            raise ValueError("LLM_PROVIDER=openai 时缺少 API Key，请设置 LLM_API_KEY 或 OPENAI_API_KEY")
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=api_key,
            base_url=base_url,
        )

    # 默认按 dashscope/openai-compatible 兼容路由，保持现有行为
    model = os.getenv("LLM_MODEL") or os.getenv("MODEL_NAME", "glm-5")
    api_key = os.getenv("LLM_API_KEY") or os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL", "https://coding.dashscope.aliyuncs.com/v1")
    if not api_key:
        raise ValueError("缺少 API Key，请设置 LLM_API_KEY 或 DASHSCOPE_API_KEY 或 OPENAI_API_KEY")
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        api_key=api_key,
        base_url=base_url,
    )


def build_agent():
    load_dotenv()
    llm = build_llm()

    system_prompt = read_markdown_file("prompt/system_main.md")
    return create_agent(
        model=llm,
        system_prompt=system_prompt,
        tools=[search_tool, calculate_tool, read_file_tool, write_file_tool],
    )


def _extract_text(result) -> str:
    if isinstance(result, dict):
        messages = result.get("messages") or []
        for message in reversed(messages):
            content = getattr(message, "content", "")
            if isinstance(content, str) and content.strip():
                return content
    return str(result)


def run_once(agent, task: str) -> str:
    result = agent.invoke({"messages": [HumanMessage(content=task)]})
    return _extract_text(result)


def interactive_loop(agent):
    print("ReAct Agent 已启动，输入任务后回车。输入 exit 或 quit 结束。")
    while True:
        task = input("\n你: ").strip()
        if task.lower() in {"exit", "quit"}:
            print("已退出。")
            break
        if not task:
            continue
        answer = run_once(agent, task)
        print(f"\nAgent:\n{answer}")


def main():
    parser = argparse.ArgumentParser(description="Minimal ReAct agent runner")
    parser.add_argument("--task", type=str, help="单次执行任务")
    args = parser.parse_args()

    agent = build_agent()
    if args.task:
        print(run_once(agent, args.task))
    else:
        interactive_loop(agent)


if __name__ == "__main__":
    main()
