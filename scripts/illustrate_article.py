from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any
from urllib import error, request


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate and inject AI illustrations for markdown article")
    parser.add_argument("--input-md", required=True, help="Input markdown path")
    parser.add_argument("--output-md", required=True, help="Output markdown path")
    parser.add_argument("--image-dir", required=True, help="Output image directory")
    parser.add_argument("--log-file", required=True, help="Illustration log json path")
    parser.add_argument("--enabled", type=int, choices=[0, 1], default=1)
    parser.add_argument("--provider", default=os.getenv("ILLUSTRATION_PROVIDER", "openai_compatible"))
    parser.add_argument("--model", default=os.getenv("ILLUSTRATION_MODEL", "gpt-image-1"))
    parser.add_argument("--count", type=int, default=int(os.getenv("ILLUSTRATION_COUNT", "3")))
    parser.add_argument(
        "--style",
        default=os.getenv("ILLUSTRATION_STYLE", "专业医疗行业资讯插图，克制、简洁、无品牌标识、无疗效暗示"),
    )
    parser.add_argument(
        "--insert-mode",
        choices=["after_section", "append_gallery"],
        default=os.getenv("ILLUSTRATION_INSERT_MODE", "after_section"),
    )
    parser.add_argument("--api-key", default=os.getenv("ILLUSTRATION_API_KEY", ""))
    parser.add_argument("--base-url", default=os.getenv("ILLUSTRATION_BASE_URL", ""))
    parser.add_argument("--size", default=os.getenv("ILLUSTRATION_SIZE", "1536x1024"))
    parser.add_argument("--wechat-access-token", default="")
    return parser.parse_args()


def extract_slots(markdown_text: str, count: int) -> list[dict[str, str]]:
    slots: list[dict[str, str]] = []
    h1 = re.search(r"^#\s+(.+)$", markdown_text, flags=re.MULTILINE)
    if h1:
        slots.append({"title": h1.group(1).strip(), "kind": "cover"})

    section_pattern = re.compile(r"^###\s+(.+)$", flags=re.MULTILINE)
    for m in section_pattern.finditer(markdown_text):
        title = m.group(1).strip()
        if "热点" in title or re.match(r"^\d+\)", title):
            slots.append({"title": title, "kind": "hotspot"})

    if "政策与合规解读" in markdown_text:
        slots.append({"title": "政策与合规解读", "kind": "policy"})

    if count <= 0:
        return []
    return slots[:count]


def build_prompt(slot: dict[str, str], style: str) -> str:
    kind = slot["kind"]
    title = slot["title"]
    aspect = "16:9" if kind == "cover" else "4:3"
    return (
        f"请生成一张中文资讯配图概念图。主题：{title}。"
        f"画面风格：{style}。"
        "约束：不要出现任何品牌logo、真实患者肖像、药品包装、疗效承诺、夸张医疗暗示。"
        f"构图比例建议：{aspect}。画面尽量少文字或不含文字。"
    )


def _http_post_json(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    req = request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    with request.urlopen(req, timeout=90) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body)


def generate_image_openai_compatible(
    *,
    base_url: str,
    api_key: str,
    model: str,
    prompt: str,
    size: str,
    output_path: Path,
) -> str:
    if not base_url:
        raise ValueError("缺少 ILLUSTRATION_BASE_URL（或 --base-url）")
    if not api_key:
        raise ValueError("缺少 ILLUSTRATION_API_KEY（或 --api-key）")
    endpoint = base_url.rstrip("/") + "/images/generations"
    payload = {"model": model, "prompt": prompt, "size": size}
    data = _http_post_json(endpoint, payload, {"Authorization": f"Bearer {api_key}"})

    entries = data.get("data") or []
    if not entries:
        raise ValueError(f"图片接口返回无 data: {data}")
    item = entries[0]
    image_b64 = item.get("b64_json")
    image_url = item.get("url")
    if image_b64:
        output_path.write_bytes(base64.b64decode(image_b64))
        return str(output_path)
    if image_url:
        with request.urlopen(image_url, timeout=90) as resp:
            output_path.write_bytes(resp.read())
        return str(output_path)
    raise ValueError(f"图片接口返回既无 b64_json 也无 url: {item}")


def upload_image_to_wechat(image_path: Path, access_token: str) -> tuple[str, str]:
    if not access_token:
        return "", "missing_access_token"
    url = f"https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token={access_token}"
    try:
        result = subprocess.run(
            [
                "curl",
                "-sS",
                "-X",
                "POST",
                url,
                "-F",
                f"media=@{image_path}",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        return "", f"curl_failed:{stderr or str(exc)}"

    try:
        data = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return "", f"invalid_json_response:{(result.stdout or '').strip()[:200]}"

    url_value = str(data.get("url", "")).strip()
    if url_value:
        return url_value, ""

    errcode = data.get("errcode")
    errmsg = data.get("errmsg", "")
    if errcode is not None:
        return "", f"wechat_upload_error errcode={errcode} errmsg={errmsg}"
    return "", "wechat_upload_missing_url"


def insert_images(markdown_text: str, items: list[dict[str, str]], mode: str) -> str:
    if not items:
        return markdown_text
    if mode == "append_gallery":
        lines = ["", "## AI 插图", ""]
        for idx, item in enumerate(items, start=1):
            lines.append(f"### 图{idx}：{item['title']}")
            lines.append(f"![{item['title']}]({item['ref']})")
            lines.append("")
        return markdown_text.rstrip() + "\n" + "\n".join(lines)

    rendered = markdown_text
    for item in items:
        heading = item["heading"]
        escaped = re.escape(heading)
        pattern = rf"(^###\s+{escaped}\s*$)"
        replacement = r"\1" + f"\n\n![{item['title']}]({item['ref']})\n"
        rendered, replaced = re.subn(pattern, replacement, rendered, count=1, flags=re.MULTILINE)
        if replaced == 0:
            rendered = rendered.rstrip() + f"\n\n![{item['title']}]({item['ref']})\n"
    return rendered


def main() -> None:
    args = parse_args()
    input_md = Path(args.input_md)
    output_md = Path(args.output_md)
    image_dir = Path(args.image_dir)
    log_file = Path(args.log_file)

    image_dir.mkdir(parents=True, exist_ok=True)
    markdown_text = input_md.read_text(encoding="utf-8")

    log_payload: dict[str, Any] = {
        "enabled": bool(args.enabled),
        "provider": args.provider,
        "model": args.model,
        "count": args.count,
        "insert_mode": args.insert_mode,
        "items": [],
        "success": 0,
        "failed": 0,
        "wechat_uploaded": 0,
        "wechat_failed": 0,
    }

    if args.enabled != 1:
        output_md.write_text(markdown_text, encoding="utf-8")
        log_file.write_text(json.dumps(log_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(str(output_md.resolve()))
        return

    slots = extract_slots(markdown_text, args.count)
    rendered_items: list[dict[str, str]] = []

    for idx, slot in enumerate(slots, start=1):
        image_name = f"illustration_{idx:02d}.png"
        image_path = image_dir / image_name
        prompt = build_prompt(slot, args.style)
        item_log: dict[str, Any] = {
            "title": slot["title"],
            "kind": slot["kind"],
            "prompt": prompt,
            "image_path": str(image_path),
            "status": "pending",
        }
        try:
            if args.provider in {"openai_compatible", "openclaw", "openai"}:
                generate_image_openai_compatible(
                    base_url=args.base_url,
                    api_key=args.api_key,
                    model=args.model,
                    prompt=prompt,
                    size=args.size,
                    output_path=image_path,
                )
            else:
                raise ValueError(f"暂不支持的 provider: {args.provider}")

            wechat_url, wechat_error = upload_image_to_wechat(image_path, args.wechat_access_token)
            item_log["wechat_url"] = wechat_url
            item_log["wechat_upload_error"] = wechat_error
            if wechat_url:
                log_payload["wechat_uploaded"] += 1
            elif args.wechat_access_token:
                # 有 token 但上传失败，降级使用本地路径，不中断流程
                log_payload["wechat_failed"] += 1
            item_log["status"] = "ok"
            ref = wechat_url or str(image_path)
            rendered_items.append(
                {"title": slot["title"], "heading": slot["title"], "ref": ref}
            )
            log_payload["success"] += 1
        except (ValueError, error.URLError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
            item_log["status"] = "failed"
            item_log["error"] = str(exc)
            log_payload["failed"] += 1
        log_payload["items"].append(item_log)

    illustrated_md = insert_images(markdown_text, rendered_items, args.insert_mode)
    output_md.write_text(illustrated_md, encoding="utf-8")
    log_file.write_text(json.dumps(log_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(output_md.resolve()))


if __name__ == "__main__":
    main()
