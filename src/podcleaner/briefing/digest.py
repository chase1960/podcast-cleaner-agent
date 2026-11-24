"""按日期汇总知识库条目，形成简报数据源。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from ..analyzer.threads import KnowledgeThread
from ..models import Episode
from ..store.base import Store


def yesterday_str() -> str:
    return (date.today() - timedelta(days=1)).isoformat()


@dataclass
class Digest:
    date: str
    items: list[Episode] = field(default_factory=list)
    groups: dict[str, list[Episode]] = field(default_factory=dict)
    threads: list[KnowledgeThread] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.items)

    @property
    def category_count(self) -> int:
        return len(self.groups)

    @property
    def has_relations(self) -> bool:
        return any(e.related for e in self.items)

    @property
    def has_threads(self) -> bool:
        return bool(self.threads)

    @property
    def open_questions(self) -> list[str]:
        """全部待解问题（去重，保持顺序），用于「知识指引」块。"""
        seen: set[str] = set()
        questions: list[str] = []
        for episode in self.items:
            for q in episode.open_questions:
                if q.question and q.question not in seen:
                    seen.add(q.question)
                    questions.append(q.question)
        return questions

    @property
    def next_steps(self) -> list[Episode]:
        """带有下一步深耕动作的条目，供卡片「知识指引」聚合。"""
        return [e for e in self.items if e.next_steps]


def collect_digest(
    store: Store,
    date_str: str | None = None,
    threads: list[KnowledgeThread] | None = None,
) -> Digest:
    target = date_str or yesterday_str()
    items = [e for e in store.list_episodes() if e.listened_at == target]
    groups: dict[str, list[Episode]] = {}
    for episode in items:
        groups.setdefault(episode.category, []).append(episode)
    return Digest(date=target, items=items, groups=groups, threads=threads or [])
