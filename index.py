from __future__ import annotations

import argparse
import os

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

from tools.agent_tools import calculate_tool, read_file_tool, search_tool, write_file_tool
from utils.files import read_markdown_file


def build_agent():
    load_dotenv()
    api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("缺少 API Key，请设置 DASHSCOPE_API_KEY 或 OPENAI_API_KEY")

    llm = ChatOpenAI(
        model=os.getenv("MODEL_NAME", "glm-5"),
        temperature=float(os.getenv("MODEL_TEMPERATURE", "0.5")),
        api_key=api_key,
        base_url=os.getenv("OPENAI_BASE_URL", "https://coding.dashscope.aliyuncs.com/v1"),
    )

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
