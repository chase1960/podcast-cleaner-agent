"""本地 Markdown 存储：notes/<分类>/<slug>.md + 索引 JSON。"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from ..models import Episode, RelatedRef

log = logging.getLogger(__name__)

_SLUG_RE = re.compile(r"[^\w\u4e00-\u9fa5]+")


def _slug(text: str) -> str:
    return _SLUG_RE.sub("-", text).strip("-")[:80] or "episode"


class LocalStore:
    def __init__(self, root: Path | str = "notes", index_file: Path | str = ".podcleaner/index.json") -> None:
        self.root = Path(root)
        self.index_file = Path(index_file)
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_file.parent.mkdir(parents=True, exist_ok=True)

    # ── 索引 ────────────────────────────────────────────────
    def _read_index(self) -> list[dict]:
        if not self.index_file.exists():
            return []
        try:
            return json.loads(self.index_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            log.warning("索引文件损坏，按空索引处理。")
            return []

    def _write_index(self, items: list[dict]) -> None:
        self.index_file.write_text(
            json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def list_episodes(self) -> list[Episode]:
        return [Episode.from_dict(item) for item in self._read_index()]

    # ── 写入 ────────────────────────────────────────────────
    def save(self, episode: Episode) -> None:
        category_dir = self.root / _slug(episode.category)
        category_dir.mkdir(parents=True, exist_ok=True)
        md_path = category_dir / f"{_slug(episode.episode_title)}.md"
        md_path.write_text(self._render_markdown(episode), encoding="utf-8")
        episode.note_url = str(md_path)

        items = self._read_index()
        items = [x for x in items if Episode.from_dict(x).signature() != episode.signature()]
        items.append(episode.to_dict())
        self._write_index(items)

    def add_backlink(self, episode: Episode, refs: list[RelatedRef]) -> None:
        by_sig = {e.signature(): e for e in self.list_episodes()}
        for ref in refs:
            target = next(
                (e for e in by_sig.values() if e.display_title == ref.title or e.episode_title == ref.title),
                None,
            )
            if target is None:
                continue
            target.related.append(
                RelatedRef(title=episode.display_title, url=episode.note_url, reason=ref.reason,
                            relation_type="continuation")
            )
            # 回写 Markdown 末尾的反向链接小节
            if target.note_url and Path(target.note_url).exists():
                self._append_backlink(Path(target.note_url), episode)
            self.save(target)

    @staticmethod
    def _append_backlink(path: Path, episode: Episode) -> None:
        existing = path.read_text(encoding="utf-8")
        line = f"- ← 关联新条目：[{episode.display_title}]({episode.note_url})"
        if episode.display_title in existing:
            return
        path.write_text(existing.rstrip() + f"\n\n### 反向链接\n{line}\n", encoding="utf-8")

    # ── 渲染 ────────────────────────────────────────────────
    @staticmethod
    def _render_markdown(episode: Episode) -> str:
        lines = [
            f"# {episode.display_title}",
            "",
            f"- 分类：{episode.category}",
            f"- 收听日期：{episode.listened_at}",
            f"- 来源：{episode.source_type}" + (f"｜[链接]({episode.url})" if episode.url else ""),
            "",
            "## 摘要",
            episode.summary or "（待补充）",
            "",
            "## 核心要点",
        ]
        lines += [f"- {point}" for point in episode.key_points] or ["- （无）"]
        if episode.quotes:
            lines += ["", "## 金句"] + [f"> {q}" for q in episode.quotes]

        if episode.aha_moments:
            lines += ["", "## 💡 啊哈时刻"]
            for moment in episode.aha_moments:
                body = moment.insight or "（待补充个人顿悟）"
                lead = f"{moment.trigger} —— {body}" if moment.trigger else body
                tag_suffix = f"（{', '.join(moment.tags)}）" if moment.tags else ""
                lines.append(f"- {lead}{tag_suffix}")
        if episode.insights:
            lines += ["", "## 个人启发"]
            for insight in episode.insights:
                lines.append(f"- {insight.text}")
        if episode.open_questions:
            lines += ["", "## ❓ 待深挖问题"]
            for question in episode.open_questions:
                extra = f" —— {question.why_it_matters}" if question.why_it_matters else ""
                lines.append(f"- {question.question}{extra}（{question.status}）")
        if episode.next_steps:
            lines += ["", "## 🧭 下一步深耕"]
            for step in episode.next_steps:
                meta = " · ".join(x for x in (step.direction, f"优先级 {step.priority}") if x)
                lines.append(f"- {step.action}" + (f"（{meta}）" if meta else ""))

        if episode.tags:
            lines += ["", "## 标签", "、".join(episode.tags)]
        if episode.related:
            lines += ["", "## 关联收听"]
            for ref in episode.related:
                lines.append(f"- [{ref.title}]({ref.url})：{ref.reason}（{ref.relation_type}）")
        return "\n".join(lines) + "\n"
