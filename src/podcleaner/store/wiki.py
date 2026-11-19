"""飞书 Wiki 存储：分类目录树 + 单集笔记，本地索引作为关联比对镜像。

命令通过本机 lark-cli 以用户身份执行；若部署环境改用 OpenAPI 直连，
替换 `_run` 即可，上层流程不变。
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

from ..config import Settings
from ..models import Episode, RelatedRef
from .local_store import LocalStore

log = logging.getLogger(__name__)


class WikiStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.index_file = Path(settings.index_file)
        self.index_file.parent.mkdir(parents=True, exist_ok=True)
        self._category_nodes: dict[str, str] = {}

    # ── CLI 封装 ────────────────────────────────────────────
    def _run(self, *args: str, cwd: Path | None = None) -> dict:
        cmd = [self.settings.lark_cli, *args, "--as", "user", "--format", "json"]
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60, cwd=str(cwd) if cwd else None
        )
        if proc.returncode != 0:
            raise RuntimeError(f"lark-cli 调用失败：{proc.stderr or proc.stdout}")
        try:
            envelope = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return {"raw": proc.stdout}
        if envelope.get("ok") is False:
            err = envelope.get("error", {})
            raise RuntimeError(
                f"lark-cli 返回错误：{err.get('message') or err}（code={err.get('code')}）"
            )
        return envelope.get("data", envelope)

    # ── 索引镜像 ────────────────────────────────────────────
    def _read_index(self) -> list[dict]:
        if not self.index_file.exists():
            return []
        try:
            return json.loads(self.index_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

    def _write_index(self, items: list[dict]) -> None:
        self.index_file.write_text(
            json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def list_episodes(self) -> list[Episode]:
        return [Episode.from_dict(item) for item in self._read_index()]

    # ── 分类目录树 ───────────────────────────────────────────
    def ensure_tree(self) -> None:
        """按 taxonomy 补齐分类节点，缓存 分类名 -> node_token。"""
        if not self.settings.wiki_space_id:
            raise RuntimeError("未配置 PODCLEANER_WIKI_SPACE_ID")

        resp = self._run("wiki", "+node-list", "--space-id", self.settings.wiki_space_id)
        for node in resp.get("nodes", []):
            self._category_nodes[node.get("title", "")] = node.get("node_token", "")

        for cat in self.settings.category_names:
            if cat in self._category_nodes and self._category_nodes[cat]:
                continue
            # 分类节点建在空间根目录：根伪节点不能作为 parent-node-token 传入，
            # 否则会触发 131007；省略父节点即落在根目录。
            create = self._run(
                "wiki", "+node-create",
                "--space-id", self.settings.wiki_space_id,
                "--title", cat,
                "--obj-type", "docx",
            )
            self._category_nodes[cat] = create.get("node_token", "")

    # ── 写入笔记 ────────────────────────────────────────────
    def save(self, episode: Episode) -> None:
        self.ensure_tree()
        parent = self._category_nodes.get(episode.category, "")
        create = self._run(
            "wiki", "+node-create",
            "--space-id", self.settings.wiki_space_id,
            "--parent-node-token", parent,
            "--title", episode.display_title,
            "--obj-type", "docx",
        )
        data = create
        episode.note_token = data.get("node_token", "")
        episode.note_url = data.get("url", "") or (
            f"/wiki/{episode.note_token}" if episode.note_token else ""
        )

        markdown = LocalStore._render_markdown(episode)
        self._write_doc(data.get("obj_token", ""), markdown)

        items = [
            x for x in self._read_index()
            if Episode.from_dict(x).signature() != episode.signature()
        ]
        items.append(episode.to_dict())
        self._write_index(items)

    def add_backlink(self, episode: Episode, refs: list[RelatedRef]) -> None:
        by_sig = {e.signature(): e for e in self.list_episodes()}
        for ref in refs:
            target = next(
                (e for e in by_sig.values() if e.display_title == ref.title), None
            )
            if target is None:
                continue
            target.related.append(
                RelatedRef(
                    title=episode.display_title,
                    url=episode.note_url,
                    reason=ref.reason,
                    relation_type="continuation",
                )
            )
            if target.note_token:
                self._append_backlink(target, episode)
            self.save(target)

    def _append_backlink(self, target: Episode, episode: Episode) -> None:
        line = f"\n\n### 反向链接\n- ← 关联新条目：[{episode.display_title}]({episode.note_url})"
        self._write_doc(target.note_token, line, append=True)

    def _write_doc(self, obj_token: str, markdown: str, append: bool = False) -> None:
        if not obj_token:
            return
        action = "append" if append else "overwrite"
        # @file 只接受 cwd 下的相对路径：临时文件放在索引目录，命令在该目录执行。
        tmp = self.index_file.parent / f".doc_write_{obj_token}.md"
        try:
            tmp.write_text(markdown, encoding="utf-8")
            self._run(
                "docs", "+update",
                "--doc", obj_token,
                "--command", action,
                "--doc-format", "markdown",
                "--content", f"@./{tmp.name}",
                cwd=self.index_file.parent,
            )
        finally:
            if tmp.exists():
                tmp.unlink()
