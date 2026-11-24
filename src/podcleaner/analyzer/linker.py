"""知识树关联：新条目入库前与历史条目比对，生成关联收听与回链。

关联不只看观点与标签，也纳入啊哈时刻、个人启发和待解问题，
让碎片顿悟能在知识树里互相串联。
"""

from __future__ import annotations

import logging

from ..config import Settings
from ..models import Episode, RelatedRef
from ..store.base import Store
from .llm import LLMClient

log = logging.getLogger(__name__)

_VALID_RELATIONS = {"theme", "echo", "contrast", "continuation", "aha"}


class Linker:
    def __init__(self, settings: Settings, llm: LLMClient, store: Store) -> None:
        self.settings = settings
        self.llm = llm
        self.store = store

    def link(self, episode: Episode) -> None:
        history = [
            e for e in self.store.list_episodes()
            if e.signature() != episode.signature()
        ]
        if not history:
            return

        candidates = self._prefilter(episode, history)
        if not candidates:
            return

        if self.llm.available:
            refs = self._llm_link(episode, candidates)
        else:
            refs = self._keyword_link(episode, candidates)

        episode.related = refs[: self.settings.max_related]
        if episode.related:
            self.store.add_backlink(episode, episode.related)

    # ── 候选筛选 ────────────────────────────────────────────
    def _prefilter(self, episode: Episode, history: list[Episode]) -> list[Episode]:
        def score(other: Episode) -> int:
            s = 0
            if other.category == episode.category:
                s += 2
            s += len(set(episode.tags) & set(other.tags))
            shared_words = {
                w for w in self._words(episode.summary)
                if w in self._words(other.summary)
            }
            s += len(shared_words)
            # 个人沉淀层：啊哈 / 启发 / 待解问题的词重合也加分
            s += len(
                self._personal_words(episode) & self._personal_words(other)
            )
            return s

        ranked = sorted(history, key=score, reverse=True)
        return [e for e in ranked[:10] if score(e) > 0]

    @staticmethod
    def _words(text: str) -> set[str]:
        return {w for w in text.replace("、", " ").split() if len(w) >= 2}

    def _personal_words(self, episode: Episode) -> set[str]:
        text = " ".join(
            [m.trigger + " " + m.insight for m in episode.aha_moments]
            + [i.text for i in episode.insights]
            + [q.question for q in episode.open_questions]
        )
        return self._words(text)

    # ── LLM 关联判断 ────────────────────────────────────────
    def _llm_link(self, episode: Episode, candidates: list[Episode]) -> list[RelatedRef]:
        blocks = []
        for idx, other in enumerate(candidates):
            blocks.append(
                f"[{idx}] {other.display_title}\n"
                f"分类：{other.category}｜标签：{', '.join(other.tags)}\n"
                f"摘要：{other.summary}\n"
                f"啊哈时刻：{self._personal_brief(other)}"
            )
        prompt = self.settings.prompt_text("knowledge_link").format(
            episode_title=episode.display_title,
            category=episode.category,
            summary=episode.summary,
            key_points="；".join(episode.key_points),
            tags="、".join(episode.tags),
            aha_moments=self._aha_brief(episode),
            insights="；".join(i.text for i in episode.insights),
            open_questions="；".join(q.question for q in episode.open_questions),
            history_blocks="\n\n".join(blocks),
            max_related=self.settings.max_related,
        )
        try:
            data = self.llm.chat_json("你在维护一棵个人知识树，只做真实、克制的关联。", prompt)
        except Exception as exc:  # noqa: BLE001
            log.warning("LLM 关联判断失败，回退关键词关联：%s", exc)
            return self._keyword_link(episode, candidates)

        refs: list[RelatedRef] = []
        for item in data if isinstance(data, list) else []:
            idx = item.get("ref_index")
            if not isinstance(idx, int) or idx >= len(candidates):
                continue
            other = candidates[idx]
            relation = str(item.get("relation_type", "theme"))
            refs.append(
                RelatedRef(
                    title=other.display_title,
                    url=other.note_url,
                    reason=str(item.get("reason", "")).strip(),
                    relation_type=relation if relation in _VALID_RELATIONS else "theme",
                )
            )
        return refs

    @staticmethod
    def _aha_brief(episode: Episode) -> str:
        return "；".join(f"{m.trigger}→{m.insight}" for m in episode.aha_moments) or "（无）"

    @staticmethod
    def _personal_brief(episode: Episode) -> str:
        bits = [f"{m.trigger}→{m.insight}" for m in episode.aha_moments]
        bits += [i.text for i in episode.insights]
        bits += [q.question for q in episode.open_questions]
        return "；".join(bits) or "（无）"

    # ── 关键词兜底关联 ──────────────────────────────────────
    def _keyword_link(self, episode: Episode, candidates: list[Episode]) -> list[RelatedRef]:
        refs: list[RelatedRef] = []
        for other in candidates:
            shared_tags = set(episode.tags) & set(other.tags)
            shared_personal = self._personal_words(episode) & self._personal_words(other)
            if not shared_tags and not shared_personal:
                continue
            reason_parts = []
            if shared_tags:
                reason_parts.append(f"共同标签：{', '.join(sorted(shared_tags))}")
            if shared_personal:
                reason_parts.append(f"顿悟 / 问题呼应：{', '.join(sorted(shared_personal)[:3])}")
            relation = "aha" if shared_personal and not shared_tags else "theme"
            refs.append(
                RelatedRef(
                    title=other.display_title,
                    url=other.note_url,
                    reason="；".join(reason_parts),
                    relation_type=relation,
                )
            )
        return refs[: self.settings.max_related]
