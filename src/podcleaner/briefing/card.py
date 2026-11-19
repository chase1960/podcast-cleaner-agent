"""把 Digest 渲染成飞书 Card 2.0 交互卡片。

设计：单焦点标题区 → 指标概览 → 按分类分组的条目卡片 → 关联脉络 → 知识库入口。
配色以 header 蓝色为主，正文用默认字号，次要信息用 grey。
"""

from __future__ import annotations

from ..models import Episode
from .digest import Digest

_CATEGORY_EMOJI = {
    "科技与互联网": "🤖",
    "商业与职场": "💼",
    "生活与情感": "🌱",
    "人文与社科": "📚",
    "其他": "🎧",
}


def build_card(digest: Digest, wiki_home_url: str = "") -> dict:
    elements: list[dict] = []

    elements.append(_overview(digest))
    elements.append({"tag": "hr"})

    if not digest.items:
        elements.append(
            {
                "tag": "markdown",
                "content": "昨日没有新增播客笔记。通勤路上听到好节目，把名字发给我即可入库。",
            }
        )
    else:
        for category, episodes in digest.groups.items():
            elements.append(_category_block(category, episodes))

    relation_lines = _relation_lines(digest)
    if relation_lines:
        elements.append({"tag": "hr"})
        elements.append(
            {"tag": "markdown", "content": "**🔗 关联脉络**\n" + "\n".join(relation_lines)}
        )

    if wiki_home_url:
        elements.append(
            {
                "tag": "markdown",
                "content": f"[打开播客知识库 →]({wiki_home_url})",
                "text_size": "caption",
            }
        )

    return {
        "schema": "2.0",
        "config": {"update_multi": True, "width_mode": "default"},
        "header": {
            "title": {"tag": "plain_text", "content": "🎙 播客早报"},
            "subtitle": {"tag": "plain_text", "content": f"{digest.date} · 昨日收听回顾"},
            "template": "blue",
            "icon": {"tag": "standard_icon", "token": "podcast_colorful"},
        },
        "body": {"direction": "vertical", "padding": "12px 12px 20px 12px", "elements": elements},
    }


def _overview(digest: Digest) -> dict:
    return {
        "tag": "column_set",
        "flex_mode": "weighted",
        "columns": [
            {
                "tag": "column",
                "width": "weighted",
                "elements": [
                    {"tag": "markdown", "content": f"**{digest.total}**\n<font color='grey'>昨日新增</font>"}
                ],
            },
            {
                "tag": "column",
                "width": "weighted",
                "elements": [
                    {"tag": "markdown", "content": f"**{digest.category_count}**\n<font color='grey'>主题分类</font>"}
                ],
            },
            {
                "tag": "column",
                "width": "weighted",
                "elements": [
                    {"tag": "markdown", "content": f"**{'有' if digest.has_relations else '无'}**\n<font color='grey'>跨条关联</font>"}
                ],
            },
        ],
    }


def _category_block(category: str, episodes: list[Episode]) -> dict:
    emoji = _CATEGORY_EMOJI.get(category, "🎧")
    body = [f"### {emoji} {category}"]
    for episode in episodes:
        body.append(_episode_markdown(episode))
    return {"tag": "markdown", "content": "\n\n".join(body)}


def _episode_markdown(episode: Episode) -> str:
    lines = [f"**{episode.display_title}**"]
    if episode.summary:
        lines.append(episode.summary)
    if episode.key_points:
        lines.append("\n".join(f"- {point}" for point in episode.key_points[:3]))
    if episode.quotes:
        lines.append("> " + " / ".join(episode.quotes[:2]))
    if episode.tags:
        lines.append("<font color='grey'>#" + " #".join(episode.tags) + "</font>")
    if episode.related:
        refs = "；".join(f"{r.title}（{r.reason}）" for r in episode.related[:2])
        lines.append(f"<font color='grey'>🔗 关联：{refs}</font>")
    return "\n".join(lines)


def _relation_lines(digest: Digest) -> list[str]:
    lines: list[str] = []
    for episode in digest.items:
        for ref in episode.related:
            lines.append(f"- **{episode.display_title}** ↔ {ref.title}：{ref.reason}")
    return lines[:6]
