# karakeep 集成：把这个项目该干的事缩小到只剩排序

## 先说结论

[karakeep](https://github.com/karakeep-app/karakeep) 已经把 facetmark 一直在慢慢重造的
东西全都做完了，而且做得比这个仓库好得多：浏览器扩展、手机 App、无头 Chrome 抓取加正文
抽取、资源归档、多用户账号、自动打标、Web UI、Docker 与 Helm 部署。

而它的**排序是一个插件**。`packages/shared/search.ts` 里的接口只有四个方法，代码库里没有
任何别的地方假设背后是 MeiliSearch：

```ts
interface SearchIndexClient {
  addDocuments(documents, options?): Promise<void>;
  deleteDocuments(ids, options?): Promise<void>;
  search(options): Promise<{hits: [{id, score?}], totalHits, processingTimeMs}>;
  clearIndex(): Promise<void>;
}
```

`PluginManager.register({type: PluginType.Search, name, provider})` 注册，**最后注册的
生效**。这就是全部的集成面。

所以分工是清楚的，而且和这个项目已经量出来的东西对得上：

| 事情 | 谁做 | 理由 |
|---|---|---|
| 抓页面、抽正文、存快照 | **karakeep** | facetmark 第一次建索引最慢的一步就是抓取，karakeep 已经付过这笔钱 |
| 浏览器扩展、手机端、UI | **karakeep** | 这个仓库里那个扩展是 1.0.0 的构建物，没有 Node 环境，无法重建也无法校验 |
| 多用户、部署、打标 | **karakeep** | 全都有，且有人在维护 |
| **排序** | **facetmark** | karakeep 的搜索是 BM25 加一个向量库；这个项目全部的实测收益都在排序上 |
| **预注册评测** | **facetmark** | 十档消融、616 条 holdout、361 条对抗探针、两次因为数字不合格而改默认值 |

不该继续造的轮子，就此不造了。`integrations/` 里只有一个转发器，`src/facetmark/bridges/`
里只有映射逻辑。

## 装法

三步，两个环境变量。

```bash
# 1. facetmark 侧：起服务，拿配对 token
facetmark serve                     # 默认 127.0.0.1:8787
facetmark token                     # 打印 token

# 2. karakeep 侧：把插件目录拷进去
cp -r integrations/karakeep/search-facetmark <karakeep>/packages/plugins/

# 3. 在 karakeep 的服务端入口里，和别的插件 import 放在一起
#    import "@karakeep/plugin-search-facetmark";
export FACETMARK_URL=http://127.0.0.1:8787
export FACETMARK_TOKEN=<上面那个 token>
```

两个变量必须都设。少一个 `isConfigured()` 就返回 false，karakeep 退回原来的搜索插件——
**缺 token 不会被当成"不需要鉴权"**。

装完之后在 karakeep 里触发一次「重建索引」，它会把全部书签通过 `addDocuments` 推过来，
facetmark 这边按批入库并逐批算向量。不需要读 karakeep 的数据库，也不需要知道它的 schema。

## 服务端的四个路由

都在同一个配对 token 后面，都在 `src/facetmark/api.py`：

| 路由 | 对应 | 返回 |
|---|---|---|
| `POST /karakeep/documents` | `addDocuments` | `received / stored / created / updated / embedded / created_at_missing / embed_error` |
| `POST /karakeep/documents/delete` | `deleteDocuments` | `requested / removed / kept_not_ours` |
| `POST /karakeep/search` | `search` | `hits[{id,score}] / totalHits / processingTimeMs / engine / truncated` |
| `POST /karakeep/clear` | `clearIndex` | `purged_bookmarks / cleared_mappings` |
| `GET /karakeep/stats` | 无（诊断用） | `documents / users / with_body` |

`/karakeep/search` 多接一个 `config` 参数，取 `full`、`A`–`E` 或任意消融档名——也就是说
**可以在真实的 karakeep 库上跑消融**，而不是只能在生成的语料上跑。这是这次集成顺带买到
的最有价值的东西：所有已有的数字都来自生成的查询集，这条路第一次让真人真库的对比成为
可能。

## 字段映射，以及它不保真的地方

| karakeep | facetmark | 说明 |
|---|---|---|
| `content` | `content.body_text` | karakeep 抓好的正文，直接进来 |
| `description` + `note` + `content` | 同上，拼成一块 | 存的推文和图片没有正文，`note` 是用户自己写的保存理由——恰好是这个项目要索引的东西 |
| `tags` | `bookmark.folder`（`" / "` 连接） | karakeep 没有文件夹树。标签是最接近"同批归档"信号的东西，但**不是等价物**：五个标签的页面看起来像五层嵌套目录 |
| `summary` + `tags` | `enrichment.summary` / `topics` | 让词法索引和内容向量都能看到 |
| `createdAt` | `bookmark.date_added` | 时间衰减和会话重建读这个。解析不了就回落到当前时间，并在返回里**计数**而不是咽掉 |
| `title` / `linkTitle` | `bookmark.title` | 前者优先，都空则用 URL |
| `userId` | `karakeep_doc.user_id` | 见下 |

**没有映射过来的是 facetmark 自己的意图面**——「当初为什么存它」那组生成查询。桥接不做
LLM 调用。装完之后单独跑 `facetmark index` 可以补上，那时正文已经是 karakeep 抓好的，
只需付 LLM 的钱。

### 多用户是这里最弱的一环，说清楚

facetmark 的索引没有用户分区。`userId` 存在映射表里，**排序完成之后**再过滤。在多用户
实例上这会把召回偏向书签多的那个人：一次查询先在全库范围内排序，然后砍掉不属于当前用户
的结果，书签少的用户就更容易被挤出候选窗口。代码里的 `OVERFETCH = 5` 是补偿，不是保证。

真要多租户，诚实的配置是**一个用户一个 facetmark 库**（每个用户一份 `FACETMARK_URL`）。
现在这版适合单用户自部署，也就是绝大多数 karakeep 实例。

### 删除有一条硬规则

`deleteDocuments` 只删 `source='karakeep'` 的行。如果一个 URL 在桥接之前就在库里（比如从
浏览器导入的），karakeep 推它时是**认领**而不是新建，`source` 保持原样；karakeep 后来忘掉
它，这边只解绑不删除，计入 `kept_not_ours`。`clearIndex` 同理，只清自己建的。

这条规则有测试钉着（`test_delete_never_removes_a_bookmark_it_did_not_create`、
`test_clear_index_removes_only_karakeep_owned_rows`）。一个能删掉不属于自己的数据的集成，
是不能装的。

映射表 `karakeep_doc` 按需创建：从没跟 karakeep 说过话的库里不存在这张表。卸载就是
`DROP TABLE karakeep_doc`。

## 测到什么程度

- **Python 侧**：40 条测试。`tests/test_karakeep_bridge.py` 34 条盖映射、时间戳解析、
  过滤器拆分、认领、删除边界、时序浏览、分页、上限钳制；`tests/test_api.py` 里
  `TestKarakeepRoutes` 6 条盖四个路由的鉴权、往返、未知档位拒绝、`limit` 超限。
- **TypeScript 侧：这个仓库不构建也不测试它。** 没有 Node 工具链，CI 里也没有 karakeep
  检出。那个文件由 karakeep 自己的构建来类型检查，在这里由**零**东西检查。它调用的请求
  与响应形状被上面那 40 条测试钉住了，这是能给的最强保证，不等于它能编译。

这一条写在这里，也写在那个 `.ts` 文件的头注释里。别人照着装的时候应该先知道这件事。

## 装完之后第一件该做的事

在自己的库上跑一次 `full` 与 `A` 的对比。已有的所有数字都来自生成的查询集，
`docs/gate-precision.md` 里那次 −18.83pp 说明了生成语料能把结论带偏多远。真实库上的
消融是这个集成真正的用处，比"多一个搜索后端"重要得多。
