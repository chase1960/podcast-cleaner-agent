"""按日期汇总知识库条目，形成简报数据源。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from ..models import Episode
from ..store.base import Store


def yesterday_str() -> str:
    return (date.today() - timedelta(days=1)).isoformat()


@dataclass
class Digest:
    date: str
    items: list[Episode] = field(default_factory=list)
    groups: dict[str, list[Episode]] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return len(self.items)

    @property
    def category_count(self) -> int:
        return len(self.groups)

    @property
    def has_relations(self) -> bool:
        return any(e.related for e in self.items)


def collect_digest(store: Store, date_str: str | None = None) -> Digest:
    target = date_str or yesterday_str()
    items = [e for e in store.list_episodes() if e.listened_at == target]
    groups: dict[str, list[Episode]] = {}
    for episode in items:
        groups.setdefault(episode.category, []).append(episode)
    return Digest(date=target, items=items, groups=groups)
