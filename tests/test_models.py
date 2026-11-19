from podcleaner.models import Episode, RelatedRef


def test_episode_roundtrip():
    episode = Episode(
        podcast_name="节目 A",
        episode_title="第 1 期",
        category="科技与互联网",
        tags=["大模型"],
        related=[RelatedRef(title="旧节目", reason="共同主题", relation_type="theme")],
    )
    restored = Episode.from_dict(episode.to_dict())
    assert restored.signature() == episode.signature()
    assert restored.related[0].reason == "共同主题"
    assert restored.display_title == "节目 A｜第 1 期"


def test_related_ref_defaults():
    ref = RelatedRef(title="x")
    assert ref.relation_type == "theme"
    assert ref.to_dict()["url"] == ""
