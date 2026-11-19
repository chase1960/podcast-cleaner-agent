"""存储接口约定，Wiki 与本地实现都遵循。"""

from __future__ import annotations

from typing import Protocol

from ..models import Episode, RelatedRef


class Store(Protocol):
    def list_episodes(self) -> list[Episode]:
        """返回知识库中全部历史条目（用于关联比对）。"""
        ...

    def save(self, episode: Episode) -> None:
        """写入一篇新笔记，并把元数据记入本地索引。"""
        ...

    def add_backlink(self, episode: Episode, refs: list[RelatedRef]) -> None:
        """在被关联的旧笔记上回写反向链接。"""
        ...
