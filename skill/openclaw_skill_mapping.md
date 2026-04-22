# OpenClaw Skill 参数映射说明

本文说明 `skill/openclaw_skill_spec.json` 中输入参数，如何映射到运行时环境变量与脚本参数。

## 1) Input -> CLI 参数映射

- `mode` -> `--mode {{mode}}`
- `date_range` -> `--range {{date_range}}`
- `task_extra` -> `--task-extra "{{task_extra}}"`
- `force_generate=true` -> `--force-generate`
- `illustration_enabled` -> `--illustration-enabled {{illustration_enabled}}`
- `illustration_provider` -> `--illustration-provider {{illustration_provider}}`
- `illustration_model` -> `--illustration-model {{illustration_model}}`
- `illustration_count` -> `--illustration-count {{illustration_count}}`
- `illustration_style` -> `--illustration-style "{{illustration_style}}"`

## 2) Input -> ENV 参数映射（建议）

为减少 `command_template` 长度，推荐在 skill 平台中将如下输入直接注入环境变量：

- `llm_provider` -> `LLM_PROVIDER`
- `llm_model` -> `LLM_MODEL`

插图相关也可改为环境变量注入（与 CLI 二选一或混用）：

- `illustration_enabled` -> `ILLUSTRATION_ENABLED`
- `illustration_provider` -> `ILLUSTRATION_PROVIDER`
- `illustration_model` -> `ILLUSTRATION_MODEL`
- `illustration_count` -> `ILLUSTRATION_COUNT`
- `illustration_style` -> `ILLUSTRATION_STYLE`

## 3) Secrets 注入建议

建议将以下 secrets 仅通过平台注入，不写入仓库：

- `LLM_API_KEY`
- `LLM_BASE_URL`
- `TAVILY_API_KEY`
- `ILLUSTRATION_API_KEY`
- `ILLUSTRATION_BASE_URL`
- `WECHAT_APPID`
- `WECHAT_APPSECRET`
- `WECHAT_THUMB_MEDIA_ID` 或 `WECHAT_COVER_IMAGE`

## 4) 最小可用配置（草稿模式）

最低必需：

- `mode=draft`
- `LLM_PROVIDER=openclaw`
- `LLM_MODEL=<chat model>`
- `LLM_BASE_URL=<endpoint>/v1`
- `LLM_API_KEY=<secret>`
- `TAVILY_API_KEY=<secret>`
- `WECHAT_APPID=<secret>`
- `WECHAT_APPSECRET=<secret>`
- `WECHAT_THUMB_MEDIA_ID=<secret>`（或 `WECHAT_COVER_IMAGE`）

## 5) 输出字段解析建议

脚本标准输出中，建议解析以下 key：

- `draft_media_id=...`
- `publish_id=...`（publish 模式）
- `article_id=...`（publish 成功）
- `markdown=...`
- `html=...`
- `payload=...`
- `illustration_log=...`
- `images_dir=...`

若日志出现：

- `WARNING: Illustration step failed, fallback to original markdown.`

代表插图降级，主流程仍成功。
