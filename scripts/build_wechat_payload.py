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


def auto_link_urls_in_markdown(md_text: str) -> str:
    """
    Convert bare URLs in markdown text to clickable markdown links.
    Example: https://example.com -> [https://example.com](https://example.com)
    """
    # Restrict URL charset to avoid swallowing Chinese punctuation/text and adjacent labels.
    url_pattern = re.compile(
        r"(?<!\]\()(?P<url>https?://[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+)"
    )
    trailing_punct = ".,;:!?)，。；：！）】》」』"

    def repl(match: re.Match) -> str:
        url = match.group("url")
        clean = url.rstrip(trailing_punct)
        suffix = url[len(clean):]
        return f"[{clean}]({clean}){suffix}"

    return url_pattern.sub(repl, md_text)


def extract_first_url(md_text: str) -> str:
    pattern = re.compile(r"https?://[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+")
    m = pattern.search(md_text)
    return m.group(0) if m else ""


def markdown_to_wechat_html(md_text: str) -> str:
    md_text = auto_link_urls_in_markdown(md_text)
    html = markdown.markdown(md_text, extensions=["extra", "sane_lists", "tables", "nl2br"])
    # Remove first H1 to avoid title duplication in WeChat article page.
    html = re.sub(r"^\s*<h1>.*?</h1>\s*", "", html, count=1, flags=re.DOTALL)
    return apply_wechat_inline_style(html)


def apply_wechat_inline_style(html: str) -> str:
    """Apply WeChat-friendly inline styles. WeChat strips <style>/class aggressively."""
    replacements = [
        (
            r"<h1>",
            '<h1 style="font-size:1.7em;font-weight:normal;border-bottom:2px solid hsl(216,100%,68%);">',
        ),
        (
            r"<h2>",
            '<h2 style="font-weight:normal;color:#333;font-size:1.4em;border-bottom:1px solid hsl(216,100%,68%);">',
        ),
        (
            r"<h3>",
            '<h3 style="font-weight:normal;color:#333;font-size:1.2em;">',
        ),
        (
            r"<h4>",
            '<h4 style="font-weight:normal;font-size:1em;width:80%;border:1px solid hsl(216,100%,68%);border-top:4px solid hsl(216,100%,68%);padding:10px;margin:30px auto;color:#666;">',
        ),
        (
            r"<h5>",
            '<h5 style="font-weight:normal;font-size:1.3em;text-align:center;background:hsl(216,100%,68%);border:3px double #fff;width:80%;padding:10px;margin:30px auto;color:#fff;">',
        ),
        (
            r"<h6>",
            '<h6 style="font-size:1.5em;font-weight:normal;color:hsl(216,100%,68%);border-bottom:1px solid hsl(216,100%,68%);">',
        ),
        (
            r"<p>",
            '<p style="color:#666;">',
        ),
        (
            r"<ul>",
            '<ul style="padding-left:2em;">',
        ),
        (
            r"<ol>",
            '<ol style="padding-left:2em;">',
        ),
        (
            r"<li>",
            '<li style="color:#666;">',
        ),
        (
            r"<blockquote>",
            '<blockquote style="background:#f9f9f9;border-left-color:hsl(216,100%,68%);">',
        ),
        (
            r"<hr\s*/?>",
            '<hr style="width:90%;margin:1.5em auto;border-top:2px dashed hsl(216,100%,68%);" />',
        ),
        (
            r"<table>",
            '<table style="margin:1.5em auto;width:auto;">',
        ),
        (
            r"<th[^>]*>",
            '<th style="color:#333;font-weight:normal;">',
        ),
        (
            r"<td[^>]*>",
            '<td style="color:#666;">',
        ),
        (
            r"<code>",
            '<code style="color:hsl(216,100%,68%);">',
        ),
        (
            r"<a\s+href=",
            '<a style="color:hsl(187,100%,45%);font-weight:normal;border-bottom-color:hsl(187,100%,45%);" href=',
        ),
        (
            r"<strong>",
            '<strong style="color:hsl(216,80%,44%);">',
        ),
        (
            r"<em>",
            '<em style="font-style:normal;font-weight:normal;color:white;background:hsl(244,100%,75%);padding:2px 4px;margin:0 2px;">',
        ),
        (
            r"<img\s",
            '<img style="width:90%;margin:0 auto;box-shadow:#CCC 0 10px 15px;" ',
        ),
        (
            r"<s>",
            '<s style="color:#999;">',
        ),
        (
            r"<del>",
            '<del style="color:#999;">',
        ),
        (
            r"<sup>",
            '<sup style="line-height:0;">',
        ),
    ]

    for pattern, repl in replacements:
        html = re.sub(pattern, repl, html, flags=re.IGNORECASE)

    wrapped = (
        '<section style="font-family:PingFang SC, Microsoft YaHei, sans-serif;word-break:break-all;">'
        + html
        + "</section>"
    )
    return wrapped


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
    content_source_url = args.content_source_url or extract_first_url(md_text)

    payload = {
        "articles": [
            {
                "title": title,
                "author": args.author,
                "digest": digest,
                "content": content,
                "content_source_url": content_source_url,
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
