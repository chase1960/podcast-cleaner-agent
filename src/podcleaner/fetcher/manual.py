"""手动稿回退：用户粘贴的文字稿 / 笔记 / 转写文本。"""

from __future__ import annotations

from pathlib import Path

from .base import BaseFetcher, FetchResult


class ManualFetcher(BaseFetcher):
    source_type = "manual"

    def __init__(self, transcript_file: str = "", inline_text: str = "") -> None:
        self.transcript_file = transcript_file
        self.inline_text = inline_text

    def fetch(
        self,
        podcast_name: str,
        episode_hint: str | None = None,
    ) -> FetchResult | None:
        text = self.inline_text.strip()
        if not text and self.transcript_file:
            path = Path(self.transcript_file)
            if path.exists():
                text = path.read_text(encoding="utf-8").strip()
        if not text:
            return None
        return FetchResult(
            content=text,
            source_type=self.source_type,
            episode_title=episode_hint or "",
            podcast_name=podcast_name,
        )
