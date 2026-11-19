"""存储适配：Wiki 知识库 / 本地 Markdown。"""

from .base import Store
from .local_store import LocalStore
from .wiki import WikiStore

__all__ = ["Store", "LocalStore", "WikiStore"]
