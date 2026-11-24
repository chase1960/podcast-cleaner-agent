"""主编排：取稿 → 转写(可选) → 提炼 → 关联 → 入库；以及简报汇总。"""

from __future__ import annotations

import logging

from .analyzer import LLMClient, Linker, analyze_episode, build_threads
from .briefing import build_card, collect_digest
from .config import Settings, get_settings
from .fetcher import (
    FetchResult,
    ManualFetcher,
    RssFetcher,
    WebSearchFetcher,
    XiaoyuzhouFetcher,
)
from .models import Episode
from .store import LocalStore, Store, WikiStore
from .transcribe import Transcriber

log = logging.getLogger(__name__)


class PipelineError(RuntimeError):
    pass


class Pipeline:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.llm = LLMClient(
            base_url=self.settings.llm_base_url,
            api_key=self.settings.llm_api_key,
            model=self.settings.llm_model,
        )
        self.store = self._build_store()
        self.linker = Linker(self.settings, self.llm, self.store)
        self.transcriber = Transcriber(engine=self.settings.asr_engine)

    def _build_store(self) -> Store:
        if self.settings.store == "local":
            return LocalStore(index_file=self.settings.index_file)
        return WikiStore(self.settings)

    # ── 入库流程 ────────────────────────────────────────────
    def ingest(
        self,
        podcast_name: str,
        episode_hint: str | None = None,
        transcript: str = "",
        audio_source: str = "",
    ) -> Episode:
        fetched = self._fetch(podcast_name, episode_hint, transcript, audio_source)
        if fetched is None or not fetched.content.strip():
            raise PipelineError(
                "未取到公开内容。请粘贴文字稿，或提供可转写的音频文件后重试。"
            )

        episode = analyze_episode(self.settings, self.llm, fetched)
        self.linker.link(episode)
        self.store.save(episode)
        log.info("已入库：%s", episode.display_title)
        return episode

    def _fetch(
        self,
        podcast_name: str,
        episode_hint: str | None,
        transcript: str,
        audio_source: str,
    ) -> FetchResult | None:
        # 组合策略：RSS → 小宇宙页面 → 网页检索
        for fetcher in (
            RssFetcher(timeout=self.settings.http_timeout),
            XiaoyuzhouFetcher(timeout=self.settings.http_timeout),
            WebSearchFetcher(),
        ):
            try:
                result = fetcher.fetch(podcast_name, episode_hint)
            except Exception as exc:  # noqa: BLE001
                log.warning("取稿器 %s 失败：%s", type(fetcher).__name__, exc)
                result = None
            if result and result.content.strip():
                return result

        # 回退 1：音频转写
        if audio_source and Transcriber.exists(audio_source):
            text = self.transcriber.transcribe(audio_source)
            if text.strip():
                return FetchResult(
                    content=text, source_type="asr", episode_title=episode_hint or "",
                    podcast_name=podcast_name,
                )

        # 回退 2：手动粘贴稿 / 稿文件
        manual = ManualFetcher(
            transcript_file=self.settings.manual_transcript,
            inline_text=transcript,
        )
        return manual.fetch(podcast_name, episode_hint)

    # ── 简报流程 ────────────────────────────────────────────
    def briefing(self, date_str: str | None = None) -> tuple[object, dict]:
        all_episodes = self.store.list_episodes()
        threads = build_threads(all_episodes, self.settings, self.llm)
        digest = collect_digest(self.store, date_str, threads=threads)
        home_url = self.settings.wiki_home_url or self.settings.wiki_root_node
        card = build_card(digest, wiki_home_url=home_url)
        return digest, card

    def tree(self) -> list[Episode]:
        return self.store.list_episodes()

    def list_insights(self) -> list[Episode]:
        """返回带有个人沉淀（啊哈 / 启发 / 问题 / 深耕）的条目，供跨期回顾。"""
        return [
            e for e in self.store.list_episodes()
            if e.aha_moments or e.insights or e.open_questions or e.next_steps
        ]
