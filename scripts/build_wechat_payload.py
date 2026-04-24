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
    # md_text = auto_link_urls_in_markdown(md_text)
    html = markdown.markdown(md_text, extensions=["extra", "sane_lists", "tables", "nl2br"])
    # Remove leading noise and the first H1 to avoid title duplication.
    # Keep <body ...> tag itself when full HTML is provided.
    if re.search(r"<body\b[^>]*>", html, flags=re.IGNORECASE):
        html = re.sub(
            r"(<body\b[^>]*>)(?:\s|.)*?<h1[^>]*>.*?</h1>\s*",
            r"\1",
            html,
            count=1,
            flags=re.DOTALL | re.IGNORECASE,
        )
    else:
        # Markdown output is usually an HTML fragment, so strip from start to first </h1>.
        html = re.sub(
            r"^.*?<h1[^>]*>.*?</h1>\s*",
            "",
            html,
            count=1,
            flags=re.DOTALL | re.IGNORECASE,
        )
    html = convert_lists_to_line_breaks(html)
    return apply_wechat_inline_style(html)


def convert_lists_to_line_breaks(html: str) -> str:
    """Convert <ul>/<ol>/<li> lists to plain paragraphs with line breaks."""
    list_pattern = re.compile(r"<(ul|ol)\b[^>]*>(.*?)</\1>", flags=re.IGNORECASE | re.DOTALL)
    li_pattern = re.compile(r"<li\b[^>]*>(.*?)</li>", flags=re.IGNORECASE | re.DOTALL)

    def replace_list(match: re.Match) -> str:
        list_content = match.group(2)
        items = [item.strip() for item in li_pattern.findall(list_content) if item.strip()]
        if not items:
            return ""
        return "<p>" + "<br>".join(items) + "</p>"

    return list_pattern.sub(replace_list, html)


def apply_wechat_inline_style(html: str) -> str:
    """Apply WeChat-friendly inline styles. WeChat strips <style>/class aggressively."""
    replacements = [
        (
            r"<h2>",
            '<h2 style="margin-top:30px;margin-bottom:15px;font-weight:bold;font-size:22px; background: linear-gradient(#0e3a9d 90%, #ffb906 10%); color: #ffffff;display: inline-block;padding: 2px 13px 2px;">',
        ),
        (
            r"<h3>",
            '<h3 style="margin-top:30px;margin-bottom:15px;font-weight:bold;color:black;font-size:20px;">',
        ),
        (
            r"<h4>",
            '<h4 style="margin-top:30px;margin-bottom:15px;font-weight:bold;color:black;font-size:18px;">',
        ),
        (
            r"<h5>",
            '<h5 style="margin-top:30px;margin-bottom:15px;font-weight:bold;color:black;font-size:16px;">',
        ),
        (
            r"<h6>",
            '<h6 style="margin-top:30px;margin-bottom:15px;font-weight:bold;color:black;font-size:16px;">',
        ),
        (
            r"<p>",
            '<p style="font-size:16px;padding-top:8px;padding-bottom:8px;margin:0;line-height:26px;color:black;">',
        ),
        (
            r"<ul>",
            '<ul style="margin-top:8px;margin-bottom:8px;padding-left:25px;color:black;list-style-type:disc;">',
        ),
        (
            r"<ol>",
            '<ol style="margin-top:8px;margin-bottom:8px;padding-left:25px;color:black;list-style-type:decimal;">',
        ),
        (
            r"<li>",
            '<li style="line-height:26px;color:rgb(1,1,1);font-weight:500;">',
        ),
        (
            r"<blockquote>",
            '<blockquote style="display:block;font-size:0.9em;overflow:auto;border-left:3px solid rgba(0,0,0,0.4);background:rgba(0,0,0,0.05);color:#6a737d;padding:10px 10px 10px 20px;margin:20px 0;border-left-color: #0e3a9d;background: #f9f9f9; color: #595959;">',
        ),
        (
            r"<blockquote>\s*<p[^>]*>",
            '<blockquote style="display:block;font-size:0.9em;overflow:auto;border-left:3px solid rgba(0,0,0,0.4);background:rgba(0,0,0,0.05);color:#6a737d;padding:10px 10px 10px 20px;margin:20px 0;"><p style="margin:0;color:black;line-height:26px;">',
        ),
        (
            r"<hr\s*/?>",
            '<hr style="height:1px;margin:10px 0;border:none;border-top:1px solid black;" />',
        ),
        (
            r"<table>",
            '<table style="display:table;text-align:left;">',
        ),
        (
            r"<th[^>]*>",
            '<th style="font-size:16px;border:1px solid #ccc;padding:5px 10px;text-align:left;font-weight:bold;background-color:#f0f0f0;">',
        ),
        (
            r"<td[^>]*>",
            '<td style="font-size:16px;border:1px solid #ccc;padding:5px 10px;text-align:left;">',
        ),
        (
            r"<code>",
            '<code style="font-size:14px;word-wrap:break-word;padding:2px 4px;border-radius:4px;margin:0 2px;color:#1e6bb8;background-color:rgba(27,31,35,.05);font-family:Operator Mono,Consolas,Monaco,Menlo,monospace;word-break:break-all;">',
        ),
        (
            r"<a\s+href=",
            '<a style="text-decoration:none;color:#1e6bb8;word-wrap:break-word;font-weight:bold;border-bottom:1px solid #1e6bb8;" href=',
        ),
        (
            r"<strong>",
            '<strong style="font-weight:bold;color:black;">',
        ),
        (
            r"<em>",
            '<em style="font-style:italic;color:black;">',
        ),
        (
            r"<img\s",
            '<img style="display:block;margin:0 auto;width:auto;max-width:100%;" ',
        ),
        (
            r"<del>",
            '<del style="font-style:italic;color:black;">',
        ),
        (
            r"<figcaption>",
            '<figcaption style="margin-top:5px;text-align:center;color:#888;font-size:14px;">',
        ),
        (
            r'<sup class="footnote-ref">',
            '<sup class="footnote-ref" style="color:#1e6bb8;font-weight:bold;">',
        ),
        (
            r'<span class="footnote-word">',
            '<span class="footnote-word" style="color:#1e6bb8;font-weight:bold;">',
        ),
    ]

    for pattern, repl in replacements:
        html = re.sub(pattern, repl, html, flags=re.IGNORECASE)

    wrapped = (
        '<section style="font-size:16px;color:black;line-height:1.6;word-spacing:0;letter-spacing:0;word-break:break-word;word-wrap:break-word;text-align:justify;font-family:Avenir, -apple-system-font, 微软雅黑, sans-serif;margin-top:-10px;">'
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
