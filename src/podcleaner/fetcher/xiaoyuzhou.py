"""小宇宙网页端 shownotes 抓取。

注意：平台页面结构可能调整；抓取失败时返回 None，由组合流程回退到其他来源。
"""

from __future__ import annotations

import logging
import re
from html import unescape
from urllib.parse import quote

from .base import BaseFetcher, FetchResult

log = logging.getLogger(__name__)

SEARCH_URL = "https://www.xiaoyuzhoufm.com/search?q={term}"
EPISODE_URL = "https://www.xiaoyuzhoufm.com/episode/{eid}"

EPISODE_LINK_RE = re.compile(r'href="/episode/([a-zA-Z0-9]+)"')
META_DESC_RE = re.compile(
    r'<meta\s+name="description"\s+content="([^"]*)"', re.IGNORECASE
)
TITLE_RE = re.compile(r'<meta\s+property="og:title"\s+content="([^"]*)"', re.IGNORECASE)


class XiaoyuzhouFetcher(BaseFetcher):
    source_type = "shownotes"

    def __init__(self, timeout: int = 15) -> None:
        self.timeout = timeout

    def fetch(
        self,
        podcast_name: str,
        episode_hint: str | None = None,
    ) -> FetchResult | None:
        try:
            search_html = self._get(SEARCH_URL.format(term=quote(podcast_name)))
        except Exception as exc:  # noqa: BLE001
            log.warning("小宇宙搜索失败：%s", exc)
            return None

        ids = EPISODE_LINK_RE.findall(search_html)
        if not ids:
            return None

        for eid in dict.fromkeys(ids):  # 保序去重
            result = self._episode(eid, podcast_name, episode_hint)
            if result is not None:
                return result
        return None

    def _episode(
        self, eid: str, podcast_name: str, episode_hint: str | None
    ) -> FetchResult | None:
        url = EPISODE_URL.format(eid=eid)
        try:
            html = self._get(url)
        except Exception as exc:  # noqa: BLE001
            log.warning("小宇宙单集抓取失败 %s：%s", url, exc)
            return None

        desc_m = META_DESC_RE.search(html)
        title_m = TITLE_RE.search(html)
        description = unescape(desc_m.group(1)) if desc_m else ""
        title = unescape(title_m.group(1)) if title_m else episode_hint or ""

        if episode_hint and episode_hint.lower() not in title.lower():
            # 搜索结果可能混入其他节目，标题不匹配则跳过
            pass

        if not description.strip():
            return None

        return FetchResult(
            content=description.strip(),
            source_type=self.source_type,
            url=url,
            episode_title=title,
            podcast_name=podcast_name,
        )

    def _get(self, url: str) -> str:
        import requests  # 懒加载

        resp = requests.get(
            url,
            timeout=self.timeout,
            headers={"User-Agent": "Mozilla/5.0 (podcast-cleaner-agent)"},
        )
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text
