"""RSS / iTunes 检索取稿。

流程：
1. 通过 Apple iTunes 公开搜索接口按节目名找到 feedUrl（无需 Key）；
2. 用 feedparser 解析 RSS；
3. 优先匹配 episode_hint，否则取最新一集；
4. 合并标题、简介、章节笔记作为内容。
"""

from __future__ import annotations

import logging
from urllib.parse import quote

from .base import BaseFetcher, FetchResult

log = logging.getLogger(__name__)

ITUNES_SEARCH = "https://itunes.apple.com/search?term={term}&media=podcast&limit=5"


class RssFetcher(BaseFetcher):
    source_type = "shownotes"

    def __init__(self, timeout: int = 15) -> None:
        self.timeout = timeout

    def _search_feed(self, podcast_name: str) -> tuple[str, str] | None:
        try:
            import requests  # 懒加载

            resp = requests.get(
                ITUNES_SEARCH.format(term=quote(podcast_name)),
                timeout=self.timeout,
                headers={"User-Agent": "podcast-cleaner-agent/0.1"},
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
        except Exception as exc:  # noqa: BLE001
            log.warning("iTunes 搜索失败：%s", exc)
            return None

        for item in results:
            feed_url = item.get("feedUrl")
            if feed_url:
                return item.get("collectionName", podcast_name), feed_url
        return None

    def fetch(
        self,
        podcast_name: str,
        episode_hint: str | None = None,
    ) -> FetchResult | None:
        found = self._search_feed(podcast_name)
        if not found:
            return None
        feed_title, feed_url = found

        try:
            import feedparser  # 懒加载

            parsed = feedparser.parse(feed_url)
            entries = parsed.entries
        except Exception as exc:  # noqa: BLE001
            log.warning("RSS 解析失败：%s", exc)
            return None

        if not entries:
            return None

        entry = self._pick_entry(entries, episode_hint)
        if entry is None:
            return None

        title = entry.get("title", episode_hint or "")
        summary = entry.get("summary", "") or entry.get("description", "")
        content = entry.get("content", [{}])
        body = content[0].get("value", "") if isinstance(content, list) else ""
        text = "\n\n".join(x for x in (summary, body) if x)

        if not text.strip():
            return None

        return FetchResult(
            content=text.strip(),
            source_type=self.source_type,
            url=entry.get("link", feed_url),
            episode_title=title,
            podcast_name=feed_title,
        )

    @staticmethod
    def _pick_entry(entries: list, hint: str | None):
        if hint:
            hint_low = hint.lower()
            for entry in entries:
                if hint_low in entry.get("title", "").lower():
                    return entry
        return entries[0]
