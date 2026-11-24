from podcleaner.analyzer.threads import KnowledgeThread
from podcleaner.briefing import build_card, collect_digest
from podcleaner.models import (
    AhaMoment,
    Episode,
    NextStep,
    OpenQuestion,
    RelatedRef,
)


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


def _all_markdown(card: dict) -> str:
    return "".join(
        el.get("content", "") for el in card["body"]["elements"] if el.get("tag") == "markdown"
    )


def test_empty_digest_card():
    digest = collect_digest(FakeStore([]), date_str="2026-11-18")
    card = build_card(digest)
    assert card["schema"] == "2.0"
    assert card["header"]["title"]["content"] == "📻 昨日播客回顾"
    assert digest.total == 0


def test_grouped_card_contains_categories_and_relations():
    eps = [
        _episode("甲", "科技与互联网"),
        _episode("乙", "生活与情感"),
    ]
    eps[0].related.append(RelatedRef(title="旧条目", reason="共同标签", relation_type="echo"))
    digest = collect_digest(FakeStore(eps), date_str="2026-11-18")
    card = build_card(digest)
    body_text = _all_markdown(card)
    assert "科技与互联网" in body_text
    assert "生活与情感" in body_text
    assert "关联脉络" in body_text


def test_card_renders_personal_layer_and_guide():
    ep = _episode("丙", "商业与职场")
    ep.aha_moments.append(AhaMoment(trigger="先做出最小作品", insight="动手胜过观望", tags=["方法论"]))
    ep.open_questions.append(OpenQuestion(question="如何把经验转成产品？", why_it_matters="个体机会"))
    ep.next_steps.append(NextStep(action="写一篇最小方案", direction="实践", priority="high"))

    digest = collect_digest(FakeStore([ep]), date_str="2026-11-18")
    card = build_card(digest)
    body_text = _all_markdown(card)

    assert "啊哈" in body_text
    assert "动手胜过观望" in body_text
    assert "待解" in body_text
    assert "如何把经验转成产品？" in body_text
    assert "深耕" in body_text
    assert "写一篇最小方案" in body_text
    assert "知识指引" in body_text


def test_card_renders_threads():
    ep = _episode("丁", "科技与互联网")
    thread = KnowledgeThread(
        title="个体如何用 AI 放大经验",
        summary="两期都在讲动手实践对个人壁垒的价值。",
        members=[ep.display_title],
        open_questions=["如何找到自己的切入场景？"],
    )
    digest = collect_digest(FakeStore([ep]), date_str="2026-11-18", threads=[thread])
    card = build_card(digest)
    body_text = _all_markdown(card)

    assert "个体如何用 AI 放大经验" in body_text
    assert "如何找到自己的切入场景？" in body_text
