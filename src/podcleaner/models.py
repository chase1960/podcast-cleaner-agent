"""核心数据模型：一期播客笔记及其在知识树中的关联。"""

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
    relation_type: str = "theme"  # theme | echo | contrast | continuation

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
    source_type: str = "shownotes"  # shownotes | transcript | manual | asr | web
    raw_content: str = ""
    note_url: str = ""
    note_token: str = ""

    # ── 序列化 ──────────────────────────────────────────────
    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["related"] = [r.to_dict() for r in self.related]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Episode":
        data = dict(data)
        data["related"] = [RelatedRef.from_dict(r) for r in data.get("related", [])]
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})

    # ── 展示辅助 ────────────────────────────────────────────
    @property
    def display_title(self) -> str:
        return f"{self.podcast_name}｜{self.episode_title}".strip("｜")

    def signature(self) -> str:
        """用于去重的稳定签名。"""
        return f"{self.podcast_name}::{self.episode_title}".lower()
