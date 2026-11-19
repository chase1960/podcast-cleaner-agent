"""取稿模块：多来源组合策略，任一来源命中即返回。"""

from .base import FetchResult, BaseFetcher
from .rss import RssFetcher
from .xiaoyuzhou import XiaoyuzhouFetcher
from .web_search import WebSearchFetcher
from .manual import ManualFetcher

__all__ = [
    "FetchResult",
    "BaseFetcher",
    "RssFetcher",
    "XiaoyuzhouFetcher",
    "WebSearchFetcher",
    "ManualFetcher",
]
