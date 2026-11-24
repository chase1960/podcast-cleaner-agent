from podcleaner.config import Settings
from podcleaner.analyzer.threads import build_threads
from podcleaner.models import Episode, OpenQuestion


def _ep(title, tags, questions=None, category="科技与互联网"):
    ep = Episode(
        podcast_name="节目",
        episode_title=title,
        category=category,
        tags=tags,
        summary="一期示例节目。",
    )
    if questions:
        ep.open_questions = [OpenQuestion(question=q) for q in questions]
    return ep


def test_empty_threads():
    settings = Settings(env={})
    assert build_threads([], settings) == []


def test_tag_cluster_groups_shared_topic():
    settings = Settings(env={})
    eps = [
        _ep("甲", ["大模型", "个体成长"], ["如何切入？"]),
        _ep("乙", ["大模型", "产品方法论"], ["如何切入？", "壁垒是什么？"]),
        _ep("丙", ["亲密关系"], []),
    ]
    threads = build_threads(eps, settings, llm=None)

    assert len(threads) >= 1
    main = max(threads, key=lambda t: len(t.members))
    assert len(main.members) == 2
    # 问题去重：同一问题只保留一次
    assert main.open_questions.count("如何切入？") == 1
    assert "壁垒是什么？" in main.open_questions


def test_disabled_threads_returns_empty():
    settings = Settings(env={"PODCLEANER_ENABLE_THREADS": "false"})
    eps = [_ep("甲", ["大模型"]), _ep("乙", ["大模型"])]
    assert build_threads(eps, settings, llm=None) == []
