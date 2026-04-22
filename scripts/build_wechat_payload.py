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


'''
/*初始化格式*/

#nice {
  line-height: 1.6;
  letter-spacing: .034em;
  color: rgb(63, 63, 63);
  font-size: 16px;
  word-break:all;
}

#nice p {
  padding-top: 23px;
  color: rgb(74,74,74);
  line-height: 1.75em;
}

/* 一级标题 */
#nice h1 {
  text-align:center;
  background-image: url(https://my-wechat.mdnice.com/mdnice/mountain_2_20191028221337.png); 
  background-position: center top;
  background-repeat: no-repeat;
  background-size: 95px;
  line-height:95px;
  margin-top: 38px;
  margin-bottom: 10px;
}

/* 一级标题内容 */
#nice h1 .content {
  font-size: 20px;
  color: rgb(60, 112, 198);
  border-bottom:2px solid #3C7076;
}

/* 一级标题修饰 请参考有实例的主题 */
#nice h1:after {
}
 
/* 二级标题 */
#nice h2 {
  display:block;
  text-align:center;
  background-image: url(https://my-wechat.mdnice.com/mdnice/mountain_2_20191028221337.png); 
  background-position: center center;
  background-repeat: no-repeat;
  background-attachment: initial;
  background-origin: initial;
  background-clip: initial;
  background-size: 63px;
  margin-top: 38px;
  margin-bottom: 10px;
}

/*二级标题伪元素*/
#nice h2:before {
}

/* 二级标题内容 */
#nice h2 .content {
  text-align:center;
  display: inline-block;
  height: 38px;
  line-height: 42px;
  color: rgb(60, 112, 198);
  background-position: left center;
  background-repeat: no-repeat;
  background-attachment: initial;
  background-origin: initial;
  background-clip: initial;
  background-size: 63px;
  margin-top: 38px;
  font-size:18px;
  margin-bottom: 10px;
}

/* 三级标题 */
#nice h3:before {
  content: "";
  background-image:url(https://my-wechat.mdnice.com/mdnice/mountain_1_20191028221337.png);
  background-size:15px 15px;
  display: inline-block;
  width: 15px;
  height: 15px;
  line-height:15px;
  margin-bottom:-1px;
}

#nice h3 {
}

/* 三级标题内容 */
#nice h3 .content {
  font-size:16px;
  font-weight:bold;
  display:inline-block;
  margin-left:8px;
  color:rgb(60,112,198);
}

/* 三级标题修饰 请参考有实例的主题 */
#nice h3:after {
}

/* 列表内容 */
#nice li {
}

/* 引用
 * 左边缘颜色 border-left-color:black;
 * 背景色 background:gray;
 */
#nice blockquote {
  padding: 15px 20px;
  line-height: 27px;
  background-color: rgb(239, 239, 239);
  border-left:none;
  display:block;
}

/* 引用文字 */
#nice blockquote p {
  padding: 0px;
  font-size:15px;
  color:rgb(89,89,89);
}

/* 链接 */
#nice a {
  color: rgb(60, 112, 198);
  text-decoration:none;
  border-bottom: 1px solid rgb(60, 112, 198);
}

/* 加粗 */
#nice strong {
  line-height: 1.75em;
  color: rgb(74,74,74);
}

/* 斜体 */
#nice em {
}

/* 加粗斜体 */
#nice em strong {
  color:rgb(248,57,41);
  letter-spacing:0.3em;
}

/* 删除线 */
#nice del {
}
 
/* 分割线 */
#nice hr {
  height:1px;
  padding:0;
  border:none;
  text-align:center;
  background-image:linear-gradient(to right,rgba(60,122,198,0),rgba(60,122,198,0.75),rgba(60,122,198,0));
}

/* 图片 */
#nice img {
    border-radius:4px;
    margin-bottom:25px;
}

/* 图片描述文字 */
#nice figcaption {
  display:block;
  font-size:12px;
  font-family:PingFangSC-Light;
}

/* 行内代码 */
#nice p code, #nice li code {
	color: rgb(60, 112, 198);;
}

/* 非微信代码块
 * 代码块不换行 display:-webkit-box !important;
 * 代码块换行 display:block;
 */
#nice pre code {
}

/* 表格内的单元格
 * 字体大小 font-size: 16px;
 * 边框 border: 1px solid #ccc;
 * 内边距 padding: 5px 10px;
 */
#nice table tr th,
#nice table tr td {
  font-size: 14px;
}

#nice .footnotes{
  padding-top: 8px;
}

/* 脚注文字 */
#nice .footnote-word {
  color: rgb(60, 112, 198);
}

/* 脚注上标 */
#nice .footnote-ref {
  color: rgb(60, 112, 198);
}

/* 脚注超链接样式 */
#nice .footnote-item em {
  color: rgb(60, 112, 198);
  font-size:13px;
  font-style:normal;
  border-bottom-color:1px dashed rgb(60, 112, 198); 
}

/* "参考资料"四个字 
 * 内容 content: "参考资料";
 */
#nice .footnotes-sep:before {
  background-image: none;
  background-size: none;
  display: block;
  width: auto;
  height: auto;
}

/* 参考资料编号 */
#nice .footnote-num {
  color: rgb(60, 112, 198);
}

/* 参考资料文字 */
#nice .footnote-item p {
  color: rgb(60, 112, 198);
  font-weight:bold;
}

/* 参考资料超链接 */
#nice .footnote-item a {
  color:rgb(60, 112, 198);
}

/* 参考资料解释 */
#nice .footnote-item p em {
  font-size:14px;
  font-weight:normal;
  border-bottom:1px dashed rgb(60, 112, 198);
}

/* 行间公式
 * 最大宽度 max-width: 300% !important;
 */
#nice .block-equation svg {
  
}

/* 行内公式*/
#nice .inline-equation svg {  
}

'''

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
        '<section style="line-height: 1.6;letter-spacing: .034em;color: rgb(63, 63, 63);font-size: 16px;word-break:all;">'
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
