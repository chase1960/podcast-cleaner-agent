"""OpenAI 兼容 LLM 客户端，负责 JSON 输出的稳健解析。"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

log = logging.getLogger(__name__)

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


class LLMClient:
    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self.model = model
        self._client = None
        if api_key:
            try:
                from openai import OpenAI

                self._client = OpenAI(base_url=base_url, api_key=api_key)
            except ImportError:
                log.warning("未安装 openai 包，LLM 调用不可用。")

    @property
    def available(self) -> bool:
        return self._client is not None

    def chat(self, system: str, user: str, temperature: float = 0.2) -> str:
        if not self.available:
            raise RuntimeError("LLM 客户端未配置（缺少 API Key 或 openai 包）。")
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
        )
        return resp.choices[0].message.content or ""

    def chat_json(self, system: str, user: str) -> Any:
        """调用并解析 JSON；解析失败时抛出 ValueError，由上层兜底。"""
        raw = self.chat(system, user)
        cleaned = _CODE_FENCE_RE.sub("", raw).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # 尝试截取第一个 JSON 对象 / 数组
            match = re.search(r"(\{.*\}|\[.*\])", cleaned, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            raise
