"""公开网页检索适配器（占位）。

默认不绑定具体搜索引擎；需要接入时在此实现：
- 按节目名 + 单集标题检索公开简介、章节笔记；
- 合并 top-N 片段作为 content；
- 失败返回 None，让组合流程继续回退。

可通过环境变量 PODCLEANER_WEB_SEARCH_* 配置你的检索后端。
"""

from __future__ import annotations

import logging

from .base import BaseFetcher, FetchResult

log = logging.getLogger(__name__)


class WebSearchFetcher(BaseFetcher):
    source_type = "web"

    def fetch(
        self,
        podcast_name: str,
        episode_hint: str | None = None,
    ) -> FetchResult | None:
        log.info("WebSearchFetcher 未配置检索后端，跳过。")
        return None
