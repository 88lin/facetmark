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
| 浏览器扩展、手机端、UI | **karakeep** | 这个仓库的扩展只有 MV3 一端，还停在 1.0.0；karakeep 有扩展、iOS、Android 三端并且有人在维护 |
| 多用户、部署、打标 | **karakeep** | 全都有，且有人在维护 |
| **排序** | **facetmark** | karakeep 的搜索是 BM25 加一个向量库；这个项目全部的实测收益都在排序上 |
| **预注册评测** | **facetmark** | 十档消融、616 条 holdout、361 条对抗探针、两次因为数字不合格而改默认值 |

不该继续造的轮子，就此不造了。`integrations/` 里只有一个转发器，`src/facetmark/bridges/`
里只有映射逻辑。

## 装法

四步，两个环境变量。

```bash
# 1. facetmark 侧：起服务，拿配对 token
facetmark serve                     # 默认 127.0.0.1:8787
facetmark token                     # 打印 token

# 2. karakeep 侧：把插件目录拷进去
#    注意它是 @karakeep/plugins 这个包里的一个子目录，不是独立的包——
#    上游的 search-meilisearch 也没有自己的 package.json
cp -r integrations/karakeep/search-facetmark <karakeep>/packages/plugins/
```

```jsonc
// 3a. packages/plugins/package.json 的 exports 里加一行
"./search-facetmark": "./search-facetmark/index.ts",
```

```ts
// 3b. packages/shared-server/src/plugins.ts 的 loadAllPlugins() 里加一行，
//     位置要在 search-meilisearch 那行之后
await import("@karakeep/plugins/search-facetmark");
```

```bash
# 4. 两个环境变量
export FACETMARK_URL=http://127.0.0.1:8787
export FACETMARK_TOKEN=<上面那个 token>
```

第 3b 步的**顺序是有意义的**：`PluginManager.getClient()` 返回最后注册的那个
provider，上游那句注释写的就是 "Order of plugin loading matter"。放在 meilisearch
之前，facetmark 会被它盖掉，然后你会花一小时怀疑桥接坏了。

两个变量必须都设。少一个 `isConfigured()` 就返回 false，插件根本不注册，karakeep 保持
它原来的搜索插件——**缺 token 不会被当成"不需要鉴权"**。

上面这些路径对应的是 `integrations/karakeep/typecheck/upstream-pins.json` 里钉住的那几个
上游文件版本。karakeep 挪了目录这段就会过期，`npm run check-drift` 会告诉你。

装完之后在 karakeep 里触发一次「重建索引」，它会把全部书签通过 `addDocuments` 推过来，
facetmark 这边按批入库并逐批算向量。不需要读 karakeep 的数据库，也不需要知道它的 schema。

## 服务端的四个路由

都在同一个配对 token 后面，都在 `src/facetmark/api.py`：

| 路由 | 对应 | 返回 |
|---|---|---|
| `POST /karakeep/documents` | `addDocuments` | `received / stored / created / updated / kept_enrichment / embedded / created_at_missing / embed_error` |
| `POST /karakeep/documents/delete` | `deleteDocuments` | `requested / removed / kept_not_ours` |
| `POST /karakeep/search` | `search` | `hits[{id,score}] / totalHits / processingTimeMs / engine / truncated` |
| `POST /karakeep/clear` | `clearIndex` | `purged_bookmarks / cleared_mappings` |
| `GET /karakeep/stats` | 无（诊断用） | `documents / users / with_body` |

`/karakeep/search` 多接一个 `config` 参数，取 `full`、`A`–`E` 或任意消融档名。

> **这条曾经被写成「可以在真实的 karakeep 库上跑消融」。往返实验把它证伪了，这里按
> 协议撤回。** 616 条留出集、2,376 篇真实书签推过去再拉回来：读取路径本身没问题
> （1,232 次 HTTP 与原生逐条比对，0 处不一致），指标级结论也搬得过去
> （ΔRecall@5 = −0.81pp，CI95 [−2.44, +0.81]）。搬不过去的是**名次级**比较——
> top-1 一致率只有 79.06%，因为 karakeep 富集出来的是文件夹标签而不是逐页主题，
> 关键词行的词汇量从 19,016 掉到 13。凡是结论取决于「谁排第一」的消融，在 karakeep
> 富集的库上都不成立，除非先跑一次 `facetmark index` 用本包自己的富集重建。
> 完整链条见 [`karakeep-roundtrip.md`](karakeep-roundtrip.md)。

## 字段映射，以及它不保真的地方

`summary` + `tags` 写进 `enrichment.summary` / `enrichment.topics` 时是**认领而不是
覆盖**：只有这一行本来就不存在，或者本来就是这个桥接自己写的（`source_hash='karakeep'`），
才会写下去；否则原样保留，并在返回里计入 `kept_enrichment`。这不是洁癖——旧代码在这里
有一个静默降级：它更新 `summary`/`topics`/`model` 却不动 `source_hash`，于是
`enrich.targets()` 认为这行「没变过」而**永久跳过**，而向量那边指纹已经变了，会拿更差的
文本重建。结果是一个不报错、不可逆（除非 `--force`）、报告里也看不出来的质量下降。


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

- **Python 侧**：69 条测试。`tests/test_karakeep_bridge.py` 38 条盖映射、时间戳解析、
  过滤器拆分、认领、删除边界、外来富集不被覆盖、时序浏览、分页、上限钳制；
  `tests/test_api.py` 里
  `TestKarakeepRoutes` 6 条盖四个路由的鉴权、往返、未知档位拒绝、`limit` 超限；
  `tests/test_karakeep_contract.py` 25 条是下面那条线格式契约的 Python 半边。
- **TypeScript 侧：类型检查有，集成测试没有。** `integrations/karakeep/typecheck/`
  里放着 karakeep 那两个接口模块（`packages/shared/search.ts`、
  `packages/shared/plugins.ts`）的手写 `.d.ts`，`tsc --noEmit` 拿它们编译插件源码，
  CI 的 `karakeep-plugin` 这个 job 每次 push 都跑。所以**四个方法确实满足
  `SearchIndexClient`，`index.ts` 里那次 `PluginManager.register` 确实类型正确**。

  这个保证的边界要说清楚：手写的 `.d.ts` 是从上游翻译过来的，不是上游本身。它按
  git blob SHA 钉在 `upstream-pins.json` 里，`npm run check-drift` 重新抓一遍上游对
  哈希，`karakeep-drift.yml` 每周一自动跑。上游一改，`tsc` 照样绿——它在对着一份已经
  不存在的契约编译，只有漂移检查能看见这件事。

- **两侧之间：线格式契约。**

  > **撤回。** 这一节原本写着「两侧之间没有任何东西……这需要同时起 karakeep 和
  > facetmark，本仓库做不到」。后半句是错的。验证两边对同一份 JSON 的理解，并不需要
  > 两个进程同时跑；只需要让每一边**把自己那半边的字节落成文件**，另一边对着文件断言。
  > 下面就是这么做的。

  `integrations/karakeep/contract/capture.ts` 用 karakeep 驱动插件的方式驱动它——设
  环境变量、`getClient()`、调四个方法——只把 `globalThis.fetch` 换成一个记录器，然后把
  真实的请求体写进 `wire.json`。插件源码一行没改，也没有被重新实现一遍：落盘的就是真
  karakeep 会放到 socket 上的字节。

  `tests/test_karakeep_contract.py` 把 `wire.json` 里那 6 条请求**原样重放**进真实的
  FastAPI 应用，断言全部 200，并把响应写回 `replies.json`；`capture.ts` 再把这些响应喂
  回插件的 `search()`，检查 TypeScript 这边解析得动。**每一边断言的都是另一边产出的文件**，
  任一侧漂移都会变成一个已提交文件里的 diff。CI 里两个 job 各跑一半：`python` 那个不需要
  Node，`karakeep-plugin` 那个不需要 Python。

  跑法：

  ```bash
  cd integrations/karakeep/typecheck
  npm run contract          # 重新捕获 wire.json
  npm run contract:check    # 变了就失败（CI 跑这条）

  FACETMARK_UPDATE_CONTRACT=1 python -m pytest tests/test_karakeep_contract.py  # 重写 replies.json
  ```

  必须用 `--experimental-transform-types` 而不是 `--strip-types`：插件的构造函数用了参数
  属性，strip-only 模式擦不掉。这里选择动运行参数而不是动插件源码——为了迁就测试工具去改
  被测对象，就没什么可测的了。

  契约钉住的东西，挑几条实际抓到的说：TypeScript 的 `Date` 经 `JSON.stringify` 变成
  `"2025-06-01T00:00:00.000Z"` 这样的字符串（`z.date()` 只存在于 TS 侧，Python 永远见不到
  日期对象）；只有两个必填字段的文档；显式 `null` 与字段缺失是两回事；`FilterQuery` 的
  `eq`（带 `value`）与 `in`（带 `values`）两种变体；`/karakeep/clear` 是一个**声明了
  `content-type: application/json` 却完全没有 body 的 POST**；两个空批次早退**不产生任何
  HTTP 请求**。还有一条 Pydantic 默认会放过的：插件发出的每一个键都必须是请求模型认识的
  字段，否则那个键会被静默丢弃而不报错。

  顺手抓到的一个语义陷阱：`search_full` 那条请求是「唯一一条匹配结果的 offset 1」，
  真实响应是 `hits: []` 但 `totalHits: 1`。**空的 `hits` 不等于没搜到**，任何在 TS 侧
  按「hits 空就是无结果」写的逻辑都会错。这条也钉进断言了。

  边界同样要说清楚：**这是格式契约，不是集成测试。** 它不覆盖插件注册、真实 HTTP 栈、
  并发、以及活的 karakeep 实例里的任何东西。

- 还没测的：活的 karakeep 里跑一遍、karakeep 自己抓的正文、多用户、增量更新漂移。

这几条写在这里，也写在那个 `.ts` 文件的头注释里。别人照着装的时候应该先知道。

写这段的时候顺手发现，最初那版 `check-upstream-drift.sh` 打印 "0 unchanged, 0 drifted"
并退出 0，其实一个文件都没抓——解析 pin 的那段 Python 撞上 3.11 不允许 f-string 里带
反斜杠，静默失败，循环读到空流。一个什么都没检查的检查比没有检查更糟，所以现在读到零条
pin 直接按错误退出。

## 装完之后第一件该做的事

在自己的库上跑一次 `full` 与 `A` 的对比。已有的所有数字都来自生成的查询集，
`docs/gate-precision.md` 里那次 −18.83pp 说明了生成语料能把结论带偏多远。真实库上的
消融是这个集成真正的用处，比"多一个搜索后端"重要得多。
