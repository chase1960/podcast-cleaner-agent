"""单集结构化提炼：prompt → LLM → Episode。"""

from __future__ import annotations

import logging
from datetime import date

from ..config import Settings
from ..fetcher.base import FetchResult
from ..models import Episode
from .llm import LLMClient

log = logging.getLogger(__name__)


def analyze_episode(
    settings: Settings,
    llm: LLMClient,
    fetched: FetchResult,
    listened_at: str | None = None,
) -> Episode:
    episode = Episode(
        podcast_name=fetched.podcast_name,
        episode_title=fetched.episode_title,
        url=fetched.url,
        platform="xiaoyuzhou" if "xiaoyuzhoufm.com" in fetched.url else "web",
        listened_at=listened_at or date.today().isoformat(),
        source_type=fetched.source_type,
        raw_content=fetched.content,
    )

    if not llm.available:
        # 无 LLM 时走兜底：关键词分类 + 朴素摘要
        episode.category = settings.match_category(fetched.content)
        episode.summary = fetched.content[:120]
        episode.key_points = [fetched.content[:200]]
        episode.tags = []
        return episode

    prompt = settings.prompt_text("episode_summary").format(
        podcast_name=episode.podcast_name or "（未识别）",
        episode_title=episode.episode_title or "（未识别）",
        url=episode.url or "（无链接）",
        categories="、".join(settings.category_names),
        raw_content=fetched.content[:6000],
    )

    try:
        data = llm.chat_json("你是一名严谨的播客内容编辑。", prompt)
    except Exception as exc:  # noqa: BLE001
        log.warning("LLM 提炼失败，使用兜底结果：%s", exc)
        episode.category = settings.match_category(fetched.content)
        episode.summary = fetched.content[:120]
        return episode

    episode.category = _validate_category(data.get("category", ""), settings)
    episode.summary = str(data.get("summary", "")).strip()
    episode.key_points = [str(x).strip() for x in data.get("key_points", []) if str(x).strip()]
    episode.quotes = [str(x).strip() for x in data.get("quotes", []) if str(x).strip()]
    episode.tags = [str(x).strip() for x in data.get("tags", []) if str(x).strip()]
    return episode


def _validate_category(value: str, settings: Settings) -> str:
    value = (value or "").strip()
    if value in settings.category_names:
        return value
    # 兼容返回 key 或别名
    for cat in settings.categories:
        if value in (cat["key"], cat["name"]):
            return cat["name"]
    return settings.match_category(value)
