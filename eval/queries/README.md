# W1 评测查询集

`w1-real-library.jsonl` — 479 条查询，绑定到一个 2,376 条书签的真实网页库。
这是 W1 决策闸门唯一的输入，把它放进仓库是为了让闸门结论可复算。

## 这些查询是怎么来的

库本身**不是任何人的私人收藏夹**。它由两个公开来源拼成：中文技术周刊
（第 191–406 期，1,807 条）和 Hacker News（569 条），抓取时遵守
`robots.txt`。构造过程见 `scripts/corpus/collect.py` 与 `sample.py`。
真实收藏夹只用于对齐规模与分布统计，从未进入这个库，也不在仓库里。

查询由 `scripts/corpus/gen_queries.py` 生成：Qwen2.5-3B-Instruct 读目标页
正文（前 1,400 字符）后写查询，再经一层拒绝规则过滤，最后由
`scripts/corpus/finalize_queries.py` 绑定 `target_id` 并补 `note`。
生成器的 seed 与阈值写在文件头两行 `//` 注释里。

## 三类查询

| qtype | n | 它测的是什么 |
|---|---|---|
| `q_content` | 171 | 记得内容说了什么，但不记得标题原文 |
| `q_vague` | 136 | 只记得当时想解决的问题，说不出关键词 |
| `q_episodic` | 172 | 记得**什么时候**、在做什么时存的 |

`q_episodic` 的 `note` 字段再分三个子类型，机制完全不同，读结果时必须分层：

| note | n | 时间表达 | 命中要靠什么 |
|---|---|---|---|
| `year` | 101 | 绝对年份 | 时间窗 → 上下文乘子 |
| `relative` | 43 | 「去年」「今年」这类相对词 | 时间窗 → 上下文乘子 |
| `anchor` | 28 | 没有日期，只有情景标记 | 只能靠一跳图扩展 |

## 三个已知偏差

生成器写查询时看的是目标页正文，所以它知道的比一个真实用户多。四轮迭代压掉
了最明显的泄漏——标题原文、组合泄漏、few-shot 示例污染——但下面三条留在里面，
读数字时要一起读：

1. **时间表达不是模型写的。** 3B 模型算不对相对日期（v2 版本 5 条
   `q_episodic` 时间全错）。现在由 Python 从 `date_added` 算出粗粒度短语，
   模型只写话题线索，再用产品自己的 `understand.classify()` 校验解析得出
   时间窗，解析不出就丢弃。这让 `q_episodic` 的时间部分**偏易**。
2. **丢弃率不低**：`q_content` 34%、`q_episodic` 34%、`q_vague` 48%。留下的是
   「3B 模型造得出、且过得了拒绝规则」的那一部分，不是查询空间的均匀抽样。
3. **中文分层不对齐**：库里 57.7% 的标题是中文，正文只有 9.5%（周刊用中文
   描述英文文章）。中文查询命中的往往是中文标题 + 英文正文的页面。

## 记录格式

```json
{"text": "...", "qtype": "q_episodic", "target_url": "https://...",
 "target_id": 1234, "note": "year", "subtype": "year"}
```

`facetmark.eval.corpus.load_query_file()` 只需要 `text` / `qtype` /
`target_url`，并按 `bookmark.url_norm` 重新绑定 id——`target_id` 只是给探针
脚本省一次查表，重新导入后以 URL 为准。
