#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

MODE="draft"
DATE_RANGE=""
TASK_EXTRA=""
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT_DIR/output}"
POLL_SECONDS="${POLL_SECONDS:-10}"
MAX_POLLS="${MAX_POLLS:-30}"
FORCE_GENERATE="0"
ILLUSTRATION_ENABLED="${ILLUSTRATION_ENABLED:-0}"
ILLUSTRATION_PROVIDER="${ILLUSTRATION_PROVIDER:-openai_compatible}"
ILLUSTRATION_MODEL="${ILLUSTRATION_MODEL:-gpt-image-1}"
ILLUSTRATION_COUNT="${ILLUSTRATION_COUNT:-3}"
ILLUSTRATION_STYLE="${ILLUSTRATION_STYLE:-专业医疗行业资讯插图，克制、简洁、无品牌标识、无疗效暗示}"
ILLUSTRATION_INSERT_MODE="${ILLUSTRATION_INSERT_MODE:-after_section}"
ILLUSTRATION_API_KEY="${ILLUSTRATION_API_KEY:-}"
ILLUSTRATION_BASE_URL="${ILLUSTRATION_BASE_URL:-}"
ILLUSTRATION_SIZE="${ILLUSTRATION_SIZE:-1536x1024}"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/run_weekly_wechat_pipeline.sh [--mode draft|publish] [--range YYYY-MM-DD,YYYY-MM-DD] [--task-extra "附加要求"] [--force-generate]
                                       [--illustration-enabled 0|1] [--illustration-provider xxx]
                                       [--illustration-model xxx] [--illustration-count N] [--illustration-style "风格"]

Description:
  1) 生成上周热点资讯 Markdown
  2) (可选) 按文章内容生成 AI 插图并回填 Markdown
  3) 渲染专业资讯 HTML
  4) 写入微信公众号草稿箱
  5) (可选) 自动发布并轮询发布状态

Default optimization:
  If today's article already exists in output/wechat_weekly_YYYYMMDD_*/, skip generation and reuse it.
  Use --force-generate to regenerate article.

Required env (.env):
  DASHSCOPE_API_KEY or OPENAI_API_KEY
  TAVILY_API_KEY
  WECHAT_APPID
  WECHAT_APPSECRET

One of:
  WECHAT_THUMB_MEDIA_ID
  WECHAT_COVER_IMAGE (local image path, used to upload and obtain media_id)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      MODE="$2"
      shift 2
      ;;
    --range)
      DATE_RANGE="$2"
      shift 2
      ;;
    --task-extra)
      TASK_EXTRA="$2"
      shift 2
      ;;
    --force-generate)
      FORCE_GENERATE="1"
      shift
      ;;
    --illustration-enabled)
      ILLUSTRATION_ENABLED="$2"
      shift 2
      ;;
    --illustration-provider)
      ILLUSTRATION_PROVIDER="$2"
      shift 2
      ;;
    --illustration-model)
      ILLUSTRATION_MODEL="$2"
      shift 2
      ;;
    --illustration-count)
      ILLUSTRATION_COUNT="$2"
      shift 2
      ;;
    --illustration-style)
      ILLUSTRATION_STYLE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown arg: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ "$MODE" != "draft" && "$MODE" != "publish" ]]; then
  echo "Invalid --mode: $MODE (expected draft|publish)" >&2
  exit 1
fi

if [[ "$ILLUSTRATION_ENABLED" != "0" && "$ILLUSTRATION_ENABLED" != "1" ]]; then
  echo "Invalid --illustration-enabled: $ILLUSTRATION_ENABLED (expected 0|1)" >&2
  exit 1
fi

if [[ -f ".env" ]]; then
  # shellcheck disable=SC1091
  source .env
fi

PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/.venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="${PYTHON_BIN_FALLBACK:-python3}"
fi

required_vars=("WECHAT_APPID" "WECHAT_APPSECRET")
for var in "${required_vars[@]}"; do
  if [[ -z "${!var:-}" ]]; then
    echo "Missing required env: $var" >&2
    exit 1
  fi
done

mkdir -p "$OUTPUT_DIR"
TS="$(date '+%Y%m%d_%H%M%S')"
TODAY_KEY="$(date '+%Y%m%d')"

LATEST_TODAY_DIR="$(
  find "$OUTPUT_DIR" -maxdepth 1 -type d -name "wechat_weekly_${TODAY_KEY}_*" 2>/dev/null | sort | tail -n 1
)"

REUSE_EXISTING_ARTICLE="0"
if [[ "$FORCE_GENERATE" != "1" && -n "$LATEST_TODAY_DIR" && -s "$LATEST_TODAY_DIR/week_report.md" ]]; then
  RUN_DIR="$LATEST_TODAY_DIR"
  REUSE_EXISTING_ARTICLE="1"
  echo "Reusing today's existing article: $RUN_DIR/week_report.md"
else
  RUN_DIR="$OUTPUT_DIR/wechat_weekly_$TS"
  mkdir -p "$RUN_DIR"
fi

if [[ -z "$DATE_RANGE" ]]; then
  DATE_RANGE="$("$PYTHON_BIN" - <<'PY'
from datetime import date, timedelta
today = date.today()
this_monday = today - timedelta(days=today.weekday())
last_monday = this_monday - timedelta(days=7)
last_sunday = this_monday - timedelta(days=1)
print(f"{last_monday.isoformat()},{last_sunday.isoformat()}")
PY
)"
fi

START_DATE="${DATE_RANGE%,*}"
END_DATE="${DATE_RANGE#*,}"
if [[ -z "$START_DATE" || -z "$END_DATE" || "$START_DATE" == "$END_DATE" && "$DATE_RANGE" != *","* ]]; then
  echo "Invalid --range. Expected format: YYYY-MM-DD,YYYY-MM-DD" >&2
  exit 1
fi

MD_FILE="$RUN_DIR/week_report.md"
if [[ "$REUSE_EXISTING_ARTICLE" == "1" ]]; then
  echo "[1/8] Skipping generation, using existing markdown..."
else
  echo "[1/8] Generating weekly article markdown..."
  TASK="使用互联网搜索公开信息，检索 ${START_DATE} 到 ${END_DATE} 的公开新闻、政策和行业资讯，主题聚焦慢特病院外市场数字化增长、处方药院外营销与合规。请严格按周报模板输出微信公众号文章：先给候选并筛选Top 5-8后成文；每条热点必须包含事件、影响、建议、来源（URL+日期）；语言专业克制；直接输出markdown正文，不要使用代码块包裹。${TASK_EXTRA}"
  "$PYTHON_BIN" index.py --task "$TASK" > "$MD_FILE"

  if grep -Eq '(^|\s)(Thought|Action|Observation)\s*:' "$MD_FILE"; then
    echo "Detected ReAct trace output, retrying with stricter instruction..."
    RETRY_TASK="请不要输出Thought/Action/Observation或任何中间推理。只输出最终的完整Markdown周报正文，严格使用既定模板，包含Top 5-8热点及来源URL+日期。时间范围：${START_DATE} 到 ${END_DATE}。主题：慢特病院外市场数字化增长、处方药院外营销与合规。${TASK_EXTRA}"
    "$PYTHON_BIN" index.py --task "$RETRY_TASK" > "$MD_FILE"
  fi

  if ! grep -Eq '^#\s+' "$MD_FILE"; then
    echo "Generated markdown seems invalid (missing H1 title). Please check:"
    sed -n '1,80p' "$MD_FILE"
    exit 1
  fi
fi

ILLUSTRATION_MD_FILE="$RUN_DIR/week_report_illustrated.md"
ILLUSTRATION_LOG_FILE="$RUN_DIR/illustration_log.json"
ILLUSTRATION_IMAGES_DIR="$RUN_DIR/images"
MD_SOURCE_FILE="$MD_FILE"

echo "[2/8] Getting WeChat access_token..."
TOKEN_RESP="$RUN_DIR/token_resp.json"
curl -sS -X POST "https://api.weixin.qq.com/cgi-bin/stable_token" \
  -H "Content-Type: application/json" \
  -d "{\"grant_type\":\"client_credential\",\"appid\":\"${WECHAT_APPID}\",\"secret\":\"${WECHAT_APPSECRET}\",\"force_refresh\":false}" \
  > "$TOKEN_RESP"

ACCESS_TOKEN="$("$PYTHON_BIN" - "$TOKEN_RESP" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], "r", encoding="utf-8"))
if data.get("access_token"):
    print(data["access_token"])
else:
    print("")
PY
)"

if [[ -z "$ACCESS_TOKEN" ]]; then
  echo "Failed to get access_token. Response:"
  cat "$TOKEN_RESP"
  exit 1
fi

if [[ "$ILLUSTRATION_ENABLED" == "1" ]]; then
  echo "[3/8] Generating AI illustrations..."
  set +e
  "$PYTHON_BIN" scripts/illustrate_article.py \
    --input-md "$MD_FILE" \
    --output-md "$ILLUSTRATION_MD_FILE" \
    --image-dir "$ILLUSTRATION_IMAGES_DIR" \
    --log-file "$ILLUSTRATION_LOG_FILE" \
    --enabled "$ILLUSTRATION_ENABLED" \
    --provider "$ILLUSTRATION_PROVIDER" \
    --model "$ILLUSTRATION_MODEL" \
    --count "$ILLUSTRATION_COUNT" \
    --style "$ILLUSTRATION_STYLE" \
    --insert-mode "$ILLUSTRATION_INSERT_MODE" \
    --api-key "$ILLUSTRATION_API_KEY" \
    --base-url "$ILLUSTRATION_BASE_URL" \
    --size "$ILLUSTRATION_SIZE" \
    --wechat-access-token "$ACCESS_TOKEN"
  ILLUSTRATION_EXIT_CODE=$?
  set -e
  if [[ "$ILLUSTRATION_EXIT_CODE" -eq 0 && -s "$ILLUSTRATION_MD_FILE" ]]; then
    MD_SOURCE_FILE="$ILLUSTRATION_MD_FILE"
    echo "Illustration completed, using markdown: $MD_SOURCE_FILE"
  else
    echo "WARNING: Illustration step failed, fallback to original markdown."
  fi
else
  echo "[3/8] Illustration disabled, skip."
fi

echo "[4/8] Rendering styled HTML..."
HTML_FILE="$RUN_DIR/week_report.html"
if [[ "$REUSE_EXISTING_ARTICLE" == "1" && -s "$HTML_FILE" ]]; then
  echo "Using existing rendered html: $HTML_FILE"
else
  "$PYTHON_BIN" scripts/render_week_report.py --input "$MD_SOURCE_FILE" --output "$HTML_FILE" >/dev/null
fi

THUMB_MEDIA_ID="${WECHAT_THUMB_MEDIA_ID:-}"
if [[ -z "$THUMB_MEDIA_ID" ]]; then
  if [[ -z "${WECHAT_COVER_IMAGE:-}" ]]; then
    echo "Need WECHAT_THUMB_MEDIA_ID or WECHAT_COVER_IMAGE in .env" >&2
    exit 1
  fi
  if [[ ! -f "$WECHAT_COVER_IMAGE" ]]; then
    echo "WECHAT_COVER_IMAGE not found: $WECHAT_COVER_IMAGE" >&2
    exit 1
  fi
  echo "[5/8] Uploading cover image to WeChat..."
  UPLOAD_RESP="$RUN_DIR/upload_resp.json"
  curl -sS -X POST "https://api.weixin.qq.com/cgi-bin/material/add_material?access_token=${ACCESS_TOKEN}&type=image" \
    -F "media=@${WECHAT_COVER_IMAGE}" \
    > "$UPLOAD_RESP"

  THUMB_MEDIA_ID="$("$PYTHON_BIN" - "$UPLOAD_RESP" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], "r", encoding="utf-8"))
print(data.get("media_id",""))
PY
)"

  if [[ -z "$THUMB_MEDIA_ID" ]]; then
    echo "Failed to upload cover image. Response:"
    cat "$UPLOAD_RESP"
    exit 1
  fi
else
  echo "[5/8] Using existing WECHAT_THUMB_MEDIA_ID..."
fi

echo "[6/8] Building draft payload..."
PAYLOAD_FILE="$RUN_DIR/draft_payload.json"
"$PYTHON_BIN" scripts/build_wechat_payload.py \
  --input "$MD_SOURCE_FILE" \
  --output "$PAYLOAD_FILE" \
  --thumb-media-id "$THUMB_MEDIA_ID" \
  --author "${WECHAT_AUTHOR:-}" \
  --content-source-url "${WECHAT_CONTENT_SOURCE_URL:-}" \
  --need-open-comment "${WECHAT_NEED_OPEN_COMMENT:-1}" \
  --only-fans-can-comment "${WECHAT_ONLY_FANS_CAN_COMMENT:-0}" \
  --show-cover-pic "${WECHAT_SHOW_COVER_PIC:-1}" \
  >/dev/null

echo "[7/8] Creating WeChat draft..."
DRAFT_RESP="$RUN_DIR/draft_add_resp.json"
curl -sS -X POST "https://api.weixin.qq.com/cgi-bin/draft/add?access_token=${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d @"$PAYLOAD_FILE" \
  > "$DRAFT_RESP"

DRAFT_MEDIA_ID="$("$PYTHON_BIN" - "$DRAFT_RESP" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], "r", encoding="utf-8"))
print(data.get("media_id",""))
PY
)"

if [[ -z "$DRAFT_MEDIA_ID" ]]; then
  echo "Draft creation failed. Response:"
  cat "$DRAFT_RESP"
  exit 1
fi

echo "Draft created successfully."
echo "draft_media_id=$DRAFT_MEDIA_ID"
echo "markdown=$MD_SOURCE_FILE"
echo "html=$HTML_FILE"
echo "payload=$PAYLOAD_FILE"
if [[ -f "$ILLUSTRATION_LOG_FILE" ]]; then
  echo "illustration_log=$ILLUSTRATION_LOG_FILE"
fi
if [[ -d "$ILLUSTRATION_IMAGES_DIR" ]]; then
  echo "images_dir=$ILLUSTRATION_IMAGES_DIR"
fi

if [[ "$MODE" == "draft" ]]; then
  echo "Mode=draft, skipping publish."
  exit 0
fi

echo "Submitting draft for publish..."
PUBLISH_SUBMIT_RESP="$RUN_DIR/freepublish_submit_resp.json"
curl -sS -X POST "https://api.weixin.qq.com/cgi-bin/freepublish/submit?access_token=${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"article_id\":\"${DRAFT_MEDIA_ID}\"}" \
  > "$PUBLISH_SUBMIT_RESP"

PUBLISH_ID="$("$PYTHON_BIN" - "$PUBLISH_SUBMIT_RESP" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], "r", encoding="utf-8"))
print(data.get("publish_id",""))
PY
)"

if [[ -z "$PUBLISH_ID" ]]; then
  echo "Publish submit failed. Response:"
  cat "$PUBLISH_SUBMIT_RESP"
  exit 1
fi

echo "publish_id=$PUBLISH_ID"
echo "Polling publish status (every ${POLL_SECONDS}s, max ${MAX_POLLS} times)..."

for ((i=1; i<=MAX_POLLS; i++)); do
  STATUS_FILE="$RUN_DIR/freepublish_get_${i}.json"
  curl -sS -X POST "https://api.weixin.qq.com/cgi-bin/freepublish/get?access_token=${ACCESS_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"publish_id\":\"${PUBLISH_ID}\"}" \
    > "$STATUS_FILE"

  STATUS_LINE="$("$PYTHON_BIN" - "$STATUS_FILE" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], "r", encoding="utf-8"))
status = data.get("publish_status")
article_id = data.get("article_id","")
publish_status = data.get("publish_status", "")
fail_idx = data.get("fail_idx", [])
print(f"{publish_status}|{article_id}|{fail_idx}")
PY
)"

PUBLISH_STATUS="${STATUS_LINE%%|*}"
REST="${STATUS_LINE#*|}"
ARTICLE_ID="${REST%%|*}"
FAIL_IDX="${REST#*|}"

echo "poll=$i publish_status=${PUBLISH_STATUS} article_id=${ARTICLE_ID}"

if [[ "$PUBLISH_STATUS" == "0" ]]; then
  echo "Publish succeeded."
  echo "article_id=${ARTICLE_ID}"
  exit 0
fi

if [[ "$PUBLISH_STATUS" == "2" || "$PUBLISH_STATUS" == "3" || "$PUBLISH_STATUS" == "5" || "$PUBLISH_STATUS" == "6" ]]; then
  echo "Publish failed with status=${PUBLISH_STATUS}, fail_idx=${FAIL_IDX}"
  echo "Check detail: $STATUS_FILE"
  exit 1
fi

  sleep "$POLL_SECONDS"
done

echo "Publish status polling timed out. Please check later with publish_id=${PUBLISH_ID}."
exit 1
