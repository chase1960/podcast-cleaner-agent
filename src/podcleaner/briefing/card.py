"""把 Digest 渲染成飞书 Card 2.0 交互卡片。

设计：单焦点标题区 → 指标概览 → 按分类分组的条目（含啊哈时刻 / 待解问题 / 深耕方向）
→ 关联脉络 → 主题线索 → 知识指引 → 知识库入口。
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
                "content": "<font color='grey'>昨天没有新的播客笔记。通勤路上听到好节目，把名字发给我即可入库。</font>",
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

    thread_blocks = _thread_blocks(digest)
    elements.extend(thread_blocks)

    guide_block = _guide_block(digest)
    if guide_block is not None:
        elements.append({"tag": "hr"})
        elements.append(guide_block)

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
            "title": {"tag": "plain_text", "content": "📻 昨日播客回顾"},
            "subtitle": {"tag": "plain_text", "content": f"{digest.date} · 昨日新增 {digest.total} 期"},
            "template": "blue",
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
    title = episode.display_title
    if episode.note_url:
        title = f"[{title}]({episode.note_url})"
    lines = [f"**{title}**"]

    if episode.summary:
        lines.append(episode.summary)
    if episode.key_points:
        lines.append("\n".join(f"- {point}" for point in episode.key_points[:3]))
    if episode.quotes:
        lines.append("> " + " / ".join(episode.quotes[:2]))

    for moment in episode.aha_moments[:2]:
        if moment.insight:
            lines.append(f"💡 **啊哈**：{moment.trigger} → {moment.insight}")
        elif moment.trigger:
            lines.append(f"💡 **啊哈**：{moment.trigger}")

    for question in episode.open_questions[:2]:
        lines.append(f"❓ **待解**：{question.question}")

    for step in episode.next_steps[:2]:
        tail = " · ".join(x for x in (step.direction, f"优先级 {step.priority}") if x)
        lines.append(f"🧭 **深耕**：{step.action}" + (f"（{tail}）" if tail else ""))

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


def _thread_blocks(digest: Digest) -> list[dict]:
    blocks: list[dict] = []
    for thread in digest.threads:
        body = [f"**🧵 {thread.title}**"]
        if thread.summary:
            body.append(thread.summary)
        if thread.members:
            body.append("<font color='grey'>线索条目：" + "、".join(thread.members[:5]) + "</font>")
        for question in thread.open_questions[:3]:
            body.append(f"❓ {question}")
        blocks.append({"tag": "markdown", "content": "\n".join(body)})
    return blocks


def _guide_block(digest: Digest) -> dict | None:
    """聚合昨日条目的待解问题与下一步深耕方向，形成「知识指引」。"""
    lines: list[str] = ["**🧭 知识指引**"]
    for question in digest.open_questions[:4]:
        lines.append(f"- ❓ {question}")
    for episode in digest.next_steps:
        for step in episode.next_steps[:2]:
            lines.append(f"- 🧭 {step.action}（{episode.display_title}）")
    if len(lines) == 1:
        return None
    return {"tag": "markdown", "content": "\n".join(lines[:8])}
