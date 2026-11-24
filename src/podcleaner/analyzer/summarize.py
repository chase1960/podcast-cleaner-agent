"""单集结构化提炼：prompt → LLM → Episode。"""

from __future__ import annotations

import logging
from datetime import date

from ..config import Settings
from ..fetcher.base import FetchResult
from ..models import AhaMoment, Episode, Insight, NextStep, OpenQuestion
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
        # 无 LLM 时走兜底：关键词分类 + 朴素摘要 + 朴素啊哈时刻
        _fill_fallback(episode, settings, fetched.content)
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
        _fill_fallback(episode, settings, fetched.content)
        return episode

    episode.category = _validate_category(data.get("category", ""), settings)
    episode.summary = str(data.get("summary", "")).strip()
    episode.key_points = [str(x).strip() for x in data.get("key_points", []) if str(x).strip()]
    episode.quotes = [str(x).strip() for x in data.get("quotes", []) if str(x).strip()]
    episode.tags = [str(x).strip() for x in data.get("tags", []) if str(x).strip()]
    _fill_personal_layer(episode, data, settings)
    return episode


def _fill_personal_layer(episode: Episode, data: dict, settings: Settings) -> None:
    """解析个人沉淀层：啊哈时刻 / 启发 / 待解问题 / 下一步，并按上限截断。"""
    aha_raw = data.get("aha_moments", []) or []
    for item in aha_raw[: settings.max_aha]:
        if isinstance(item, str):
            episode.aha_moments.append(AhaMoment(trigger=item, insight=""))
        elif isinstance(item, dict):
            episode.aha_moments.append(
                AhaMoment(
                    trigger=str(item.get("trigger", "")).strip(),
                    insight=str(item.get("insight", "")).strip(),
                    tags=[str(t).strip() for t in item.get("tags", []) if str(t).strip()],
                )
            )

    insights_raw = data.get("insights", []) or []
    for item in insights_raw:
        if isinstance(item, str):
            episode.insights.append(Insight(text=item.strip(), source=episode.display_title))
        elif isinstance(item, dict) and item.get("text"):
            episode.insights.append(
                Insight(
                    text=str(item.get("text", "")).strip(),
                    source=str(item.get("source", episode.display_title)),
                    relation=str(item.get("relation", "")),
                )
            )

    questions_raw = data.get("open_questions", []) or []
    for item in questions_raw[: settings.max_open_questions]:
        if isinstance(item, str):
            episode.open_questions.append(OpenQuestion(question=item.strip()))
        elif isinstance(item, dict) and item.get("question"):
            episode.open_questions.append(
                OpenQuestion(
                    question=str(item.get("question", "")).strip(),
                    why_it_matters=str(item.get("why_it_matters", "")).strip(),
                    status=str(item.get("status", "open")) or "open",
                )
            )

    steps_raw = data.get("next_steps", []) or []
    for item in steps_raw[: settings.max_next_steps]:
        if isinstance(item, str):
            episode.next_steps.append(NextStep(action=item.strip()))
        elif isinstance(item, dict) and item.get("action"):
            episode.next_steps.append(
                NextStep(
                    action=str(item.get("action", "")).strip(),
                    direction=str(item.get("direction", "")).strip(),
                    priority=str(item.get("priority", "medium")) or "medium",
                )
            )


def _fill_fallback(episode: Episode, settings: Settings, content: str) -> None:
    """离线 / LLM 失败时的朴素兜底：关键词分类 + 摘要 + 由金句/要点生成的啊哈占位。"""
    episode.category = settings.match_category(content)
    episode.summary = content[:120]
    episode.key_points = [content[:200]]
    episode.tags = []
    # 把第一条有记忆点的内容记为朴素啊哈时刻，避免离线时个人沉淀层完全空白
    seed = (episode.quotes[0] if episode.quotes else episode.key_points[0] if episode.key_points else "")
    if seed:
        episode.aha_moments.append(
            AhaMoment(trigger=seed[:80], insight="（离线兜底：待回看时补充个人顿悟）", tags=[])
        )


def _validate_category(value: str, settings: Settings) -> str:
    value = (value or "").strip()
    if value in settings.category_names:
        return value
    # 兼容返回 key 或别名
    for cat in settings.categories:
        if value in (cat["key"], cat["name"]):
            return cat["name"]
    return settings.match_category(value)
