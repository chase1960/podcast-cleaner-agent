"""命令行入口：python -m podcleaner.cli {ingest|briefing|tree|insights}"""

from __future__ import annotations

import argparse
import json
import logging

from .pipeline import Pipeline, PipelineError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="podcleaner", description="播客清洗与知识树 Agent")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest", help="抓取并清洗一期播客，写入知识库")
    ingest.add_argument("name", help="播客节目名")
    ingest.add_argument("--episode", help="单集标题（可选，用于匹配）")
    ingest.add_argument("--transcript", help="粘贴的文字稿（可选回退）")
    ingest.add_argument("--audio", help="音频文件路径（可选 ASR 回退）")

    briefing = sub.add_parser("briefing", help="生成昨日简报卡片")
    briefing.add_argument("--date", help="指定日期 YYYY-MM-DD，默认昨天")
    briefing.add_argument("--dry-run", action="store_true", help="只渲染不推送")
    briefing.add_argument("--json", action="store_true", help="输出卡片 JSON")

    sub.add_parser("tree", help="查看当前知识库索引")

    insights = sub.add_parser("insights", help="跨期回顾啊哈时刻 / 启发 / 待解问题 / 深耕方向")
    insights.add_argument("--json", action="store_true", help="输出结构化 JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = _build_parser().parse_args(argv)
    pipeline = Pipeline()

    if args.command == "ingest":
        try:
            episode = pipeline.ingest(
                podcast_name=args.name,
                episode_hint=args.episode,
                transcript=args.transcript or "",
                audio_source=args.audio or "",
            )
        except PipelineError as exc:
            print(f"✗ {exc}")
            return 1
        print(f"✓ 已入库：{episode.display_title}")
        print(f"  分类：{episode.category}｜要点 {len(episode.key_points)} 条｜关联 {len(episode.related)} 条")
        print(f"  啊哈 {len(episode.aha_moments)}｜启发 {len(episode.insights)}｜待解 {len(episode.open_questions)}｜深耕 {len(episode.next_steps)}")
        if episode.note_url:
            print(f"  笔记：{episode.note_url}")
        return 0

    if args.command == "briefing":
        digest, card = pipeline.briefing(args.date)
        print(f"简报日期：{digest.date}｜新增 {digest.total} 期｜分类 {digest.category_count} 个｜脉络 {len(digest.threads)} 条")
        if args.json:
            print(json.dumps(card, ensure_ascii=False, indent=2))
        if not args.dry_run:
            print("提示：实际推送由定时任务调用消息通道发送卡片 JSON。")
        return 0

    if args.command == "tree":
        episodes = pipeline.tree()
        by_category: dict[str, list] = {}
        for ep in episodes:
            by_category.setdefault(ep.category, []).append(ep)
        for category, items in by_category.items():
            print(f"\n【{category}】{len(items)} 期")
            for ep in items:
                print(f"  - {ep.display_title}（{ep.listened_at}）")
        return 0

    if args.command == "insights":
        episodes = pipeline.list_insights()
        if args.json:
            print(json.dumps([ep.to_dict() for ep in episodes], ensure_ascii=False, indent=2))
            return 0
        if not episodes:
            print("还没有沉淀任何啊哈时刻 / 启发 / 待解问题 / 深耕方向。")
            return 0
        by_category: dict[str, list] = {}
        for ep in episodes:
            by_category.setdefault(ep.category, []).append(ep)
        for category, items in by_category.items():
            print(f"\n【{category}】{len(items)} 期有沉淀")
            for ep in items:
                print(f"  ▸ {ep.display_title}")
                for moment in ep.aha_moments:
                    print(f"      💡 {moment.trigger} → {moment.insight}")
                for insight in ep.insights:
                    print(f"      ✨ {insight.text}")
                for question in ep.open_questions:
                    print(f"      ❓ {question.question}")
                for step in ep.next_steps:
                    print(f"      🧭 {step.action}（{step.direction} · {step.priority}）")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
