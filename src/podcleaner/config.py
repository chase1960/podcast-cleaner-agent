"""配置加载：环境变量 + taxonomy YAML。"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = ROOT / "config" / "categories.yaml"
PROMPTS_DIR = ROOT / "prompts"


class Settings:
    def __init__(self, env: dict[str, str] | None = None) -> None:
        env = env or os.environ

        # LLM
        self.llm_base_url = env.get("PODCLEANER_LLM_BASE_URL", "https://api.openai.com/v1")
        self.llm_api_key = env.get("PODCLEANER_LLM_API_KEY", "")
        self.llm_model = env.get("PODCLEANER_LLM_MODEL", "gpt-4o-mini")

        # 存储
        self.store = env.get("PODCLEANER_STORE", "wiki")
        self.index_file = Path(env.get("PODCLEANER_INDEX_FILE", ".podcleaner/index.json"))

        # 飞书
        self.wiki_space_id = env.get("PODCLEANER_WIKI_SPACE_ID", "")
        self.wiki_root_node = env.get("PODCLEANER_WIKI_ROOT_NODE", "")
        self.wiki_home_url = env.get("PODCLEANER_WIKI_HOME_URL", "")
        self.lark_cli = env.get("PODCLEANER_LARK_CLI", "lark-cli")

        # 抓取
        self.http_timeout = int(env.get("PODCLEANER_HTTP_TIMEOUT", "15"))
        self.manual_transcript = env.get("PODCLEANER_MANUAL_TRANSCRIPT", "")

        # ASR
        self.asr_engine = env.get("PODCLEANER_ASR_ENGINE", "none")

        # taxonomy
        taxonomy = self._load_taxonomy()
        self.categories: list[dict[str, Any]] = taxonomy["taxonomy"]
        self.category_names: list[str] = [c["name"] for c in self.categories]
        self.default_category = taxonomy.get("default_category", "其他")
        self.max_related = int(taxonomy.get("max_related_per_episode", 3))

        # 个人沉淀层上限与开关（yaml 默认值，env 可覆盖）
        self.max_aha = int(env.get("PODCLEANER_MAX_AHA", taxonomy.get("max_aha_per_episode", 3)))
        self.max_open_questions = int(
            env.get("PODCLEANER_MAX_OPEN_QUESTIONS", taxonomy.get("max_open_questions", 3))
        )
        self.max_next_steps = int(
            env.get("PODCLEANER_MAX_NEXT_STEPS", taxonomy.get("max_next_steps", 3))
        )
        self.enable_threads = env.get("PODCLEANER_ENABLE_THREADS", "").lower() not in (
            "0",
            "false",
            "no",
        ) and bool(taxonomy.get("enable_threads", True))

    @staticmethod
    def _load_taxonomy() -> dict[str, Any]:
        if not CONFIG_FILE.exists():
            return {"taxonomy": [], "default_category": "其他", "max_related_per_episode": 3}
        import yaml  # 懒加载：仅在实例化 Settings 时需要

        with CONFIG_FILE.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh)

    def prompt_text(self, name: str) -> str:
        return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")

    def match_category(self, text: str) -> str:
        """无 LLM 时的关键词兜底分类。"""
        lowered = text.lower()
        best, best_hits = self.default_category, 0
        for cat in self.categories:
            hits = sum(k.lower() in lowered for k in cat.get("keywords", []))
            if hits > best_hits:
                best, best_hits = cat["name"], hits
        return best


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
