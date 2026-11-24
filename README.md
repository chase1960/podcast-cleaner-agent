# podcast-cleaner-agent · 播客清洗与知识树 Agent

把通勤路上听的播客，自动变成一篇结构清晰的笔记，并按主题汇入你的**个人知识树**；每天早上推送一份可读的昨日回顾简报。

## 在线演示

- [打开可交互流程演示](https://htmlpreview.github.io/?https://github.com/chase1960/podcast-cleaner-agent/main/docs/flow.html)：逐步查看取稿 → 提炼 → 关联 → 脉络 → 入树 → 播报的完整管线，以及样例简报卡片。
- [演示页源码](https://github.com/chase1960/podcast-cleaner-agent/blob/main/docs/flow.html)：单文件、自包含，无外部依赖。

> 若在仓库 **Settings → Pages** 中将 Source 设为 GitHub Actions，本仓库会经 `.github/workflows/pages.yml` 发布到 `https://chase1960.github.io/podcast-cleaner-agent/`；未开启前可使用上面的预览链接。

## 这是什么

一个可独立运行的 Python Agent 框架。你告诉它播客名称（可选单集标题或链接），它会：

1. **取稿**：优先解析 RSS feed 与节目公开 shownotes（小宇宙等平台）；拿不到全文时回退到你粘贴的文字稿 / 音频转写稿。
2. **提炼**：调用 LLM 输出结构化结果——一句话摘要、核心要点、金句、标签、所属分类，并单独留下**当时被点醒的啊哈时刻**、可迁移到自己身上的**个人启发**、**待深挖的问题**和**下一步深耕方向**，避免好想法一闪而过。
3. **入树与串联**：笔记写入飞书 Wiki 对应分类目录；`Linker` 与历史同主题条目做**关联收听**（双向链接），`Threads` 再把多条笔记聚成可延续的**主题线索**，让碎片知识彼此串联，而不是一堆孤立碎片。
4. **播报**：每日定时汇总昨日新增条目、关联脉络与主题线索，并把待解问题、深耕方向汇成「知识指引」，渲染成美观的飞书交互卡片推送给你。

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
                │   Analyzer    │  摘要 / 要点 / 金句 / 标签 / 分类 / 啊哈 / 启发 / 问题 / 深耕
                └──────┬───────┘
                       ▼
                ┌──────────────┐
                │    Linker     │  与历史笔记比对，生成关联收听 + 回链
                └──────┬───────┘
                       ▼
                ┌──────────────┐
                │   Threads     │  跨条目聚类成主题线索，沉淀共同待解问题
                └──────┬───────┘
                       ▼
                ┌──────────────┐
                │    Store      │  飞书 Wiki 目录树（默认）/ 本地 Markdown
                └──────┬───────┘
                       ▼
                ┌──────────────┐
                │   Briefing    │  昨日回顾 · 关联脉络 · 主题线索 · 知识指引 → 飞书卡片
                └──────────────┘
```

### 知识树关联机制

- 每篇笔记带有：分类、标签、要点、金句，以及个人沉淀层——**啊哈时刻**（节目触点 + 我的顿悟）、**个人启发**、**待深挖问题**、**下一步深耕**。
- 新条目入库前，`Linker` 先从索引中取出候选历史条目，通过**标签/关键词/顿悟与问题的重合度 + LLM 判断**选出最相关的若干条，记录「为什么相关」（主题印证 / 观点对立 / 案例延续 / 顿悟呼应）。
- `Threads` 再把多条笔记按共同标签、顿悟与待解问题聚成 1~3 条主题线索，标注它们共同呼应的主题与可继续追查的问题；无 LLM 时按标签共现兜底聚类。
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

# 6. 跨期回顾沉淀的啊哈时刻 / 启发 / 待解问题 / 深耕方向
python -m podcleaner.cli insights
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
| `PODCLEANER_MAX_AHA` / `PODCLEANER_MAX_OPEN_QUESTIONS` / `PODCLEANER_MAX_NEXT_STEPS` | 单条笔记内啊哈时刻 / 待解问题 / 深耕方向的保留上限 |
| `PODCLEANER_ENABLE_THREADS` | 是否在简报中生成跨条目主题脉络（`true` / `false`） |

> 飞书写入默认通过本机 `lark-cli`（用户身份）执行；`wiki.py` 里的命令可按你的部署环境替换为 OpenAPI 直连。

## 目录结构

```text
podcast-cleaner-agent/
├── config/
│   └── categories.yaml        # 分类 taxonomy 与关联上限
├── prompts/
│   ├── episode_summary.md      # 单集提炼提示词（含啊哈 / 启发 / 问题 / 深耕）
│   ├── knowledge_link.md       # 跨条目关联判断提示词
│   └── knowledge_threads.md    # 主题线索归纳提示词
├── src/podcleaner/
│   ├── fetcher/                 # 取稿：rss / xiaoyuzhou / web_search / manual
│   ├── transcribe/              # ASR 适配器（可选）
│   ├── analyzer/               # LLM 客户端、结构化提炼、关联、主题线索
│   ├── store/                   # wiki / local 两种存储适配
│   ├── briefing/                # 昨日汇总 + 卡片渲染
│   ├── pipeline.py             # 编排：取稿 → 提炼 → 关联 → 入树 → 脉络
│   └── cli.py                   # 命令行入口（ingest / briefing / tree / insights）
├── docs/
│   └── flow.html               # 可交互流程演示页（静态、自包含）
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
