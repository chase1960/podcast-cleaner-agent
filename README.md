# podcast-cleaner-agent · 播客清洗与知识树 Agent

把通勤路上听的播客，自动变成一篇结构清晰的笔记，并按主题汇入你的**个人知识树**；每天早上推送一份可读的昨日回顾简报。

## 这是什么

一个可独立运行的 Python Agent 框架。你告诉它播客名称（可选单集标题或链接），它会：

1. **取稿**：优先解析 RSS feed 与节目公开 shownotes（小宇宙等平台）；拿不到全文时回退到你粘贴的文字稿 / 音频转写稿。
2. **提炼**：调用 LLM 输出结构化结果——一句话摘要、核心要点、金句、标签、所属分类。
3. **入树**：笔记写入飞书 Wiki 对应分类目录，并与历史同主题条目做**关联收听**（双向链接），形成知识树，而不是一堆孤立碎片。
4. **播报**：每日定时汇总昨日新增条目与跨条目关联脉络，渲染成美观的飞书交互卡片推送给你。

## 架构

```text
                ┌──────────────┐
 播客名 / 链接  │   Fetcher     │  RSS · 小宇宙页面 · 网页检索 · 手动稿
 ─────────────▶│  (组合策略)   │
                └──────┬───────┘
                       ▼
                ┌──────────────┐        可选：音频 → ASR 转写
                │  Transcribe   │◀────── audio source（适配器接口）
                └──────┬───────┘
                       ▼
                ┌──────────────┐
                │   Analyzer    │  摘要 / 要点 / 金句 / 标签 / 分类
                └──────┬───────┘
                       ▼
                ┌──────────────┐
                │    Linker     │  与历史笔记比对，生成关联收听 + 回链
                └──────┬───────┘
                       ▼
                ┌──────────────┐
                │    Store      │  飞书 Wiki 目录树（默认）/ 本地 Markdown
                └──────┬───────┘
                       ▼
                ┌──────────────┐
                │   Briefing    │  昨日回顾 · 分组脉络 · 关联高亮 → 飞书卡片
                └──────────────┘
```

### 知识树关联机制

- 每篇笔记带有：分类、标签、要点、金句。
- 新条目入库前，`Linker` 先从索引中取出同分类历史条目，通过**标签/关键词重合度 + LLM 判断**选出最相关的若干条，记录「为什么相关」。
- 新笔记中写入「关联收听」小节；被关联的旧笔记回写反向链接，保证双向可追溯。
- 分类 taxonomy 在 `config/categories.yaml` 中维护，默认：科技与互联网 / 商业与职场 / 生活与情感 / 人文与社科 / 其他。

## 快速开始

```bash
# 1. 安装依赖（建议 3.10+）
pip install -r requirements.txt

# 2. 复制环境变量并填写
cp .env.example .env

# 3. 抓取并清洗一集播客
python -m podcleaner.cli ingest "随机波动" --episode "第 120 期 标题"

# 4. 生成本地预览的昨日简报（不推送）
python -m podcleaner.cli briefing --dry-run

# 5. 查看当前知识树索引
python -m podcleaner.cli tree
```

## 配置

见 `.env.example`。关键项：

| 变量 | 说明 |
|---|---|
| `PODCLEANER_LLM_BASE_URL` / `PODCLEANER_LLM_API_KEY` / `PODCLEANER_LLM_MODEL` | OpenAI 兼容的 LLM 接口 |
| `PODCLEANER_STORE` | `wiki`（飞书知识库，默认）或 `local`（本地 Markdown） |
| `PODCLEANER_WIKI_SPACE_ID` | 飞书 Wiki 空间 ID（store=wiki 时必填） |
| `PODCLEANER_WIKI_HOME_URL` | 知识库首页链接，用于简报卡片的入口跳转 |
| `PODCLEANER_INDEX_FILE` | 本地索引文件路径，用于关联比对与简报取数 |

> 飞书写入默认通过本机 `lark-cli`（用户身份）执行；`wiki.py` 里的命令可按你的部署环境替换为 OpenAPI 直连。

## 目录结构

```text
podcast-cleaner-agent/
├── config/
│   └── categories.yaml        # 分类 taxonomy 与关联上限
├── prompts/
│   ├── episode_summary.md      # 单集提炼提示词
│   └── knowledge_link.md       # 跨条目关联判断提示词
├── src/podcleaner/
│   ├── fetcher/                 # 取稿：rss / xiaoyuzhou / web_search / manual
│   ├── transcribe/              # ASR 适配器（可选）
│   ├── analyzer/               # LLM 客户端、结构化提炼
│   ├── linker.py                # 知识树关联与回链
│   ├── store/                   # wiki / local 两种存储适配
│   ├── briefing/                # 昨日汇总 + 卡片渲染
│   ├── pipeline.py             # 编排：取稿 → 提炼 → 关联 → 入库
│   └── cli.py                   # 命令行入口
├── tests/
└── examples/
```

## 部署到日常使用

- **入库**：在对话中把播客名发给 Agent，命中 `ingest` 流程；缺稿时回退为粘贴文字稿。
- **每日简报**：定时任务每天 08:00 触发 `briefing`，读取昨日索引，渲染卡片并私聊推送。
- **Wiki 目录树**：首次运行时按 taxonomy 自动创建分类节点；每集笔记落在对应分类下。

## 开发说明

- 所有外部依赖（LLM、飞书、ASR）都走适配器，替换实现不动主流程。
- 不要把 API Key、Wiki token 提交进仓库；敏感配置只走 `.env`（已在 `.gitignore` 中排除）。
- `tests/` 覆盖数据模型序列化与卡片渲染；新增适配器时补对应单测。

## License

MIT
