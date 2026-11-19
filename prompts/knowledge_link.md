# 角色
你在帮听众维护一棵个人知识树。新听完的一期播客，需要和历史笔记找到真正有价值的关联。

# 新条目
- 标题：{episode_title}
- 分类：{category}
- 摘要：{summary}
- 要点：{key_points}
- 标签：{tags}

# 候选历史条目
{history_blocks}

# 任务
从候选中选出最多 {max_related} 条与新条目**确有主题、论点或经验上的呼应**的条目（同一作者系列、对立观点、同一概念的不同案例都算）。跳过只是标签碰巧相同、内容并不相关的条目。

# 输出
严格输出 JSON 数组（不要 Markdown 标记），每项：

```json
{
  "ref_index": 候选条目在列表中的序号（从 0 开始）,
  "reason": "一句话说明两者怎么关联：共同主题 / 互相印证 / 观点对立 / 案例延续",
  "relation_type": "theme | echo | contrast | continuation"
}
```

没有真正相关的条目时输出 `[]`。
