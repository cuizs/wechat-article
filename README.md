# ReAct Agent Demo

一个基于 LangChain 的最小 ReAct Agent 示例，支持：

- `Search`：互联网搜索（Tavily）
- `Calculate`：安全数学表达式计算
- `ReadFile`：读取项目工作区内文件
- `WriteFile`：写入项目工作区内文件

## 1. 安装依赖

```bash
pip install langchain langchain-openai langchain-community python-dotenv markdown
```

## 2. 配置 `.env`

复制模板文件并填写密钥：

```bash
cp .env.example .env
```

`.env` 示例：

```env
DASHSCOPE_API_KEY=your_api_key_here
TAVILY_API_KEY=tvly-your_tavily_key_here
OPENAI_BASE_URL=https://coding.dashscope.aliyuncs.com/v1
MODEL_NAME=glm-5
MODEL_TEMPERATURE=0.5
WECHAT_APPID=wx_your_appid
WECHAT_APPSECRET=your_appsecret
WECHAT_AUTHOR=数字化增长智库
WECHAT_THUMB_MEDIA_ID=
WECHAT_COVER_IMAGE=
```

说明：

- 程序会在启动时自动读取项目根目录下的 `.env`
- `DASHSCOPE_API_KEY` 和 `OPENAI_API_KEY` 二选一即可
- `TAVILY_API_KEY` 用于 `Search` 工具联网检索
- 微信发布需要配置 `WECHAT_APPID`、`WECHAT_APPSECRET`，以及封面图参数（`WECHAT_THUMB_MEDIA_ID` 或 `WECHAT_COVER_IMAGE` 二选一）
- `.env` 已在 `.gitignore` 中，避免提交到仓库

### 使用 OpenClaw 模型（推荐）

可以通过统一的 `LLM_*` 配置切换模型提供方。在 openclaw skill 中，建议由平台注入这些变量（不要写死到仓库）：

```env
LLM_PROVIDER=openclaw
LLM_MODEL=your-openclaw-chat-model
LLM_BASE_URL=https://your-openclaw-endpoint/v1
LLM_API_KEY=your-openclaw-key
MODEL_TEMPERATURE=0.5
```

兼容说明：

- `index.py` 会优先读取 `LLM_*`；
- 当 `LLM_PROVIDER=openclaw` 时，也兼容 `OPENCLAW_API_KEY/OPENCLAW_BASE_URL/OPENCLAW_MODEL`；
- 若未设置 `LLM_PROVIDER`，默认走现有 dashscope/openai-compatible 路由。

## 3. 运行

单次任务：

```bash
python index.py --task "使用前端技术，开发一个贪吃蛇游戏，内容生成到snake/index.html文件中"
```

交互模式：

```bash
python index.py
```

输入 `exit` 或 `quit` 退出。

## 4. 渲染专业资讯样式（Markdown -> HTML）

先把 Agent 结果保存为 Markdown：

```bash
mkdir -p output
python index.py --task "请基于web_search生成上一周热点资讯微信公众号文章，聚焦慢特病院外市场数字化增长、处方药院外营销与合规，严格按模板输出，直接输出markdown正文，不要使用代码块包裹" > output/week_report.md
```

再渲染为专业资讯风格 HTML：

```bash
python scripts/render_week_report.py --input output/week_report.md --output output/week_report.html
```

样式模板在：

- `templates/week_report.html`

你可以按品牌规范调整颜色、字体、间距，渲染脚本会自动套用。

## 5. 一键执行“抓取 -> 生成 -> 草稿箱 -> 发布”

脚本：

- `scripts/run_weekly_wechat_pipeline.sh`

能力：

- 自动确定上周日期范围（周一到周日）
- 若当天已生成过文章，默认复用当天最新 `week_report.md`，跳过“重新生成文章”
- 调用 Agent 检索并生成周报 Markdown
- 可选按内容生成 AI 插图并自动回填到 Markdown
- 渲染专业资讯风格 HTML
- 发布到微信公众号草稿箱
- 可选自动发布，并轮询发布状态

仅入草稿箱：

```bash
./scripts/run_weekly_wechat_pipeline.sh --mode draft
```

提交发布并轮询：

```bash
./scripts/run_weekly_wechat_pipeline.sh --mode publish
```

自定义日期范围：

```bash
./scripts/run_weekly_wechat_pipeline.sh --mode draft --range 2026-04-06,2026-04-12
```

附加写作要求：

```bash
./scripts/run_weekly_wechat_pipeline.sh --task-extra "请加强政策解读深度，并突出DTP渠道动作"
```

强制重新生成当天文章：

```bash
./scripts/run_weekly_wechat_pipeline.sh --mode draft --force-generate
```

启用 AI 插图（并指定模型）：

```bash
./scripts/run_weekly_wechat_pipeline.sh --mode draft \
  --illustration-enabled 1 \
  --illustration-provider openclaw \
  --illustration-model your-image-model \
  --illustration-count 4 \
  --illustration-style "医疗行业资讯插图，克制、简洁、专业"
```

运行产物会输出到：

- `output/wechat_weekly_时间戳/`

其中包含 markdown、html、微信接口响应、最终 payload，以及插图日志与图片目录，便于审计与复盘。

插图相关产物：

- `week_report_illustrated.md`：回填插图后的 Markdown
- `illustration_log.json`：插图执行日志（成功/失败、上传结果、错误原因）
- `images/`：生成的本地图片文件

说明（重要）：

- 微信公众号会清洗 `<style>`、`class`、外链样式和部分复杂标签。
- 本项目发布到公众号时使用 `scripts/build_wechat_payload.py` 生成“内联样式 HTML”，而不是直接复用 `templates/week_report.html` 的页面样式。
- 若你修改了网页模板样式，公众号端不会自动等效；需要同步调整 `build_wechat_payload.py` 中的内联样式规则。
- 插图步骤默认可降级：即使生成或微信正文图上传失败，也会回退到纯文字版本继续创建草稿。
- 若需要在公众号正文稳定展示图片，建议为插图步骤提供可用的 `ILLUSTRATION_API_KEY/ILLUSTRATION_BASE_URL`，并确保微信 token 获取成功。

## 6. 最短联调命令（验收）

### 本地联调（draft + openclaw + 插图）

先在环境中准备好 `LLM_*`、`WECHAT_*`、`TAVILY_API_KEY`、`ILLUSTRATION_*`，然后执行：

```bash
./scripts/run_weekly_wechat_pipeline.sh --mode draft --illustration-enabled 1 --illustration-provider openclaw --illustration-model your-image-model
```

验收关键输出：

- `draft_media_id=...`
- `markdown=...`
- `html=...`
- `payload=...`
- `illustration_log=...`（开启插图时）

### Skill 联调（最小）

建议在 skill 平台中设置：

- 输入：`mode=draft`、`illustration_enabled=true`
- 环境变量：`LLM_PROVIDER=openclaw`、`LLM_MODEL=...`
- secrets：`LLM_API_KEY`、`LLM_BASE_URL`、`TAVILY_API_KEY`、`WECHAT_APPID`、`WECHAT_APPSECRET`、封面图相关

然后调用入口：

```bash
./scripts/run_weekly_wechat_pipeline.sh --mode draft --illustration-enabled 1
```

参数映射详情见：

- `skill/openclaw_skill_mapping.md`
- `skill/openclaw_skill_spec.json`
