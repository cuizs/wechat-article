from pathlib import Path


def read_markdown_file(file_path: str) -> str:
    """Read markdown file as plain text for LLM system prompt."""
    return Path(file_path).read_text(encoding="utf-8")
