"""取稿适配器基类与结果结构。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FetchResult:
    """一次取稿的结果；拿不到内容时返回 None。"""

    content: str
    source_type: str  # shownotes | transcript | manual | asr | web
    url: str = ""
    episode_title: str = ""
    podcast_name: str = ""


class BaseFetcher:
    """各来源适配器继承此接口。"""

    source_type: str = "shownotes"

    def fetch(
        self,
        podcast_name: str,
        episode_hint: str | None = None,
    ) -> FetchResult | None:  # pragma: no cover - 接口定义
        raise NotImplementedError
