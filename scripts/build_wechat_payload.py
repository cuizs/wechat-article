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
            '<h1 style="font-size:1.8em;color:#009688;margin:1.2em auto;text-align:center;border-bottom:1px solid #009688;line-height:1.6;">',
        ),
        (
            r"<h2>",
            '<h2 style="color:#009688;padding-left:10px;margin:1em auto;border-left:3px solid #009688;font-size:1.5em;line-height:1.6;">',
        ),
        (
            r"<h3>",
            '<h3 style="margin:0.6em auto;padding-left:10px;border-left:2px solid #009688;font-size:1.25em;line-height:1.6;">',
        ),
        (
            r"<h4>",
            '<h4 style="margin:0.6em auto;font-size:1.2em;padding-left:10px;border-left:2px dashed #009688;line-height:1.6;">',
        ),
        (
            r"<h5>",
            '<h5 style="margin:0.6em auto;font-size:1.1em;padding-left:10px;border-left:1px dashed #009688;line-height:1.6;">',
        ),
        (
            r"<h6>",
            '<h6 style="margin:0.6em auto;font-size:1em;padding-left:10px;border-left:1px dotted #009688;line-height:1.6;">',
        ),
        (
            r"<p>",
            '<p style="margin-top:5px;margin-bottom:5px;line-height:26px;word-spacing:3px;letter-spacing:1px;text-align:justify;color:#3e3e3e;font-size:16px;text-indent:2em;">',
        ),
        (
            r"<ul>",
            '<ul style="margin:10px 0 14px 0;padding-left:22px;line-height:26px;">',
        ),
        (
            r"<ol>",
            '<ol style="margin:10px 0 14px 0;padding-left:22px;line-height:26px;">',
        ),
        (
            r"<li>",
            '<li style="font-size:16px;line-height:26px;color:#3e3e3e;margin:6px 0;text-align:justify;letter-spacing:1px;">',
        ),
        (
            r"<blockquote>",
            '<blockquote style="border-left:2px solid #888;border-right:2px solid #888;padding-left:1em;color:#777;margin:16px 0;">',
        ),
        (
            r"<hr\s*/?>",
            '<hr style="border:none;border-top:1px solid #3e3e3e;margin:20px 0;" />',
        ),
        (
            r"<table>",
            '<table style="border-collapse:collapse;width:100%;margin:14px 0;font-size:16px;">',
        ),
        (
            r"<th[^>]*>",
            '<th style="border:1px solid #009688;background:#009688;color:#f8f8f8;border-bottom:0;padding:5px 10px;font-size:16px;">',
        ),
        (
            r"<td[^>]*>",
            '<td style="border:1px solid #009688;padding:5px 10px;font-size:16px;color:#3e3e3e;">',
        ),
        (
            r"<code>",
            '<code style="color:#009688;">',
        ),
        (
            r"<a\s+href=",
            '<a style="color:#009688;border-bottom:1px solid #009688;text-decoration:none;" href=',
        ),
        (
            r"<strong>",
            '<strong style="color:#3e3e3e;font-weight:700;">',
        ),
    ]

    for pattern, repl in replacements:
        html = re.sub(pattern, repl, html, flags=re.IGNORECASE)

    wrapped = (
        '<section style="padding:30px;font-family:Optima-Regular, PingFang SC, Microsoft YaHei, Arial, sans-serif;'
        'font-size:16px;line-height:26px;color:#3e3e3e;word-break:break-all;">'
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
