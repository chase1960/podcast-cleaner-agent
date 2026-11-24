from podcleaner.models import (
    AhaMoment,
    Episode,
    Insight,
    NextStep,
    OpenQuestion,
    RelatedRef,
)


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


def test_personal_layer_roundtrip():
    episode = Episode(
        podcast_name="节目 B",
        episode_title="第 2 期",
        aha_moments=[AhaMoment(trigger="原话", insight="顿悟", tags=["成长"])],
        insights=[Insight(text="可迁移启发", source="节目 B｜第 2 期", relation="互相印证")],
        open_questions=[OpenQuestion(question="还能怎么做？", why_it_matters="和工作相关", status="open")],
        next_steps=[NextStep(action="做个小实验", direction="实践", priority="high")],
    )
    restored = Episode.from_dict(episode.to_dict())
    assert restored.aha_moments[0].trigger == "原话"
    assert restored.aha_moments[0].insight == "顿悟"
    assert restored.insights[0].text == "可迁移启发"
    assert restored.open_questions[0].question == "还能怎么做？"
    assert restored.next_steps[0].action == "做个小实验"
    assert restored.next_steps[0].priority == "high"


def test_legacy_dict_without_personal_layer():
    """旧索引缺少个人沉淀字段时，反序列化应回退为空列表，不报错。"""
    legacy = {
        "podcast_name": "旧节目",
        "episode_title": "旧单集",
        "category": "其他",
        "summary": "老笔记",
        "related": [],
    }
    episode = Episode.from_dict(legacy)
    assert episode.aha_moments == []
    assert episode.insights == []
    assert episode.open_questions == []
    assert episode.next_steps == []
    assert episode.signature() == "旧节目::旧单集"
