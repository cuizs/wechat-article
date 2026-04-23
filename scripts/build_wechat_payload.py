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
            '<h1 style="font-size:2.1em;line-height:1.1em;padding-top:16px;padding-bottom:10px;margin-bottom:4px;border-bottom:1px solid #c99833;">',
        ),
        (
            r"<h2>",
            '<h2 style="line-height:1.5em;margin-top:2.2em;margin-bottom:35px;display:inline-block;font-weight:bold;background:linear-gradient(#0e3a9d 90%, #ffb906 10%);color:#ffffff;padding:2px 13px 2px;margin-right:3px;height:50%;">',
        ),
        (
            r"<h3>",
            '<h3 style="line-height:1.4;padding-top:10px;margin:10px 0 5px;color:#515151;font-weight:700;font-size:1em;">',
        ),
        (
            r"<h4>",
            '<h4 style="line-height:1.5em;margin-top:2.2em;margin-bottom:4px;">',
        ),
        (
            r"<h5>",
            '<h5 style="line-height:1.5em;margin-top:2.2em;margin-bottom:4px;">',
        ),
        (
            r"<h6>",
            '<h6 style="line-height:1.5em;margin-top:2.2em;margin-bottom:4px;">',
        ),
        (
            r"<p>",
            '<p style="margin:0 0 20px;padding:0;line-height:1.8em;color:#3a3a3a;">',
        ),
        (
            r"<ul>",
            '<ul>',
        ),
        (
            r"<ol>",
            '<ol>',
        ),
        (
            r"<li>",
            '<li>',
        ),
        (
            r"<blockquote>",
            '<blockquote style="border-left-color:#ffb906;background:#fff5e3;color:#595959;">',
        ),
        (
            r"<hr\s*/?>",
            '<hr style="border-top:1px solid #0e3a9d;margin:20px 0;" />',
        ),
        (
            r"<table>",
            '<table>',
        ),
        (
            r"<th[^>]*>",
            '<th style="text-align:center;">',
        ),
        (
            r"<td[^>]*>",
            '<td style="text-align:center;">',
        ),
        (
            r"<code>",
            '<code style="color:#9b6e23;background-color:#fff5e3;padding:3px;margin:3px;">',
        ),
        (
            r"<a\s+href=",
            '<a style="border:none;text-decoration:none;color:#0e3a9d;" href=',
        ),
        (
            r"<strong>",
            '<strong>',
        ),
        (
            r"<em>",
            '<em>',
        ),
        (
            r"<img\s",
            '<img style="width:100%;border-radius:5px;display:block;margin-bottom:15px;height:auto;" ',
        ),
        (
            r"<del>",
            '<del style="color:#d19826;">',
        ),
        (
            r"<figcaption>",
            '<figcaption style="color:#dda52d;font-size:14px;">',
        ),
        (
            r'<sup class="footnote-ref">',
            '<sup class="footnote-ref" style="color:#dda52d;margin:2px;padding:3px;">',
        ),
    ]

    for pattern, repl in replacements:
        html = re.sub(pattern, repl, html, flags=re.IGNORECASE)

    wrapped = (
        '<section style="word-break:break-all;">'
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
