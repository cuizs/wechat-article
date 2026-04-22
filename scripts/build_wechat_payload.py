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
            '<h1 style="text-align:center;background-image:url(https://my-wechat.mdnice.com/mdnice/mountain_2_20191028221337.png);background-position:center top;background-repeat:no-repeat;background-size:95px;line-height:95px;margin-top:38px;margin-bottom:10px;font-size:20px;color:rgb(60,112,198);border-bottom:2px solid #3C7076;">',
        ),
        (
            r"<h2>",
            '<h2 style="display:block;text-align:center;background-image:url(https://my-wechat.mdnice.com/mdnice/mountain_2_20191028221337.png);background-position:center center;background-repeat:no-repeat;background-size:63px;margin-top:38px;margin-bottom:10px;line-height:42px;font-size:18px;color:rgb(60,112,198);">',
        ),
        (
            r"<h3>",
            '<h3 style="font-size:16px;font-weight:bold;color:rgb(60,112,198);padding-left:23px;background-image:url(https://my-wechat.mdnice.com/mdnice/mountain_1_20191028221337.png);background-repeat:no-repeat;background-size:15px 15px;background-position:left center;">',
        ),
        (
            r"<h4>",
            '<h4 style="font-size:16px;font-weight:bold;color:rgb(60,112,198);margin:14px 0 8px;">',
        ),
        (
            r"<h5>",
            '<h5 style="font-size:15px;font-weight:bold;color:rgb(60,112,198);margin:12px 0 8px;">',
        ),
        (
            r"<h6>",
            '<h6 style="font-size:14px;font-weight:bold;color:rgb(60,112,198);margin:10px 0 6px;">',
        ),
        (
            r"<p>",
            '<p style="padding-top:23px;color:rgb(74,74,74);line-height:1.75em;margin:0;">',
        ),
        (
            r"<ul>",
            '<ul style="margin:10px 0 14px 0;padding-left:22px;">',
        ),
        (
            r"<ol>",
            '<ol style="margin:10px 0 14px 0;padding-left:22px;">',
        ),
        (
            r"<li>",
            '<li style="font-size:16px;line-height:1.75em;color:rgb(74,74,74);margin:6px 0;">',
        ),
        (
            r"<blockquote>\s*<p[^>]*>",
            '<blockquote style="padding:15px 20px;line-height:27px;background-color:rgb(239,239,239);border-left:none;display:block;margin:16px 0;"><p style="padding:0;font-size:15px;color:rgb(89,89,89);margin:0;">',
        ),
        (
            r"<blockquote>",
            '<blockquote style="padding:15px 20px;line-height:27px;background-color:rgb(239,239,239);border-left:none;display:block;margin:16px 0;">',
        ),
        (
            r"<hr\s*/?>",
            '<hr style="height:1px;padding:0;border:none;text-align:center;background-image:linear-gradient(to right,rgba(60,122,198,0),rgba(60,122,198,0.75),rgba(60,122,198,0));margin:20px 0;" />',
        ),
        (
            r"<table>",
            '<table style="border-collapse:collapse;width:100%;margin:14px 0;font-size:14px;">',
        ),
        (
            r"<th[^>]*>",
            '<th style="font-size:14px;padding:6px 8px;border:1px solid #d6d6d6;">',
        ),
        (
            r"<td[^>]*>",
            '<td style="font-size:14px;padding:6px 8px;border:1px solid #d6d6d6;">',
        ),
        (
            r"<code>",
            '<code style="color:rgb(60,112,198);">',
        ),
        (
            r"<a\s+href=",
            '<a style="color:rgb(60,112,198);text-decoration:none;border-bottom:1px solid rgb(60,112,198);" href=',
        ),
        (
            r"<strong>",
            '<strong style="line-height:1.75em;color:rgb(74,74,74);">',
        ),
        (
            r"<img\s",
            '<img style="border-radius:4px;margin-bottom:25px;" ',
        ),
    ]

    for pattern, repl in replacements:
        html = re.sub(pattern, repl, html, flags=re.IGNORECASE)

    wrapped = (
        '<section style="line-height:1.6;letter-spacing:.034em;color:rgb(63,63,63);font-size:16px;word-break:break-all;">'
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
