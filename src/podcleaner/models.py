"""核心数据模型：一期播客笔记及其在知识树中的关联。

除节目层面的摘要 / 要点 / 金句外，模型还保留面向「个人沉淀」的四类结构：
- ``aha_moments``：听到当时被点醒的瞬间（节目触点 + 我的顿悟）；
- ``insights``：可迁移到自己身上的个人启发（区别于节目观点）；
- ``open_questions``：听完仍想搞清楚、值得继续深挖的问题；
- ``next_steps``：下一步可执行的深耕方向 / 动作。
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Any


@dataclass
class RelatedRef:
    """与历史条目的一条关联。"""

    title: str
    url: str = ""
    reason: str = ""
    relation_type: str = "theme"  # theme | echo | contrast | continuation | aha

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RelatedRef":
        return cls(
            title=data.get("title", ""),
            url=data.get("url", ""),
            reason=data.get("reason", ""),
            relation_type=data.get("relation_type", "theme"),
        )


@dataclass
class AhaMoment:
    """一个啊哈时刻：节目里的触点，以及它当时点醒了我什么。"""

    trigger: str = ""          # 原话 / 场景 / 概念，是什么触发了顿悟
    insight: str = ""          # 我的顿悟 / 受启发之处
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | str) -> "AhaMoment":
        if isinstance(data, str):
            return cls(trigger=data.strip())
        return cls(
            trigger=str(data.get("trigger", "")),
            insight=str(data.get("insight", "")),
            tags=[str(x) for x in data.get("tags", []) if str(x).strip()],
        )


@dataclass
class Insight:
    """一条可跨条目沉淀的个人启发（区别于节目本身的观点）。"""

    text: str = ""
    source: str = ""           # 来自哪期笔记（display_title）
    relation: str = ""         # 与其他启发如何呼应（可选）

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | str) -> "Insight":
        if isinstance(data, str):
            return cls(text=data.strip())
        return cls(
            text=str(data.get("text", "")),
            source=str(data.get("source", "")),
            relation=str(data.get("relation", "")),
        )


@dataclass
class OpenQuestion:
    """一个待深挖的问题。"""

    question: str = ""
    why_it_matters: str = ""    # 为什么值得继续想 / 与什么相关
    status: str = "open"        # open | exploring | resolved

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | str) -> "OpenQuestion":
        if isinstance(data, str):
            return cls(question=data.strip())
        return cls(
            question=str(data.get("question", "")),
            why_it_matters=str(data.get("why_it_matters", "")),
            status=str(data.get("status", "open")) or "open",
        )


@dataclass
class NextStep:
    """一个下一步深耕方向 / 可执行动作。"""

    action: str = ""
    direction: str = ""         # 研究 | 实践 | 阅读 | 对话 | 复盘
    priority: str = "medium"     # high | medium | low

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | str) -> "NextStep":
        if isinstance(data, str):
            return cls(action=data.strip())
        return cls(
            action=str(data.get("action", "")),
            direction=str(data.get("direction", "")),
            priority=str(data.get("priority", "medium")) or "medium",
        )


@dataclass
class Episode:
    """一期播客的清洗结果，也是知识树中的一个节点。"""

    podcast_name: str
    episode_title: str
    url: str = ""
    platform: str = "xiaoyuzhou"
    listened_at: str = field(default_factory=lambda: date.today().isoformat())
    category: str = "其他"
    summary: str = ""
    key_points: list[str] = field(default_factory=list)
    quotes: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    related: list[RelatedRef] = field(default_factory=list)

    # ── 个人沉淀层 ──────────────────────────────────────────
    aha_moments: list[AhaMoment] = field(default_factory=list)
    insights: list[Insight] = field(default_factory=list)
    open_questions: list[OpenQuestion] = field(default_factory=list)
    next_steps: list[NextStep] = field(default_factory=list)

    source_type: str = "shownotes"  # shownotes | transcript | manual | asr | web
    raw_content: str = ""
    note_url: str = ""
    note_token: str = ""

    # ── 序列化 ──────────────────────────────────────────────
    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["related"] = [r.to_dict() for r in self.related]
        data["aha_moments"] = [m.to_dict() for m in self.aha_moments]
        data["insights"] = [i.to_dict() for i in self.insights]
        data["open_questions"] = [q.to_dict() for q in self.open_questions]
        data["next_steps"] = [n.to_dict() for n in self.next_steps]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Episode":
        data = dict(data)
        data["related"] = [RelatedRef.from_dict(r) for r in data.get("related", [])]
        data["aha_moments"] = [AhaMoment.from_dict(r) for r in data.get("aha_moments", [])]
        data["insights"] = [Insight.from_dict(r) for r in data.get("insights", [])]
        data["open_questions"] = [OpenQuestion.from_dict(r) for r in data.get("open_questions", [])]
        data["next_steps"] = [NextStep.from_dict(r) for r in data.get("next_steps", [])]
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})

    # ── 展示辅助 ────────────────────────────────────────────
    @property
    def display_title(self) -> str:
        return f"{self.podcast_name}｜{self.episode_title}".strip("｜")

    def signature(self) -> str:
        """用于去重的稳定签名。"""
        return f"{self.podcast_name}::{self.episode_title}".lower()
