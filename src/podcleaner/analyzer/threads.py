"""主题脉络（KnowledgeThread）：把多条播客笔记聚成可延续的知识线索。

线索回答两个问题：
- 这些碎片知识彼此怎么串联（共同主题 / 顿悟呼应 / 共同待解问题）；
- 沿着这条线索，下一步还可以深挖什么。

无 LLM 时按标签 / 个人沉淀词共现做兜底聚类；LLM 可用时再交给模型归纳。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from ..config import Settings
from ..models import Episode
from .llm import LLMClient

log = logging.getLogger(__name__)


@dataclass
class KnowledgeThread:
    """一条跨条目的主题脉络。"""

    title: str
    summary: str = ""
    members: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            "members": list(self.members),
            "open_questions": list(self.open_questions),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KnowledgeThread":
        return cls(
            title=str(data.get("title", "")),
            summary=str(data.get("summary", "")),
            members=[str(x) for x in data.get("members", [])],
            open_questions=[str(x) for x in data.get("open_questions", [])],
        )


def build_threads(
    episodes: list[Episode],
    settings: Settings,
    llm: LLMClient | None = None,
) -> list[KnowledgeThread]:
    """聚合全部历史条目，返回 1~3 条主题脉络；无内容时返回空列表。"""
    if not episodes:
        return []
    if not settings.enable_threads:
        return []

    if llm is not None and llm.available:
        try:
            threads = _llm_threads(episodes, settings, llm)
            if threads:
                return threads[:3]
        except Exception as exc:  # noqa: BLE001
            log.warning("LLM 主题脉络失败，回退标签共现聚类：%s", exc)

    return _tag_cluster_threads(episodes)[:3]


# ── 兜底：标签 / 沉淀词共现聚类 ──────────────────────────
def _tag_cluster_threads(episodes: list[Episode]) -> list[KnowledgeThread]:
    parent = list(range(len(episodes)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for i, left in enumerate(episodes):
        for j in range(i + 1, len(episodes)):
            right = episodes[j]
            if _shared_signals(left, right):
                union(i, j)

    clusters: dict[int, list[int]] = {}
    for i in range(len(episodes)):
        clusters.setdefault(find(i), []).append(i)

    threads: list[KnowledgeThread] = []
    for members_idx in clusters.values():
        if len(members_idx) < 2:
            continue  # 单条不构成「线索」
        group = [episodes[k] for k in members_idx]
        tag_freq: dict[str, int] = {}
        for ep in group:
            for tag in ep.tags:
                tag_freq[tag] = tag_freq.get(tag, 0) + 1
        top_tags = [t for t, _ in sorted(tag_freq.items(), key=lambda kv: -kv[1])[:2]
                    if t]
        title = top_tags[0] if top_tags else group[0].category
        questions: list[str] = []
        for ep in group:
            for q in ep.open_questions:
                if q.question and q.question not in questions:
                    questions.append(q.question)
        threads.append(
            KnowledgeThread(
                title=title,
                summary=(
                    f"围绕「{'、'.join(top_tags)}」等主题，{len(group)} 期内容互相印证或延伸，"
                    "可作为一条持续跟踪的知识线索。"
                    if top_tags else f"{len(group)} 期同属「{group[0].category}」主题，可对照回看。"
                ),
                members=[ep.display_title for ep in group],
                open_questions=questions[:3],
            )
        )

    threads.sort(key=lambda t: len(t.members), reverse=True)
    return threads


def _shared_signals(left: Episode, right: Episode) -> bool:
    if set(left.tags) & set(right.tags):
        return True
    left_words = {w for ep in [left] for w in _personal_words(ep)}
    right_words = {w for ep in [right] for w in _personal_words(ep)}
    return bool(left_words & right_words)


def _personal_words(episode: Episode) -> set[str]:
    text = " ".join(
        [m.trigger + " " + m.insight for m in episode.aha_moments]
        + [i.text for i in episode.insights]
        + [q.question for q in episode.open_questions]
    )
    return {w for w in text.replace("、", " ").split() if len(w) >= 2}


# ── LLM 归纳 ────────────────────────────────────────────
def _llm_threads(
    episodes: list[Episode], settings: Settings, llm: LLMClient
) -> list[KnowledgeThread]:
    blocks: list[str] = []
    for idx, ep in enumerate(episodes):
        blocks.append(
            f"[{idx}] {ep.display_title}\n"
            f"标签：{', '.join(ep.tags)}\n摘要：{ep.summary}\n"
            f"啊哈：{_brief_aha(ep)}｜待解问题：{_brief_questions(ep)}"
        )
    prompt = settings.prompt_text("knowledge_threads").format(
        episodes="\n\n".join(blocks),
        max_threads=3,
    )
    data = llm.chat_json(
        "你在把零散的播客笔记整理成可延续的个人知识线索。", prompt
    )
    threads: list[KnowledgeThread] = []
    index_map = {ep.display_title: ep for ep in episodes}
    for item in data if isinstance(data, list) else []:
        if not isinstance(item, dict):
            continue
        members = [str(m) for m in item.get("members", []) if str(m)]
        threads.append(
            KnowledgeThread(
                title=str(item.get("title", "")).strip() or "未命名线索",
                summary=str(item.get("summary", "")).strip(),
                members=members,
                open_questions=[str(q) for q in item.get("open_questions", []) if str(q)],
            )
        )
    # 仅保留能在索引里对上标题的成员，避免编造
    for thread in threads:
        thread.members = [m for m in thread.members if m in index_map]
    return [t for t in threads if t.members]


def _brief_aha(ep: Episode) -> str:
    return "；".join(f"{m.trigger}→{m.insight}" for m in ep.aha_moments) or "（无）"


def _brief_questions(ep: Episode) -> str:
    return "；".join(q.question for q in ep.open_questions) or "（无）"
