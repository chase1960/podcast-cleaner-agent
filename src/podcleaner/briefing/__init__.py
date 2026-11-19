"""每日简报：昨日条目汇总 + 飞书卡片渲染。"""

from .digest import Digest, collect_digest
from .card import build_card

__all__ = ["Digest", "collect_digest", "build_card"]
