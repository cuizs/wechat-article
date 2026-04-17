from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import markdown


def extract_title(md_text: str) -> str:
    for line in md_text.splitlines():
        m = re.match(r"^#\s+(.+?)\s*$", line.strip())
        if m:
            return m.group(1).strip()
    return "上周热点资讯周报"


def extract_digest(md_text: str) -> str:
    lines = [ln.strip() for ln in md_text.splitlines() if ln.strip()]
    candidates = []
    for ln in lines:
        if ln.startswith("#"):
            continue
        if ln.startswith("```"):
            continue
        candidates.append(ln)
    if not candidates:
        return "基于公开信息整理的行业周报。"
    text = re.sub(r"\s+", " ", candidates[0])
    return text[:120]


def markdown_to_wechat_html(md_text: str) -> str:
    html = markdown.markdown(md_text, extensions=["extra", "sane_lists", "tables", "nl2br"])
    # Remove first H1 to avoid title duplication in WeChat article page.
    html = re.sub(r"^\s*<h1>.*?</h1>\s*", "", html, count=1, flags=re.DOTALL)
    return html


def main() -> None:
    parser = argparse.ArgumentParser(description="Build WeChat draft payload from markdown")
    parser.add_argument("--input", required=True, help="Input markdown file")
    parser.add_argument("--output", required=True, help="Output payload json file")
    parser.add_argument("--thumb-media-id", required=True, help="WeChat thumb_media_id")
    parser.add_argument("--author", default="", help="Article author")
    parser.add_argument("--content-source-url", default="", help="Original link")
    parser.add_argument("--need-open-comment", type=int, default=1, choices=[0, 1])
    parser.add_argument("--only-fans-can-comment", type=int, default=0, choices=[0, 1])
    parser.add_argument("--show-cover-pic", type=int, default=1, choices=[0, 1])
    args = parser.parse_args()

    md_text = Path(args.input).read_text(encoding="utf-8")
    title = extract_title(md_text)
    digest = extract_digest(md_text)
    content = markdown_to_wechat_html(md_text)

    payload = {
        "articles": [
            {
                "title": title,
                "author": args.author,
                "digest": digest,
                "content": content,
                "content_source_url": args.content_source_url,
                "thumb_media_id": args.thumb_media_id,
                "need_open_comment": args.need_open_comment,
                "only_fans_can_comment": args.only_fans_can_comment,
                "show_cover_pic": args.show_cover_pic,
            }
        ]
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(str(output_path.resolve()))


if __name__ == "__main__":
    main()
