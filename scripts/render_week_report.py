from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path

import markdown


DEFAULT_TITLE = "上周热点资讯周报"


def extract_title(md_text: str) -> str:
    for line in md_text.splitlines():
        m = re.match(r"^#\s+(.+?)\s*$", line.strip())
        if m:
            return m.group(1).strip()
    return DEFAULT_TITLE


def build_html(md_text: str, template_path: Path) -> str:
    title = extract_title(md_text)
    html_content = markdown.markdown(
        md_text,
        extensions=["extra", "sane_lists", "tables", "nl2br", "toc"],
    )

    template = template_path.read_text(encoding="utf-8")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return (
        template.replace("{{TITLE}}", title)
        .replace("{{GENERATED_AT}}", now)
        .replace("{{CONTENT}}", html_content)
    )


def main():
    parser = argparse.ArgumentParser(description="Render weekly markdown report to styled HTML")
    parser.add_argument("--input", required=True, help="Input markdown file path")
    parser.add_argument("--output", required=True, help="Output html file path")
    parser.add_argument(
        "--template",
        default="templates/week_report.html",
        help="HTML template path",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    template_path = Path(args.template)

    md_text = input_path.read_text(encoding="utf-8")
    final_html = build_html(md_text, template_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(final_html, encoding="utf-8")

    print(f"Rendered: {output_path.resolve()}")


if __name__ == "__main__":
    main()
