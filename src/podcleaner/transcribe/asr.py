"""ASR 适配器：默认关闭；接入 faster-whisper 后可把音频转成文字稿。"""

from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)


class Transcriber:
    def __init__(self, engine: str = "none", model_size: str = "small") -> None:
        self.engine = engine
        self.model_size = model_size
        self._model = None

    def transcribe(self, audio_source: str) -> str:
        """返回转写文本；引擎未启用时返回空串，由上层走手动稿回退。"""
        if self.engine == "none" or not audio_source:
            return ""

        if self.engine != "whisper":
            log.warning("未知 ASR 引擎：%s", self.engine)
            return ""

        try:
            from faster_whisper import WhisperModel  # type: ignore
        except ImportError:
            log.warning("未安装 faster-whisper，跳过音频转写。")
            return ""

        if self._model is None:
            self._model = WhisperModel(self.model_size)

        segments, _ = self._model.transcribe(audio_source)
        return "\n".join(segment.text for segment in segments).strip()

    @staticmethod
    def exists(audio_source: str) -> bool:
        return bool(audio_source) and Path(audio_source).exists()
