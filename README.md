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

运行产物会输出到：

- `output/wechat_weekly_时间戳/`

其中包含 markdown、html、微信接口响应、最终 payload，便于审计与复盘。
