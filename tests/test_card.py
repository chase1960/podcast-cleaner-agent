from podcleaner.briefing import build_card, collect_digest
from podcleaner.models import Episode


class FakeStore:
    def __init__(self, episodes):
        self._episodes = episodes

    def list_episodes(self):
        return self._episodes


def _episode(title, category, date="2026-11-18"):
    return Episode(
        podcast_name="节目",
        episode_title=title,
        category=category,
        listened_at=date,
        summary="一期示例节目。",
        key_points=["要点一", "要点二"],
        quotes=["一句金句"],
        tags=["标签"],
    )


def test_empty_digest_card():
    digest = collect_digest(FakeStore([]), date_str="2026-11-18")
    card = build_card(digest)
    assert card["schema"] == "2.0"
    assert card["header"]["title"]["content"] == "🎙 播客早报"
    assert digest.total == 0


def test_grouped_card_contains_categories_and_relations():
    eps = [
        _episode("甲", "科技与互联网"),
        _episode("乙", "生活与情感"),
    ]
    eps[0].related.append(__import__("podcleaner.models", fromlist=["RelatedRef"]).RelatedRef(
        title="旧条目", reason="共同标签", relation_type="echo"
    ))
    digest = collect_digest(FakeStore(eps), date_str="2026-11-18")
    card = build_card(digest)
    body_text = "".join(
        el.get("content", "") for el in card["body"]["elements"] if el.get("tag") == "markdown"
    )
    assert "科技与互联网" in body_text
    assert "生活与情感" in body_text
    assert "关联脉络" in body_text
